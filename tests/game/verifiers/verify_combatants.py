import argparse
import json
from pathlib import Path

from sts2_mcp.roundtrip_client import Client, player_result


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
    expected = {"scene", "player", "enemies", "hover_tips"}
    if any(enemy.get("intents") for enemy in result["enemies"]):
        expected.add("notes")
        assert set(result["notes"]) == {"enemy_attack_intents"}, result
    assert set(result) == expected and result["scene"] == "combat", result
    if result["player"] is not None:
        assert set(result["player"]) == {"powers", "orb_slots"}, result["player"]
        assert_visible_subsequence(result["player"]["powers"], before["state"]["player"]["powers"])
        assert result['player']['orb_slots'] == before['state']['player']['orb_slots'], result['player']
    observed = {enemy["id"]: enemy for enemy in before["state"]["enemies"]}
    for enemy in result["enemies"]:
        assert set(enemy) == {"id", "name", "powers", "intents"}, enemy
        basic = observed[enemy["id"]]
        assert enemy["name"] == basic["name"], enemy
        for field in ("powers", "intents"):
            assert_visible_subsequence(enemy[field], basic[field])
    tips = result["hover_tips"]
    assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
    for tip in tips:
        assert set(tip) == {"title", "description", "sources"}, tip
        assert isinstance(tip["description"], str), tip
        assert "[img]" not in tip["description"] and "[gold]" not in tip["description"], tip
        assert tip["sources"] and len(tip["sources"]) == len(set(tip["sources"])), tip
        for source in tip["sources"]:
            assert (".powers." in source or source.startswith('player.orb_slots.')
                    or (source.startswith("enemies.") and ".intents." in source)), source
            value = result
            for part in source.split("."):
                value = value[int(part)] if isinstance(value, list) else value[part]
            assert isinstance(value, dict), (source, value)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({"completed": True, "before": before, "inspection": inspected,
                                     "repeated": repeated, "after": after}, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: {len(result['enemies'])} enemies and {len(tips)} shared tips; observation unchanged; JSON: {args.output}")


if __name__ == "__main__":
    main()
