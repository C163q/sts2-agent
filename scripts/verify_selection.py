from available_tools import GAME_ACTIONS
import argparse
import json
import os
import time
from pathlib import Path

from roundtrip_client import Client
from game_output import observation_details
from selection_details import inspect_selection_details
from transition_details import end_turn_details


def main():
    parser = argparse.ArgumentParser(description="验证独立测试实例中的原生选牌流程。")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--legacy-tyranny", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    client = Client(root / ".tmp/roundtrip/ipc")
    evidence = []

    def call(operation, arguments=None, *, success=True, stale_retries=0, previous_selection=None):
        token = None
        if operation in {"start_test_combat", "end_turn", "select_card", "selection_option"}:
            observed = call("get_state")
            token = observed["snapshot_id"]
            if previous_selection is not None:
                assert (observed["selection_generation"], (observed.get("selection") or {}).get("selected_ids")) == previous_selection, observed
        response = client.call(operation, token, arguments=arguments)
        evidence.append({"operation": operation, "arguments": arguments, "response": response})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
        if os.environ.get("SELECTION_WINDOWED") and operation == "get_state" and response["ok"]:
            view = (response["state"].get("selection") or {}).get("status")
            capture = root / ".tmp/roundtrip/observation.png"
            if view and capture.is_file():
                args.report.with_name(args.report.stem + "-" + view + ".png").write_bytes(capture.read_bytes())
        if (not response["ok"] and response["error"]["code"] == "stale_state" and success
                and operation in {"select_card", "selection_option"} and stale_retries < 4):
            # A stale-state response guarantees no input; re-observe and verify the same decision remains pending.
            expected = (observed["selection_generation"], (observed.get("selection") or {}).get("selected_ids"))
            return call(operation, arguments, success=success, stale_retries=stale_retries + 1, previous_selection=expected)
        if success:
            assert response["ok"], response
        return response["state"] if response["ok"] else response

    observed = call("get_state")
    deadline = time.monotonic() + 30
    while observed["scene"] == "loading_or_noncombat" and time.monotonic() < deadline:
        time.sleep(.25)
        observed = call("get_state")
    assert observed["scene"] == "main_menu", "仅允许新启动独立测试实例，不能复用正式对局。"
    call("start_test_combat")
    if args.legacy_tyranny or args.scenario in {"tyranny", "retain_zero", "retain_one", "retain_death", "retain_victory"}:
        call("end_turn")
    observed = call("get_state")
    assert observed.get("selection") is not None, "get_observation must report pending card selection"
    observation_details(observed)
    selection = observed["selection"]
    assert selection["status"] == "visible", observed
    assert observed["top_bar"] is not None, "The native selection leaves the top bar visible"
    assert selection["cards"], "Visible selection cards must be included in the basic observation"
    if args.legacy_tyranny:
        return
    inspection = call("inspect_selection")
    inspect_selection_details(inspection)
    cards = inspection["selection"]["cards"]
    assert cards and all("description" in card for card in cards), inspection
    if args.scenario == "combat_pile":
        assert cards and all(card["energy_cost"] == "0" for card in cards), "Corruption must apply in selection details"
        assert all(card["energy_cost"] == "0" for card in selection["cards"]), selection
    if args.scenario == "scroll_race":
        result = call("check_test_selection_race")
        assert result["passed"], result
        print("PASS scroll_race: refused input after concurrent selection")
        return
    assert "end_turn" not in observed["available_actions"], observed
    invalid = call("select_card", {"card_id": 2147483647}, success=False)
    assert not invalid["ok"] and invalid["error"]["code"] == "illegal_action", invalid
    close = call("close_card_view", success=False)
    assert not close["ok"] and close["error"]["code"] == "illegal_action", close

    if selection["can_view_battlefield"]:
        peek = call("set_selection_view", {"view": "battlefield"})
        assert peek["selection"]["status"] == "battlefield" and peek["selection"]["cards"] is None, peek
        assert peek["player"] is not None and peek["enemies"], peek
        assert not set(peek["available_actions"]) & GAME_ACTIONS, peek
        assert not call("end_turn", success=False)["ok"]
        assert not call("select_card", {"card_id": cards[0]["id"]}, success=False)["ok"]
        assert not call("inspect_selection", success=False)["ok"]
        call("inspect_hand")
        call("inspect_combatants")
        call("inspect_ui")
        deck = call("inspect_deck", {"detail_level": "summary"})
        assert deck["scene"] == "deck", deck
        covered = call("get_state")
        assert covered["selection"]["status"] == "covered" and covered["selection"]["cards"] is None, covered
        assert not call("set_selection_view", {"view": "selection"}, success=False)["ok"]
        call("close_card_view")
        map_view = call("inspect_map", success=False)
        if "ok" not in map_view:
            call("close_map")
        pile = call("inspect_pile", {"pile": "discard", "detail_level": "full"})
        if pile["status"] == "opened":
            call("close_card_view")
        peek = call("get_state")
        assert peek["selection"]["status"] == "battlefield", peek
        call("set_selection_view", {"view": "selection"})

    if args.scenario in {"forced_two", "knowledge"}:
        assert len(cards) == 2 and not any(option["id"] == "skip" for option in selection["options"]), selection
    if args.scenario == "chain":
        before_chain = call("get_state")
        first = call("select_card", {"card_id": cards[0]["id"]})
        assert first["transition"]["stop_reason"] == "choice_required", first
        after_chain = call("get_state")
        assert before_chain["selection_generation"] != after_chain["selection_generation"], after_chain
        stale = client.call("select_card", before_chain["snapshot_id"], arguments={"card_id": cards[0]["id"]})
        assert not stale["ok"] and stale["error"]["code"] == "stale_state", stale

    if args.scenario in {"potion_skip", "reward_skip"}:
        option = next(option for option in selection["options"] if option["enabled"] and option["id"] == "skip")
        result = call("selection_option", {"option_id": option["id"]})
    elif args.scenario == "retain_zero":
        assert selection["min_select"] == 0 and selection["max_select"] == 1, selection
        result = call("selection_option", {"option_id": "confirm"})
    else:
        minimum = selection["min_select"]
        choose_count = max(1, minimum)
        if args.scenario == "grid_two":
            assert (minimum, selection["max_select"], len(cards)) == (2, 2, 8), selection
        if args.scenario == "paradox":
            assert len(cards) == 5 and observed["turn"] in (None, 1), inspection
        if args.scenario == "grid_two":
            first = call("select_card", {"card_id": cards[0]["id"]})
            assert first["selection"]["selected_ids"] == [cards[0]["id"]], first
            toggled = call("select_card", {"card_id": cards[0]["id"]})
            assert toggled["selection"]["selected_ids"] == [], toggled
        selected_cards = cards[-1:] if args.scenario == "grid_scroll" else cards[:choose_count]
        for card in selected_cards:
            result = call("select_card", {"card_id": card["id"]})
        if args.scenario == "unsupported_next":
            assert result["transition"]["stop_reason"] == "choice_required" and result["transition"]["complete"], result
            assert result["selection"]["status"] == "unsupported" and not result["available_actions"], result
            print("PASS unsupported_next: choice_required without unsupported actions")
            return
        if args.scenario == "deck":
            assert any(option["id"] == "cancel_preview" for option in result["selection"]["options"]), result
            result = call("selection_option", {"option_id": "cancel_preview"})
            assert not result["selection"]["selected_ids"], result
            result = call("select_card", {"card_id": cards[0]["id"]})
        if (result.get("selection") or {}).get("status") == "visible":
            buttons = result["selection"]["options"]
            if any(b["id"] == "confirm" and b["enabled"] for b in buttons):
                result = call("selection_option", {"option_id": "confirm"})
    end_turn_details(result)
    assert result["transition"]["complete"], result
    assert result["transition"]["stop_reason"] in {"player_ready", "selection_resolved", "combat_won", "combat_lost"}, result
    assert not result.get("selection"), result
    if args.scenario in {"retain_death", "retain_victory"}:
        assert result["transition"]["stop_reason"] == ("combat_lost" if args.scenario == "retain_death" else "combat_won"), result
        assert any(event["type"] == "died" for event in result["transition"]["events"]), result
    print(f"PASS {args.scenario}: {result['transition']['stop_reason']}")


if __name__ == "__main__":
    main()
