import argparse
import json
import time
import uuid
from pathlib import Path

from sts2_mcp.roundtrip_client import Client, player_result


def main():
    parser = argparse.ArgumentParser(description="在独立游戏实例中验证状态与动作往返。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--observation-output", type=Path, help="在首回合另存并校验英语可见观察")
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    evidence = []

    def call(operation, state=None, request_id=None):
        response = client.call(operation, state, request_id)
        evidence.append({"operation": operation, "response": response})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + "\n")
        print(operation, response.get("ok"), response.get("error", {}).get("code", ""), flush=True)
        return response

    observed = call("get_state")
    assert observed["ok"], observed
    state = observed["state"]
    deadline = time.monotonic() + 30
    while state["scene"] == "unrecognized" and time.monotonic() < deadline:
        time.sleep(0.25)
        observed = call("get_state")
        assert observed["ok"], observed
        state = observed["state"]
    assert state["scene"] == "main_menu", "完整验证须从新启动实例的主菜单执行。"
    illegal = call("end_turn", state["snapshot_id"])
    assert not illegal["ok"] and illegal["error"]["code"] == "illegal_action", illegal
    setup = call("start_test_combat", state["snapshot_id"])
    assert setup["ok"], setup
    state = setup["state"]
    assert state["scene"] == "combat" and "end_turn" in state["available_actions"], state
    if args.observation_output:
        from tests.game.verifiers.verify_observation import verify
        time.sleep(3)
        response = call("get_state")
        assert response["ok"], response
        state = response["state"]
        verify(state)
        args.observation_output.parent.mkdir(parents=True, exist_ok=True)
        args.observation_output.write_text(json.dumps(player_result(response), indent=2, ensure_ascii=False) + "\n")
    before = state
    before_ids = {card["id"] for card in state["player"]["hand"]}
    assert len(before_ids) == len(state["player"]["hand"])
    assert player_result(illegal)["error"]["recovery"] == "get_state"

    invalid = call("end_turn", "invalid-snapshot")
    assert not invalid["ok"] and invalid["error"]["code"] == "stale_state", invalid
    unchanged = call("get_state")["state"]
    assert unchanged["snapshot_id"] == before["snapshot_id"], (before, unchanged)

    request_id = uuid.uuid4().hex
    executed = call("end_turn", before["snapshot_id"], request_id)
    assert executed["ok"], executed
    after = executed["state"]
    assert after["scene"] == "combat" and after["turn"] == before["turn"] + 1, (before, after)
    assert after["snapshot_id"] != before["snapshot_id"], (before, after)
    readback = call("get_state")["state"]
    assert readback["snapshot_id"] == after["snapshot_id"], (after, readback)

    stale = call("end_turn", before["snapshot_id"])
    assert not stale["ok"] and stale["error"]["code"] == "stale_state", stale
    replay = call("end_turn", before["snapshot_id"], request_id)
    assert replay == executed, (replay, executed)
    duplicate_path = args.ipc_dir / "requests" / (request_id + ".json")
    deadline = time.monotonic() + 5
    while duplicate_path.exists() and time.monotonic() < deadline:
        time.sleep(0.025)
    assert not duplicate_path.exists(), "Duplicate request was not consumed."
    final = call("get_state")["state"]
    assert [card["id"] for card in final["player"]["hand"]] == [card["id"] for card in after["player"]["hand"]]
    assert final["turn"] == after["turn"] and final["snapshot_id"] == after["snapshot_id"], final
    print(f'PASS: turn {before["turn"]} -> {after["turn"]}; '
          f'HP {before["player"]["hp"]} -> {after["player"]["hp"]}; '
          'readback, illegal/stale requests and duplicate request verified', flush=True)


if __name__ == "__main__":
    main()
