from scripts._bootstrap import ROOT
import argparse
import json
from pathlib import Path

from sts2_mcp.roundtrip_client import Client, player_result
from sts2_mcp.output.card_format import browse_result


def main():
    parser = argparse.ArgumentParser(description="真实点击并读取三类战斗牌堆，不出牌或结束回合。")
    parser.add_argument("--ipc-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exercise-cases", action="store_true", help="仅独立实例：原生空堆、替换与生命周期检查")
    args = parser.parse_args()
    root = ROOT
    if args.exercise_cases and args.ipc_dir.resolve() != (root / ".tmp/roundtrip/ipc").resolve():
        parser.error("原生测试场景仅允许独立实例。")
    client = Client(args.ipc_dir)
    evidence = []
    args.output_dir.mkdir(parents=True, exist_ok=True)

    def call(operation, arguments=None):
        options = dict(arguments or {})
        preset = options.pop('preset', 'full')
        response = client.call(operation, arguments=options or None)
        evidence.append({"operation": operation, "arguments": arguments, "response": response})
        assert response["ok"], response
        return browse_result(response, operation, options, preset) if operation in {'inspect_deck', 'inspect_pile'} else player_result(response)

    before = call("get_state")
    assert before["scene"] == "combat" and before["screen"] == {"status": "visible"}, before
    for pile in ("draw", "discard", "exhaust"):
        summary = call("inspect_pile", {"pile": pile, "preset": "summary"})
        assert summary["pile"] == pile and "detail_level" not in summary, summary
        assert "hover_tips" not in summary and "notes" not in summary
        if summary["status"] == "opened":
            assert summary["cards"] and all("description" not in card for card in summary["cards"])
            full = call("inspect_pile", {"pile": pile, "preset": "full"})
            assert [card["id"] for card in full["cards"]] == [card["id"] for card in summary["cards"]]
            assert "hover_tips" in full and all("description" in card for card in full["cards"])
            assert call("inspect_pile", {"pile": pile, "preset": "summary"}) == summary
            call("close_card_view")
            (args.output_dir / (pile + "-full.json")).write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n")
        elif summary["status"] == "empty":
            assert summary["cards"] == [] and summary["screen"] == {"status": "visible"}
        else:
            assert summary["status"] == "unavailable" and summary["cards"] is None
        (args.output_dir / (pile + "-summary.json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    assert call("get_state") == before, "Pile browsing changed gameplay."
    if args.exercise_cases:
        response = client.call("check_test_piles")
        evidence.append({"operation": "check_test_piles", "response": response})
        assert response["ok"], response
        checks = response["state"]
        assert checks["results"] and all(result["passed"] for result in checks["results"]), checks
        native = json.loads((args.ipc_dir.parent / "pile-checks.json").read_text())
        for entry in native["calls"]:
            if entry["operation"] != "inspect_pile" or not entry["response"]["ok"]:
                continue
            sample = player_result(entry["response"])
            name = "-".join(sample[key] for key in ("pile", "status"))
            (args.output_dir / (name + ".json")).write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "pile-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("PASS: all three pile outcomes, repeated summary/full and explicit close; gameplay unchanged.")


if __name__ == "__main__":
    main()
