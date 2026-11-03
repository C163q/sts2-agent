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
from tests.game.support.combatant_assertions import assert_combatant_inspection
from sts2_mcp.mcp_catalog import tool_definitions


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    reference = await asyncio.to_thread(client.call, "inspect_combatants")
    assert reference["ok"], reference
    config = args.report.with_suffix('.config.json')
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({'screenshots': {'enabled': False}}))
    parameters = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), "--ipc-dir", str(args.ipc_dir.resolve()), "--config", str(config)])
    evidence = {"completed": False, "before": before, "reference": reference, "calls": []}
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            initialized = await session.initialize()
            evidence["protocol_version"] = initialized.protocolVersion
            evidence["server"] = initialized.serverInfo.model_dump()
            listed = await session.list_tools()
            evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]
            assert {tool.name for tool in listed.tools} == {tool.name for tool in tool_definitions()}
            tool = next(tool for tool in listed.tools if tool.name == "inspect_combatants")
            assert tool.annotations.readOnlyHint is True
            assert set(tool.inputSchema['properties']) == {'preset', 'sources'} and not tool.inputSchema['additionalProperties']

            async def call(name):
                result = await session.call_tool(name, full_output_arguments(name, {}))
                evidence["calls"].append({"name": name, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            inspected = await call("inspect_combatants")
            observed = await call("get_observation")
            repeated = await call("inspect_combatants")
            assert inspected == repeated == player_result(reference, operation="inspect_combatants"), "Combatants changed or MCP differs from file inspection."
            assert_combatant_inspection(inspected, observed)
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, reference, after)}) == 1, "Observation changed."
    evidence.update(completed=True, after=after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inspected, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: real stdio MCP inspected {len(inspected['enemies'])} enemies and {len(inspected['hover_tips'])} shared tips; "
          f"game observation unchanged; JSON: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 只读验证双方 powers 和敌人意图，不执行游戏动作。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
