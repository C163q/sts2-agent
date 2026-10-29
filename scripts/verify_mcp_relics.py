import argparse
import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from roundtrip_client import Client, player_result
from verify_combatants import assert_visible_subsequence


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    reference = await asyncio.to_thread(client.call, "inspect_relics")
    assert reference["ok"], reference
    parameters = StdioServerParameters(command=sys.executable, args=[
        str(Path(__file__).with_name("mcp_server.py")), "--ipc-dir", str(args.ipc_dir.resolve())])
    evidence = {"completed": False, "before": before, "reference": reference, "calls": []}
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            initialized = await session.initialize()
            evidence["protocol_version"] = initialized.protocolVersion
            evidence["server"] = initialized.serverInfo.model_dump()
            listed = await session.list_tools()
            evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]
            assert {tool.name for tool in listed.tools} == {
                "get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "end_turn"}
            tool = next(tool for tool in listed.tools if tool.name == "inspect_relics")
            assert tool.annotations.readOnlyHint is True
            assert tool.inputSchema == {"type": "object", "properties": {}, "additionalProperties": False}

            async def call(name):
                result = await session.call_tool(name, {})
                evidence["calls"].append({"name": name, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            inspected = await call("inspect_relics")
            observed = await call("get_observation")
            repeated = await call("inspect_relics")
            assert inspected == repeated == player_result(reference), "Relics changed or MCP differs from file inspection."
            assert set(inspected) == {"relics", "hover_tips"}, inspected
            relics = inspected["relics"]
            assert_visible_subsequence([{key: item[key] for key in ("name", "counter")} for item in relics],
                                       observed["top_bar"]["relics"])
            for relic in relics:
                assert set(relic) == {"name", "counter", "description"}, relic
                assert isinstance(relic["description"], str), relic
            tips = inspected["hover_tips"]
            assert len(tips) == len({(tip["title"], tip["description"]) for tip in tips}), tips
            raw_links = {(index, tip["title"], tip["description"])
                         for index, relic in enumerate(reference["state"]["relics"])
                         for tip in relic["hover_tips"]}
            links = {(index, tip["title"], tip["description"]) for tip in tips for index in tip["relic_indices"]}
            assert links == raw_links, (links, raw_links)
            for tip in tips:
                assert set(tip) == {"title", "description", "relic_indices"}, tip
                indices = tip["relic_indices"]
                assert indices and len(indices) == len(set(indices)), tip
                assert all(type(index) is int and 0 <= index < len(relics) for index in indices), tip
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"], after
    assert len({response["state"]["snapshot_id"] for response in (before, reference, after)}) == 1, "Observation changed."
    evidence.update(completed=True, after=after)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inspected, indent=2, ensure_ascii=False) + "\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: real stdio MCP inspected {len(relics)} relics and {len(tips)} shared tips; "
          f"game observation unchanged; JSON: {args.output}")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 只读验证当前遗物说明，不执行游戏动作。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
