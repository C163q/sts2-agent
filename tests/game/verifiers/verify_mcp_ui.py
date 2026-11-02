from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.roundtrip_client import Client, player_result


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    reference = await asyncio.to_thread(client.call, "inspect_ui")
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
            assert {tool.name for tool in listed.tools} == {"get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map", "end_turn"}
            tool = next(tool for tool in listed.tools if tool.name == "inspect_ui")
            assert tool.annotations.readOnlyHint is True
            assert set(tool.inputSchema['properties']) == {'preset'} and not tool.inputSchema['additionalProperties']

            async def call(name):
                result = await session.call_tool(name, full_output_arguments(name, {}))
                evidence["calls"].append({"name": name, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            inspected = await call("inspect_ui")
            observed = await call("get_observation")
            repeated = await call("inspect_ui")
            assert inspected == repeated == player_result(reference), "UI changed or MCP output differs from file inspection."
            assert observed["scene"] == "combat"
            assert set(inspected) == {"scene", "hover_tips"} and inspected["scene"] == "combat", inspected
            for tip in inspected["hover_tips"]:
                assert set(tip) == {"title", "description", "sources"}, tip
                for source in tip["sources"]:
                    value = observed
                    for part in source.split("."):
                        value = value[part]
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"], after
    assert before["state"]["snapshot_id"] == reference["state"]["snapshot_id"] == after["state"]["snapshot_id"], "Game observation changed."
    evidence.update(completed=True, after=after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inspected, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: real stdio MCP inspected {len(inspected['hover_tips'])} UI tips; game observation unchanged; JSON: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 只读验证当前界面说明，不执行游戏动作。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
