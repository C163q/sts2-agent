import argparse
import json
from pathlib import Path

from roundtrip_client import Client, player_result


def main():
    parser = argparse.ArgumentParser(description="只读验证当前药水栏位与英语说明，并导出 JSON。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    before = client.call("get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    inspection = client.call("inspect_potions")
    assert inspection["ok"], inspection
    after = client.call("get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, inspection, after)}) == 1, "Observation changed."
    result = player_result(inspection)
    assert set(result) == {"slot_tip", "potion_slots", "hover_tips"}, result
    common = result["slot_tip"]
    assert set(common) == {"title", "description"} and isinstance(common["description"], str), common
    assert json.dumps(result).count(json.dumps(common["description"])) == 1, result
    slots = result["potion_slots"]
    basic = before["state"]["top_bar"]["potion_slots"]
    assert len(slots) == len(basic), (slots, basic)
    for potion, observed in zip(slots, basic):
        if observed is None:
            assert potion is None, potion
        else:
            assert potion and set(potion) == {"name", "description"}, potion
            assert potion["name"] == observed["name"] and isinstance(potion["description"], str), potion
            assert "[img]" not in potion["description"] and "[gold]" not in potion["description"], potion
    tips = result["hover_tips"]
    assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
    raw_links = {(index, tip["title"], tip["description"])
                 for index, potion in enumerate(inspection["state"]["potion_slots"]) if potion
                 for tip in potion["hover_tips"]}
    links = {(index, tip["title"], tip["description"]) for tip in tips for index in tip["slot_indices"]}
    assert links == raw_links, (links, raw_links)
    for tip in tips:
        assert set(tip) == {"title", "description", "slot_indices"}, tip
        assert tip["slot_indices"] and len(tip["slot_indices"]) == len(set(tip["slot_indices"])), tip
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before,
        "inspection": inspection, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(slots)} potion slots, {len(tips)} shared tips; observation unchanged; JSON: {args.output}")


if __name__ == "__main__":
    main()
