import argparse
import json
from pathlib import Path

from sts2_mcp.roundtrip_client import Client


def main():
    parser = argparse.ArgumentParser(description="仅在独立测试战斗中验证跨回合重抽的卡牌 ID。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--roundtrip-report", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    # Require evidence of this exact process's explicitly created test fixture.
    original = json.loads(args.roundtrip_report.read_text())
    setup = next(e["response"]["state"] for e in original if e["operation"] == "start_test_combat" and e["response"]["ok"])
    client = Client(args.ipc_dir)
    response = client.call("get_state")
    assert response["ok"], response
    state = response["state"]
    assert state["session"] == setup["session"] and state["combat_generation"] == setup["combat_generation"], state
    known = {card["id"]: card["name"] for card in setup["player"]["hand"]}
    first_ids = set(known)
    evidence = []
    for _ in range(3):
        assert "end_turn" in state["available_actions"], state
        response = client.call("end_turn", state["snapshot_id"])
        assert response["ok"], response
        state = response["state"]
        evidence.append(response)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
        hand = state["player"]["hand"]
        assert len({card["id"] for card in hand}) == len(hand), hand
        for card in hand:
            if card["id"] in known:
                assert card["name"] == known[card["id"]], (known, card)
            known[card["id"]] = card["name"]
        repeated = first_ids.intersection(card["id"] for card in hand)
        if repeated:
            readback = client.call("get_state")
            assert readback["ok"], readback
            assert readback["state"]["player"]["hand"] == hand, (state, readback)
            print(f"PASS: previously drawn card IDs {sorted(repeated)} reused on turn {state['turn']}")
            return
    raise AssertionError("The test fixture did not redraw an original card within three extra turns.")


if __name__ == "__main__":
    main()
