import argparse
import json
from pathlib import Path

from sts2_mcp.roundtrip_client import Client, player_result
from tests.game.support.combatant_assertions import assert_combatant_inspection


def assert_visible_subsequence(actual, observed):
    if actual is None:
        assert observed is None, (actual, observed)
        return
    assert isinstance(observed, list), observed
    remaining = iter(observed)
    for item in actual:
        assert any(item == visible for visible in remaining), (item, observed)


def main():
    parser = argparse.ArgumentParser(description="只读验证当前双方 powers 与敌人意图说明，并导出 JSON。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    before = client.call("get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    inspected = client.call("inspect_combatants")
    assert inspected["ok"], inspected
    repeated = client.call("inspect_combatants")
    assert repeated["ok"] and player_result(inspected) == player_result(repeated), repeated
    after = client.call("get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, inspected, repeated, after)}) == 1, "Observation changed."
    result = player_result(inspected)
    assert_combatant_inspection(result, player_result(before))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before, "inspection": inspected,
                                     "repeated": repeated, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(result['enemies'])} enemies and {len(tips)} shared tips; observation unchanged; JSON: {args.output}")


if __name__ == "__main__":
    main()
