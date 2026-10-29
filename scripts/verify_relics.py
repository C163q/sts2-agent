import argparse
import json
from pathlib import Path

from roundtrip_client import Client, player_result
from verify_combatants import assert_visible_subsequence


def main():
    parser = argparse.ArgumentParser(description="只读验证当前可见遗物的英语详情，并导出 JSON。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    before = client.call("get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    inspected = client.call("inspect_relics")
    assert inspected["ok"], inspected
    repeated = client.call("inspect_relics")
    assert repeated["ok"] and player_result(inspected) == player_result(repeated), repeated
    after = client.call("get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, inspected, repeated, after)}) == 1, "Observation changed."
    result = player_result(inspected)
    assert set(result) == {"relics", "hover_tips"}, result
    assert_visible_subsequence([{key: item[key] for key in ("name", "counter")} for item in result["relics"]],
                               before["state"]["top_bar"]["relics"])
    for item in result["relics"]:
        assert set(item) == {"name", "counter", "description"}, item
        assert isinstance(item["name"], str) and isinstance(item["description"], str), item
        assert item["counter"] is None or type(item["counter"]) is int, item
        assert "[img]" not in item["description"] and "[gold]" not in item["description"], item
    tips = result["hover_tips"]
    assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
    for tip in tips:
        assert set(tip) == {"title", "description", "relic_indices"}, tip
        assert isinstance(tip["description"], str), tip
        indices = tip["relic_indices"]
        assert indices and len(indices) == len(set(indices)), tip
        assert all(type(index) is int and 0 <= index < len(result["relics"]) for index in indices), tip
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before, "inspection": inspected,
                                     "repeated": repeated, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(result['relics'])} relics and {len(tips)} shared tips; observation unchanged; JSON: {args.output}")


if __name__ == "__main__":
    main()
