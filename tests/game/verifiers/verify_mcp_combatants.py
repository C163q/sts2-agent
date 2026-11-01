from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.roundtrip_client import Client, player_result
from tests.game.verifiers.verify_combatants import assert_visible_subsequence


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    reference = await asyncio.to_thread(client.call, "inspect_combatants")
    assert reference["ok"], reference
    parameters = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), "--ipc-dir", str(args.ipc_dir.resolve())])
    evidence = {"completed": False, "before": before, "reference": reference, "calls": []}
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            initialized = await session.initialize()
            evidence["protocol_version"] = initialized.protocolVersion
            evidence["server"] = initialized.serverInfo.model_dump()
            listed = await session.list_tools()
            evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]
            assert {tool.name for tool in listed.tools} == {
                "get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map", "end_turn"}
            tool = next(tool for tool in listed.tools if tool.name == "inspect_combatants")
            assert tool.annotations.readOnlyHint is True
            assert tool.inputSchema == {"type": "object", "properties": {}, "additionalProperties": False}

            async def call(name):
                result = await session.call_tool(name, {})
                evidence["calls"].append({"name": name, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            inspected = await call("inspect_combatants")
            observed = await call("get_observation")
            repeated = await call("inspect_combatants")
            assert inspected == repeated == player_result(reference), "Combatants changed or MCP differs from file inspection."
            expected = {"scene", "player", "enemies", "hover_tips"}
            if any(enemy["intents"] for enemy in inspected["enemies"]):
                expected.add("notes")
                assert set(inspected["notes"]) == {"enemy_attack_intents"}, inspected
            assert set(inspected) == expected and inspected["scene"] == "combat", inspected
            if inspected["player"] is not None:
                assert set(inspected["player"]) == {"powers"}, inspected["player"]
                assert_visible_subsequence(inspected["player"]["powers"], observed["player"]["powers"])
            basic = {enemy["id"]: enemy for enemy in observed["enemies"]}
            for enemy in inspected["enemies"]:
                assert set(enemy) == {"id", "name", "powers", "intents"}, enemy
                assert enemy["name"] == basic[enemy["id"]]["name"], enemy
                for field in ("powers", "intents"):
                    assert_visible_subsequence(enemy[field], basic[enemy["id"]][field])
            tips = inspected["hover_tips"]
            assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
            for tip in tips:
                assert set(tip) == {"title", "description", "sources"}, tip
                assert tip["sources"] and len(tip["sources"]) == len(set(tip["sources"])), tip
                for source in tip["sources"]:
                    value = inspected
                    for part in source.split("."):
                        value = value[int(part)] if isinstance(value, list) else value[part]
                    assert isinstance(value, dict), (source, value)
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, reference, after)}) == 1, "Observation changed."
    evidence.update(completed=True, after=after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inspected, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: real stdio MCP inspected {len(inspected['enemies'])} enemies and {len(tips)} shared tips; "
          f"game observation unchanged; JSON: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 只读验证双方 powers 和敌人意图，不执行游戏动作。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
