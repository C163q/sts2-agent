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

from sts2_mcp.roundtrip_client import Client, player_result
from sts2_mcp.output.card_format import browse_result


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["screen"] == {"status": "visible"}, before
    evidence = {"completed": False, "before": before, "calls": [], "references": []}
    parameters = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), "--ipc-dir", str(args.ipc_dir.resolve())])
    samples = {}
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            initialized = await session.initialize()
            evidence.update(protocol_version=initialized.protocolVersion, server=initialized.serverInfo.model_dump())
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert names >= {"get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants",
                             "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map", "end_turn"}, names
            tool = next(tool for tool in listed.tools if tool.name == "inspect_pile")
            assert tool.annotations.readOnlyHint is False and tool.annotations.destructiveHint is False
            assert set(tool.inputSchema["properties"]) == {"preset", "pile"} and tool.inputSchema["required"] == ["pile"]
            evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]

            async def call(name, arguments=None):
                result = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                evidence["calls"].append({"name": name, "arguments": arguments, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            observed = await call("get_observation")
            assert observed == player_result(before), observed
            for pile in ("draw", "discard", "exhaust"):
                for level in ("summary", "full"):
                    arguments = {"pile": pile, "preset": level}
                    result = await call("inspect_pile", arguments)
                    reference = await asyncio.to_thread(client.call, "inspect_pile", arguments={"pile": pile})
                    evidence["references"].append(reference)
                    assert reference["ok"] and result == browse_result(reference, "inspect_pile", {"pile": pile}, level), (result, reference)
                    assert result["pile"] == pile and "detail_level" not in result
                    assert "snapshot_id" not in result and "available_actions" not in result and "notes" not in result
                    if result["cards"] is not None:
                        ids = [card["id"] for card in result["cards"]]
                        assert len(ids) == len(set(ids)) and all(identifier.startswith("pile:") for identifier in ids)
                        if level == "full":
                            assert all("description" in card for card in result["cards"])
                            assert all(set(tip["card_ids"]) <= set(ids) for tip in result["hover_tips"])
                        else:
                            assert "hover_tips" not in result and all("description" not in card for card in result["cards"])
                    if result["status"] == "opened":
                        covered = await call("get_observation")
                        assert covered["screen"] == {"status": "covered", "view": pile + "_pile"}
                        assert "close_card_view" in covered["available_actions"] and not set(covered["available_actions"]) & GAME_ACTIONS
                    samples[pile + "-" + level] = result
                if result["status"] == "opened":
                    assert [card["id"] for card in samples[pile + "-summary"]["cards"]] == ids
                    assert await call("inspect_pile", {"pile": pile, "preset": "summary"}) == samples[pile + "-summary"]
                    assert await call("close_card_view") == observed
                assert await call("get_observation") == observed
            assert {tool.name for tool in (await session.list_tools()).tools} == names
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"] and player_result(after) == observed
    assert after["state"]["snapshot_id"] != before["state"]["snapshot_id"], "UI clicks did not invalidate the old token."
    evidence.update(completed=True, after=after)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, result in samples.items():
        (args.output_dir / (name + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "mcp-piles-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print("PASS: real stdio MCP, all three piles, repeated summary/full, native empty feedback and explicit close; gameplay unchanged.")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 验证三类牌堆，不出牌或结束回合。")
    parser.add_argument("--ipc-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
