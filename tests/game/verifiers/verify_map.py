from scripts._bootstrap import ROOT
import argparse
import json
from pathlib import Path

from sts2_mcp.roundtrip_client import Client, player_result


def main():
    parser = argparse.ArgumentParser(description="打开整张当前幕地图、重复查看并关闭，不选路或推进回合。")
    parser.add_argument("--ipc-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--exercise-cases", action="store_true")
    args = parser.parse_args()
    root = ROOT
    if args.exercise_cases and args.ipc_dir.resolve() != (root / ".tmp/roundtrip/ipc").resolve():
        parser.error("原生测试场景仅允许独立实例。")
    client = Client(args.ipc_dir)
    evidence = []
    args.output_dir.mkdir(parents=True, exist_ok=True)

    def call(operation):
        response = client.call(operation)
        evidence.append({"operation": operation, "response": response})
        assert response["ok"], response
        return player_result(response)

    before = call("get_state")
    assert before["scene"] == "combat" and before["screen"] == {"status": "visible"}, before
    viewed = call("inspect_map")
    assert viewed["scene"] == before["scene"] and viewed["screen"] == {"status": "visible", "view": "map"}, viewed
    assert viewed["nodes"] and not viewed["can_travel"] and viewed["selectable_nodes"] == [], viewed
    ids = [node["id"] for node in viewed["nodes"]]
    assert len(ids) == len(set(ids))
    assert viewed["current_node"] is None or viewed["current_node"] in ids
    assert all(target in ids for node in viewed["nodes"] for target in node["next"])
    assert "notes" not in viewed and "available_actions" not in viewed
    assert call("inspect_map") == viewed
    (args.output_dir / "map-inspection.json").write_text(json.dumps(viewed, ensure_ascii=False, indent=2) + "\n")
    call("close_map")
    assert call("get_state") == before, "Map browsing changed gameplay."
    if args.exercise_cases:
        response = client.call("check_test_map")
        evidence.append({"operation": "check_test_map", "response": response})
        assert response["ok"], response
        checks = response["state"]
        assert checks["results"] and all(item["passed"] for item in checks["results"]), checks
        native = json.loads((args.ipc_dir.parent / "map-checks.json").read_text())
        for sample in native.get("samples", []):
            (args.output_dir / (sample["name"] + ".json")).write_text(
                json.dumps(player_result({"ok": True, "state": sample["state"]}), ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "map-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("PASS: full current-act map browsing preserved gameplay."
          + (" Isolated native checks passed." if args.exercise_cases else ""))


if __name__ == "__main__":
    main()
