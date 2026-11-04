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

from sts2_mcp.roundtrip_client import Client
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.tool_registry import SPECS
from tests.game.support.potion_assertions import assert_potion_inspection


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["top_bar"] is not None, before
    reference = await asyncio.to_thread(client.call, "inspect_potions")
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
            required = {spec.name for spec in SPECS if spec.category != 'screenshot'}
            actual = {tool.name for tool in listed.tools}
            assert required <= actual <= required | {'capture_screenshot'}, (required, actual)
            tool = next(tool for tool in listed.tools if tool.name == "inspect_potions")
            assert tool.annotations.readOnlyHint is True
            assert set(tool.inputSchema['properties']) == {'preset', 'slot_indices'} and not tool.inputSchema['additionalProperties']

            async def call(name):
                result = await session.call_tool(name, full_output_arguments(name, {}))
                evidence["calls"].append({"name": name, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            inspected = await call("inspect_potions")
            observed = await call("get_observation")
            repeated = await call("inspect_potions")
            assert inspected == repeated == decode_success('inspect_potions', reference['state'])
            assert_potion_inspection(inspected, reference['state'], observed)
            slots, tips = inspected['potion_slots'], inspected['hover_tips']
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, reference, after)}) == 1, "Observation changed."
    evidence.update(completed=True, after=after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inspected, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: real stdio MCP inspected {len(slots)} potion slots and {len(tips)} shared tips; "
          f"game observation unchanged; JSON: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 只读验证当前药水说明，不执行游戏动作。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
