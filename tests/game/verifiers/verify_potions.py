import argparse
import json
from pathlib import Path

from sts2_mcp.roundtrip_client import Client
from sts2_mcp.output.response_pipeline import decode_success
from tests.game.support.potion_assertions import assert_potion_inspection


def main():
    parser = argparse.ArgumentParser(description="只读验证当前药水栏位与英语说明，并导出 JSON。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    before = client.call("get_state")
    assert before["ok"] and before["state"]["top_bar"] is not None, before
    inspection = client.call("inspect_potions")
    assert inspection["ok"], inspection
    after = client.call("get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, inspection, after)}) == 1, "Observation changed."
    result = decode_success('inspect_potions', inspection['state'])
    assert_potion_inspection(result, inspection['state'], before['state'])
    slots, tips = result['potion_slots'], result['hover_tips']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before,
        "inspection": inspection, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(slots)} potion slots, {len(tips)} shared tips; observation unchanged; JSON: {args.output}")


if __name__ == "__main__":
    main()
