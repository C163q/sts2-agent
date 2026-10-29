import argparse
import json
from pathlib import Path

from roundtrip_client import Client, player_result


def main():
    parser = argparse.ArgumentParser(description="只读验证当前界面说明并导出面向 LLM 的 JSON。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    before = client.call("get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    inspection = client.call("inspect_ui")
    assert inspection["ok"], inspection
    after = client.call("get_state")
    assert after["ok"], after
    assert before["state"]["snapshot_id"] == inspection["state"]["snapshot_id"] == after["state"]["snapshot_id"], "Game state changed during inspection."
    result = player_result(inspection)
    assert set(result) == {"scene", "hover_tips"} and result["scene"] == "combat", result
    tips = result["hover_tips"]
    assert isinstance(tips, list), tips
    assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
    for tip in tips:
        assert set(tip) == {"title", "description", "sources"}, tip
        assert tip["title"] is None or isinstance(tip["title"], str), tip
        assert isinstance(tip["description"], str), tip
        assert "[img]" not in tip["description"] and "[gold]" not in tip["description"], tip
        assert tip["sources"] and len(tip["sources"]) == len(set(tip["sources"])), tip
        for source in tip["sources"]:
            assert not any(word in source for word in ("potion", "power", "relic", "intent", "hand", "block")), source
            observed = before["state"]
            for component in source.split("."):
                observed = observed[component]
            if source.endswith("_visible"):
                assert observed is True, (source, observed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before,
        "inspection": inspection, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(tips)} UI tips inspected without changing the observation; JSON: {args.output}")


if __name__ == "__main__":
    main()
