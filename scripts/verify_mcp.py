import argparse
import asyncio
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from roundtrip_client import Client


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    directory = args.ipc_dir.expanduser().resolve()
    if directory != root / ".tmp" / "roundtrip" / "ipc":
        raise SystemExit("本验证仅允许 .tmp/roundtrip/ipc，不能操作正式对局。")
    client = Client(directory)
    evidence = {"completed": False, "calls": []}

    def record(entry):
        evidence["calls"].append(entry)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")

    async def raw(operation, token=None):
        result = await asyncio.to_thread(client.call, operation, token)
        record({"transport": "file", "operation": operation, "result": result})
        assert result["ok"], result
        return result["state"]

    state = await raw("get_state")
    deadline = time.monotonic() + 30
    while state["scene"] == "loading_or_noncombat" and time.monotonic() < deadline:
        await asyncio.sleep(0.25)
        state = await raw("get_state")
    assert state["scene"] == "main_menu", "完整验证须从新启动的独立实例主菜单执行。"

    parameters = StdioServerParameters(command=sys.executable, args=[
        str(root / "scripts" / "mcp_server.py"), "--ipc-dir", str(directory)])
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=60)) as session:
            initialized = await session.initialize()
            evidence["protocol_version"] = initialized.protocolVersion
            evidence["server"] = initialized.serverInfo.model_dump()
            listed = await session.list_tools()
            evidence["tools"] = [tool.model_dump(exclude_none=True) for tool in listed.tools]
            assert {tool.name for tool in listed.tools} == {"get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "close_card_view", "end_turn"}

            async def call(name, arguments=None):
                result = await session.call_tool(name, arguments or {})
                record({"transport": "mcp", "operation": name, "result": result.model_dump(exclude_none=True)})
                assert json.loads(result.content[0].text) == result.structuredContent
                assert result.structuredContent is not None
                return result

            missing = await call("end_turn")
            assert missing.isError and missing.structuredContent["error"]["code"] == "observation_required"
            menu = await call("get_observation")
            assert not menu.isError and menu.structuredContent["available_actions"] == []
            illegal = await call("end_turn")
            assert illegal.isError and illegal.structuredContent["error"]["code"] == "illegal_action"

            state = await raw("get_state")
            await raw("start_test_combat", state["snapshot_id"])
            await asyncio.sleep(3)
            observed = await call("get_observation")
            assert not observed.isError
            before = observed.structuredContent
            assert before["scene"] == "combat" and before["screen"]["status"] == "visible"
            assert before["available_actions"] == ["end_turn"]
            assert not {"snapshot_id", "session", "schema_version", "overlay", "language"} & before.keys()
            inspected = await call("inspect_hand")
            assert not inspected.isError
            assert set(inspected.structuredContent) == {"hand", "hover_tips", "notes"}
            assert [card["id"] for card in inspected.structuredContent["hand"]] == [card["id"] for card in before["player"]["hand"]]
            invalid = await call("end_turn", {"unexpected": True})
            assert invalid.isError and invalid.structuredContent["error"]["code"] == "invalid_request"
            executed = await call("end_turn")
            assert not executed.isError
            after = executed.structuredContent
            assert after["turn"] == before["turn"] + 1
            duplicate = await call("end_turn")
            assert duplicate.isError and duplicate.structuredContent["error"]["code"] == "observation_required"
            readback = await call("get_observation")
            assert not readback.isError and readback.structuredContent == after

            current = await raw("get_state")
            advanced = await raw("end_turn", current["snapshot_id"])
            stale = await call("end_turn")
            assert stale.isError and stale.structuredContent["error"]["code"] == "stale_state"
            assert stale.structuredContent["error"]["recovery"] == "get_observation"
            recovered = await call("get_observation")
            assert not recovered.isError and recovered.structuredContent["turn"] == advanced["turn"]
            evidence.update(completed=True, before_turn=before["turn"], after_turn=after["turn"])
            record({"verification": "passed"})
            print(f'PASS: MCP turn {before["turn"]} -> {after["turn"]}; '
                  'structured results, invalid/missing/duplicate/stale actions and readback verified')


def main():
    parser = argparse.ArgumentParser(description="通过真实 stdio MCP server 验证独立游戏战斗往返。")
    parser.add_argument("--ipc-dir", type=Path, default=Path(".tmp/roundtrip/ipc"))
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    asyncio.run(verify(args))


if __name__ == "__main__":
    main()
