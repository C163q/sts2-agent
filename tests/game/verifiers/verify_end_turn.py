from scripts._bootstrap import ROOT
import argparse
import json
import time
from pathlib import Path

from sts2_mcp.roundtrip_client import Client
from sts2_mcp.output.transition_details import end_turn_details


EXPECTED = {
    "normal": "player_ready", "wither": "player_ready", "wither_death": "combat_lost",
    "enemy_death": "combat_lost", "tyranny": "choice_required", "retain_choice": "choice_required",
    "boulder": "combat_won", "doom": "combat_won", "stampede": "combat_won",
    "revive": "player_ready", "blocked": "player_ready",
    "hellraiser": "player_ready", "exhaust_block": "player_ready", "hidden_hp": "player_ready",
}


def main():
    parser = argparse.ArgumentParser(description="验证已启动独立测试实例中的结束回合机制。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--scenario", required=True, choices=EXPECTED)
    args = parser.parse_args()
    directory = args.ipc_dir.expanduser().resolve()
    if directory != ROOT / ".tmp" / "roundtrip" / "ipc":
        raise SystemExit("本验证仅允许 .tmp/roundtrip/ipc，不能操作正式对局。")
    client = Client(directory)
    evidence = []

    def call(operation, token=None):
        response = client.call(operation, token)
        evidence.append({"operation": operation, "response": response})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
        assert response["ok"], response
        return response["state"]

    observed = call("get_state")
    deadline = time.monotonic() + 30
    while observed["scene"] == "unrecognized" and time.monotonic() < deadline:
        time.sleep(0.25)
        observed = call("get_state")
    assert observed["scene"] == "main_menu", "须从带匹配 --turn-scenario 参数的新测试实例主菜单执行。"
    call("start_test_combat", observed["snapshot_id"])
    observed = call("get_state")
    result = end_turn_details(call("end_turn", observed["snapshot_id"]))
    history = [result["transition"]]
    if args.scenario == "revive":
        for _ in range(3):
            if any(e["type"] == "revived" for e in history[-1]["events"]):
                break
            observed = call("get_state")
            result = end_turn_details(call("end_turn", observed["snapshot_id"]))
            history.append(result["transition"])
    transition = history[-1]
    assert transition["stop_reason"] == EXPECTED[args.scenario], transition
    assert all(t["complete"] for t in history), history
    events = transition["events"]
    kinds = [e["type"] for e in events]

    def source(kind, name):
        return any(e["type"] == kind and e.get("source") and e["source"]["name"] == name for e in events)

    if args.scenario in ("wither", "wither_death"):
        assert source("damage", "Wither"), transition
    if args.scenario in ("wither_death", "enemy_death"):
        assert "damage" in kinds and "died" in kinds, transition
    if args.scenario == "stampede":
        assert source("card_played", "Stampede"), transition
        assert any(e["type"] == "card_played" and e["autoplay"] for e in events), transition
    if args.scenario in ("stampede", "boulder"):
        assert "damage" in kinds and "died" in kinds, transition
    if args.scenario == "doom":
        assert source("died", "Doom"), transition
    if args.scenario == "revive":
        assert any(e["type"] == "died" for t in history for e in t["events"]), history
        assert "revived" in kinds, transition
    if args.scenario == "blocked":
        assert any(e["type"] == "damage" and e["blocked"] > 0 and e["hp_loss"] == 0 for e in events), transition
    if args.scenario in ("tyranny", "retain_choice"):
        assert "end_turn" not in result["available_actions"] and result["selection"]["status"] == "visible", result
        assert "select_card" in result["available_actions"], result
    if args.scenario == "hellraiser":
        plays = [e for e in events if e["type"] == "card_played" and e["autoplay"]]
        assert plays, transition
        for play in plays:
            assert any(e["type"] == "card_drawn" and e["card"]["id"] == play["card"]["id"]
                       and e["sequence"] < play["sequence"] for e in events), transition
    if args.scenario == "exhaust_block":
        exhausted = next(e for e in events if e["type"] == "card_exhausted" and e["card"]["name"] == "Dazed")
        gained = next(e for e in events if e["type"] == "block_changed" and e["after"] > e["before"])
        assert exhausted["sequence"] < gained["sequence"], transition
    if args.scenario == "hidden_hp":
        hidden = [enemy["id"] for enemy in observed["enemies"] if enemy["hp_display"] == "infinite"]
        assert hidden, observed
        assert not any(e["type"] == "hp_changed" and e["target"]["id"] in hidden for e in events), transition
    print(f"PASS {args.scenario}: {transition['stop_reason']}, {len(events)} events")


if __name__ == "__main__":
    main()
