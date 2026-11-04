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
from sts2_mcp.output.browse_output import browse_result
from sts2_mcp.output.observation_presets import observation_preset


async def verify(args):
    client = Client(args.ipc_dir)
    before = await asyncio.to_thread(client.call, "get_state")
    assert before["ok"] and before["state"]["screen"]["status"] == "visible", before
    evidence = {"completed": False, "before": before, "calls": [], "references": []}
    parameters = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), "--ipc-dir", str(args.ipc_dir.resolve())])
    samples = {}
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            initialized = await session.initialize()
            evidence.update(protocol_version=initialized.protocolVersion, server=initialized.serverInfo.model_dump())
            listed = await session.list_tools()
            evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]
            names = {tool.name for tool in listed.tools}
            assert names >= {"get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants",
                             "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map", "end_turn"}, names
            for name in ("inspect_deck", "close_card_view"):
                tool = next(tool for tool in listed.tools if tool.name == name)
                assert tool.annotations.readOnlyHint is False and tool.annotations.destructiveHint is False
            schema = next(tool for tool in listed.tools if tool.name == "inspect_deck").inputSchema
            assert set(schema["properties"]) == {"preset", "card_ids", "view_upgrades", "sort_by", "descending"}, schema

            async def call(name, arguments=None):
                result = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                evidence["calls"].append({"name": name, "arguments": arguments, "result": result.model_dump(exclude_none=True)})
                assert not result.isError, result
                assert json.loads(result.content[0].text) == result.structuredContent
                return result.structuredContent

            observed = await call("get_observation")
            assert observed == player_result(before), observed
            for name, arguments in [("summary", {"preset": "summary"}), ("full", {"preset": "full"}),
                                    ("upgraded", {"preset": "full", "view_upgrades": True})]:
                result = await call("inspect_deck", arguments)
                reference = await asyncio.to_thread(client.call, "inspect_deck", arguments={key: value for key, value in arguments.items() if key != 'preset'})
                evidence["references"].append(reference)
                assert reference["ok"] and result == browse_result(reference, "inspect_deck", preset=arguments["preset"]), (result, reference)
                assert len(result["deck"]) == observed["top_bar"]["deck_count"], result
                samples[name] = result
            ids = [card["id"] for card in samples["summary"]["deck"]]
            assert len(ids) == len(set(ids)), ids
            for result in samples.values():
                assert [card["id"] for card in result["deck"]] == ids
                assert "snapshot_id" not in result and "available_actions" not in result and "notes" not in result
            assert "hover_tips" not in samples["summary"]
            for result in (samples["full"], samples["upgraded"]):
                assert all("description" in card for card in result["deck"])
                assert all(set(tip["card_ids"]) <= set(ids) for tip in result["hover_tips"])
            retained = await call("inspect_deck")
            assert retained["view_upgrades"] and "detail_level" not in retained, retained
            assert retained["sort"] == samples["upgraded"]["sort"], retained
            covered = await call("get_observation")
            assert covered["screen"] == {"status": "covered", "view": "deck"} and "close_card_view" in covered["available_actions"] and not set(covered["available_actions"]) & GAME_ACTIONS, covered
            closed = await call("close_card_view")
            assert closed == observation_preset(observed, 'actions_only'), "Closing returned inconsistent action context."
            assert await call("get_observation") == observed, "Gameplay changed."
            assert {tool.name for tool in (await session.list_tools()).tools} == names, "Tool set changed with the UI."
    after = await asyncio.to_thread(client.call, "get_state")
    assert after["ok"] and player_result(after) == player_result(before), after
    assert after["state"]["snapshot_id"] != before["state"]["snapshot_id"], "The old action token was restored."
    evidence.update(completed=True, after=after)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, result in samples.items():
        (args.output_dir / f"deck-{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (args.output_dir / "mcp-deck-evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    print(f"PASS: real stdio MCP, {len(ids)} cards, repeated inspection, upgrade preview and explicit card-view close; gameplay unchanged.")


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP 验证牌组浏览和关闭，只执行 UI 操作。")
    parser.add_argument("--ipc-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
