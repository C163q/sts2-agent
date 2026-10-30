import argparse
import json
import time
from pathlib import Path

from roundtrip_client import Client, player_result


def verify(state):
    assert state["schema_version"] == 6, state
    assert state["language"] == "en", state
    assert "phase" not in state and "side" not in state, state
    assert state["screen"]["status"] == "visible", state
    player = state["player"]
    assert player["character"] == "IRONCLAD", player
    assert player["hp"] == player["max_hp"] == 80, player
    assert player["energy"] == player["max_energy"] == 3, player
    assert len(player["hand"]) == 5 and player["draw_count"] == 5, player
    assert player["discard_count"] == 0, player
    assert all(card["name"] and card["energy_cost"] in ("1", "2") for card in player["hand"]), player
    assert len(state["enemies"]) == 3, state
    assert all(enemy["name"] and enemy["hp"] == enemy["max_hp"] for enemy in state["enemies"]), state
    assert any(enemy["intents"] for enemy in state["enemies"]), state
    assert state["top_bar"]["gold"] == 99, state
    assert state["top_bar"]["deck_count"] == 10, state
    assert len(state["top_bar"]["potion_slots"]) == 3, state
    assert state["top_bar"]["relics"][0]["name"] == "Burning Blood", state
    assert "overlay" not in state, state
    assert len({card["id"] for card in player["hand"]}) == 5, player
    assert all(card["type"] in ("Attack", "Skill") for card in player["hand"]), player
    assert all(card["rarity"] == "basic" and card["visual_card_pool"] == "ironclad" for card in player["hand"]), player
    assert all("energy_cost_color" not in card and "star_cost_color" not in card for card in player["hand"]), player
    assert all(card["unplayable_markers"] == [] for card in player["hand"]), player
    assert all(slot is None for slot in state["top_bar"]["potion_slots"]), state
    assert isinstance(state["top_bar"]["bosses"], list), state
    assert player["hp_display"] == "numeric", state
    assert state["buttons"]["end_turn"]["text"] == "End Turn 1", state
    assert all(card["outline"] == "cyan" for card in player["hand"]), state
    forbidden = {"description", "effects", "dynamic_vars", "next_move", "rng_state", "draw_order",
                 "target_rules", "phase", "side", "pile_contents", "model", "position", "hp_text", "hp_infinite",
                 "energy_unplayable_marker", "star_unplayable_marker"}

    def check(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value), value
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(state)


def main():
    parser = argparse.ArgumentParser(description="在独立临时战斗中检查可见观察 JSON。")
    parser.add_argument("--ipc-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    response = client.call("get_state")
    assert response["ok"], response
    deadline = time.monotonic() + 30
    while response["state"]["scene"] == "loading_or_noncombat" and time.monotonic() < deadline:
        time.sleep(0.25)
        response = client.call("get_state")
        assert response["ok"], response
    if response["state"]["scene"] == "main_menu":
        response = client.call("start_test_combat", response["state"]["snapshot_id"])
        assert response["ok"], response
    # Wait for the entrance animations without changing the combat.
    time.sleep(3)
    response = client.call("get_state")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(player_result(response), indent=2, ensure_ascii=False) + "\n")
    assert response["ok"], response
    verify(response["state"])
    print(f"PASS: visible English combat observation saved to {args.output}", flush=True)


if __name__ == "__main__":
    main()
