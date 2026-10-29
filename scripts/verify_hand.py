import argparse
import json
from pathlib import Path

from roundtrip_client import Client, player_result


def main():
    parser = argparse.ArgumentParser(description="只读验证当前手牌详情并导出面向 LLM 的 JSON。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    client = Client(args.ipc_dir)
    before = client.call("get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    inspection = client.call("inspect_hand")
    assert inspection["ok"], inspection
    after = client.call("get_state")
    assert after["ok"], after
    assert before["state"]["snapshot_id"] == after["state"]["snapshot_id"], "Game state changed during inspection."
    result = player_result(inspection)
    hand = result["hand"]
    basic = before["state"]["player"]["hand"]
    assert [card["id"] for card in hand] == [card["id"] for card in basic], (hand, basic)
    for card in hand:
        assert "hover_tips" not in card, card
        if card["type"] is None:
            assert card["description"] is None, card
            continue
        assert isinstance(card["description"], str), card
        assert "[gold]" not in card["description"] and "[img]" not in card["description"], card
    tips = result["hover_tips"]
    assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
    for tip in tips:
        assert tip["card_ids"] and len(tip["card_ids"]) == len(set(tip["card_ids"])), tip
    raw_links = {(card["id"], tip["title"], tip["description"])
                 for card in inspection["state"]["hand"] for tip in card["hover_tips"] or []}
    shared_links = {(card_id, tip["title"], tip["description"])
                    for tip in tips for card_id in tip["card_ids"]}
    assert shared_links == raw_links, (shared_links, raw_links)
    if hand:
        assert set(result) == {"hand", "hover_tips", "notes"}, result
        assert set(result["notes"]) == {"card_values"}, result
    else:
        assert result == {"hand": [], "hover_tips": []}, result
    assert all("description" not in card for card in basic), basic
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before,
        "inspection": inspection, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(hand)} cards inspected without changing the observation; JSON: {args.output}")


if __name__ == "__main__":
    main()
