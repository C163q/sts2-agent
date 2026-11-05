from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from sts2_mcp.output.available_tools import GAME_ACTIONS
import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.output.map_details import map_details
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.roundtrip_client import Client
from sts2_mcp.output.response_pipeline import decode_success


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["scene"] == "combat" and before["state"]["screen"] == {"status": "visible"}, before
    evidence = {"completed": False, "before": before, "calls": [], "references": []}
    sample = None
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try:
        parameters = StdioServerParameters(command=sys.executable, args=[
            str((ROOT / "scripts/mcp_server.py")), "--ipc-dir", str(args.ipc_dir.resolve())])
        async with stdio_client(parameters) as (read, write):
            async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
                initialized = await session.initialize()
                evidence.update(protocol_version=initialized.protocolVersion, server=initialized.serverInfo.model_dump())
                listed = await session.list_tools()
                names = {tool.name for tool in listed.tools}
                assert names == {tool.name for tool in tool_definitions(screenshots_enabled="capture_screenshot" in names)}, names
                for tool in listed.tools:
                    if tool.name in {"inspect_map", "close_map"}:
                        if tool.name == 'inspect_map':
                            assert set(tool.inputSchema['properties']) == {'preset', 'max_steps'}
                        else:
                            assert set(tool.inputSchema['properties']) == {'preset'} and not tool.inputSchema['additionalProperties']
                        assert tool.annotations.readOnlyHint is False and tool.annotations.destructiveHint is False
                        assert tool.annotations.idempotentHint is False and tool.annotations.openWorldHint is False
                evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]

                async def call(name, arguments=None, error=None):
                    result = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                    evidence["calls"].append({"name": name, "arguments": arguments, "result": result.model_dump(exclude_none=True)})
                    assert json.loads(result.content[0].text) == result.structuredContent
                    if error:
                        assert result.isError and result.structuredContent["error"]["code"] == error, result
                    else:
                        assert not result.isError, result
                    return result.structuredContent

                observed = await call("get_observation")
                assert observed == decode_success("get_state", before["state"])
                for name in ("inspect_map", "close_map"):
                    await call(name, {"act": 2}, error="invalid_request")
                sample = await call("inspect_map")
                reference = await asyncio.to_thread(client.call, "inspect_map")
                evidence["references"].append(reference)
                assert reference["ok"] and sample == decode_success("inspect_map", reference["state"]), (sample, reference)
                assert sample == map_details(reference["state"])
                assert not sample["can_travel"] and sample["selectable_nodes"] == []
                assert "available_actions" not in sample and "notes" not in sample and "snapshot_id" not in sample
                assert await call("inspect_map") == sample
                covered = await call("get_observation")
                assert covered["screen"] == {"status": "covered", "view": "map"} and "close_map" in covered["available_actions"] and not set(covered["available_actions"]) & GAME_ACTIONS
                assert covered['map']['selectable_nodes'] == sample['selectable_nodes']
                await call("close_map", {"force": True}, error="invalid_request")
                assert await call("get_observation") == covered
                assert await call("close_map") == observation_preset(observed, "actions_only")
                assert await call("get_observation") == observed
                assert {tool.name for tool in (await session.list_tools()).tools} == names
        after = await asyncio.to_thread(client.call, "get_state")
        evidence["after"] = after
        assert after["ok"] and decode_success("get_state", after["state"]) == decode_success("get_state", before["state"])
        assert after["state"]["snapshot_id"] != before["state"]["snapshot_id"]
        evidence["completed"] = True
    finally:
        if sample is not None:
            (args.output_dir / "map-inspection.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2) + "\n")
        (args.output_dir / "mcp-map-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("PASS: real stdio MCP, full map, file JSON parity, repeat, argument rejection and compact explicit close; gameplay unchanged.")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 查看并关闭整张地图，不选路或结束回合。")
    parser.add_argument("--ipc-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
