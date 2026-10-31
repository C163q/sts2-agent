from available_tools import GAME_ACTIONS
import argparse
import json
from pathlib import Path

from roundtrip_client import Client, player_result


def main():
    parser = argparse.ArgumentParser(description="验证真实牌组页面、导出两档及升级预览，最后显式关闭页面；会改变 UI。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--exercise-options", action="store_true", help="仅在独立实例执行完整参数与排序检查")
    args = parser.parse_args()
    if args.exercise_options and args.ipc_dir.resolve() != Path(__file__).resolve().parents[1] / ".tmp/roundtrip/ipc":
        parser.error("完整参数检查只用于仓库独立游戏实例。")
    client = Client(args.ipc_dir)
    evidence = {"completed": False, "calls": []}

    def call(operation, arguments=None):
        response = client.call(operation, arguments=arguments)
        evidence["calls"].append({"operation": operation, "arguments": arguments, "response": response})
        assert response["ok"], response
        return player_result(response)

    before = call("get_state")
    assert before["screen"]["status"] == "visible", before
    before_token = evidence["calls"][-1]["response"]["state"]["snapshot_id"]
    if args.exercise_options:
        for invalid in [{"detail_level": "bad"}, {"detail_level": None}, {"view_upgrades": "yes"},
                        {"view_upgrades": None}, {"descending": True}, {"sort_by": "rarity"},
                        {"sort_by": "cost", "descending": 1}, {"unknown": 1}, []]:
            response = client.call("inspect_deck", arguments=invalid)
            evidence["calls"].append({"operation": "inspect_deck", "arguments": invalid, "response": response})
            assert not response["ok"] and response["error"]["code"] == "invalid_request", response
        assert call("get_state") == before, "Invalid options changed the observation."
    summary = call("inspect_deck")
    assert summary["scene"] == "deck" and summary["detail_level"] == "summary", summary
    assert not summary["view_upgrades"] and summary["sort"] == {"by": "obtained", "descending": False}, summary
    basic_fields = {"id", "name", "type", "rarity", "visual_card_pool", "energy_cost", "star_cost"}
    assert all(set(card) == basic_fields for card in summary["deck"]), summary
    assert "hover_tips" not in summary and "notes" not in summary, summary
    assert len(summary["deck"]) == before["top_bar"]["deck_count"], summary
    ids = [card["id"] for card in summary["deck"]]
    assert len(ids) == len(set(ids)) and all(card_id.startswith("deck:") for card_id in ids), ids
    covered = call("get_state")
    assert covered["screen"]["status"] == "covered" and "close_card_view" in covered["available_actions"] and not set(covered["available_actions"]) & GAME_ACTIONS, covered
    if args.exercise_options:
        for operation in ["inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics"]:
            rejected = client.call(operation)
            evidence["calls"].append({"operation": operation, "response": rejected})
            assert not rejected["ok"] and rejected["error"]["code"] == "illegal_action", rejected
        rejected = client.call("inspect_deck", arguments={"detail_level": "bad"})
        assert not rejected["ok"] and rejected["error"]["code"] == "invalid_request", rejected
        assert call("inspect_deck") == summary, "Invalid options changed the open deck."
    full = call("inspect_deck", {"detail_level": "full"})
    assert full["sort"] == summary["sort"] and not full["view_upgrades"], full
    assert [card["id"] for card in full["deck"]] == ids, full
    assert all(set(card) == basic_fields | {"description"} for card in full["deck"]), full
    assert "notes" not in full, full
    for item in (full,):
        tips = item["hover_tips"]
        assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
        assert all(tip["card_ids"] and len(tip["card_ids"]) == len(set(tip["card_ids"]))
                   and set(tip["card_ids"]) <= set(ids) for tip in tips), tips
    upgraded = call("inspect_deck", {"detail_level": "full", "view_upgrades": True})
    assert upgraded["view_upgrades"] and [card["id"] for card in upgraded["deck"]] == ids, upgraded
    retained = call("inspect_deck")
    assert retained["view_upgrades"] and retained["detail_level"] == "summary", retained
    if args.exercise_options:
        strike = next(card for card in full["deck"] if card["name"] == "Strike")
        strike_upgraded = next(card for card in upgraded["deck"] if card["id"] == strike["id"])
        assert strike["description"] == "Deal 6 damage." and strike_upgraded["description"] == "Deal 9 damage.", strike_upgraded
        assert strike_upgraded["name"] == "Strike+", strike_upgraded
        slam = next(card for card in full["deck"] if card["name"] == "Body Slam")
        slam_upgraded = next(card for card in upgraded["deck"] if card["id"] == slam["id"])
        assert slam["energy_cost"] == "1" and slam_upgraded["energy_cost"] == "0", slam_upgraded
        unchanged = {card["id"]: card for card in upgraded["deck"]}
        fixed = [card for card in full["deck"] if card["name"] in {"Ascender's Bane", "Body Slam+"}]
        assert len(fixed) == 2 and all(unchanged[card["id"]] == card for card in fixed)
        for sort_by in ("obtained", "type", "cost", "name"):
            for descending in (False, True):
                sorted_view = call("inspect_deck", {"sort_by": sort_by, "descending": descending})
                assert sorted_view["sort"] == {"by": sort_by, "descending": descending}, sorted_view
                assert sorted_view["view_upgrades"] and {card["id"] for card in sorted_view["deck"]} == set(ids), sorted_view
                if sort_by == "obtained":
                    assert [card["id"] for card in sorted_view["deck"]] == (list(reversed(ids)) if descending else ids)
                assert call("inspect_deck") == sorted_view, "Omitted options reset the current page."
        restored = call("inspect_deck", {"detail_level": "full", "view_upgrades": False, "sort_by": "obtained"})
        assert restored == full, "Returning to normal changed card details."
    closed = call("close_deck")
    assert closed == before, "Closing did not restore the original visible observation."
    after = call("get_state")
    assert after == before, "Gameplay changed during browsing."
    assert evidence["calls"][-1]["response"]["state"]["snapshot_id"] != before_token, "Browsing restored a stale action token."
    if args.exercise_options:
        stale = client.call("end_turn", expected_state=before_token)
        assert not stale["ok"] and stale["error"]["code"] == "stale_state", stale
        evidence["stale_action_after_browsing"] = stale
        rejected = client.call("close_deck")
        assert not rejected["ok"] and rejected["error"]["code"] == "illegal_action", rejected
        evidence["close_when_not_open"] = rejected
        lifecycle = client.call("check_test_deck_lifecycle")
        assert lifecycle["ok"], lifecycle
        assert all(result["passed"] for result in lifecycle["state"]["results"]), lifecycle
        evidence["lifecycle"] = lifecycle
        assert call("get_state") == before, "Lifecycle checks changed gameplay."
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, result in [("deck-summary", summary), ("deck-full", full), ("deck-upgraded", upgraded)]:
        (args.output_dir / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    evidence["completed"] = True
    (args.output_dir / "deck-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: {len(ids)} cards, full and upgrade previews, explicit close; gameplay observation unchanged.")


if __name__ == "__main__":
    main()
