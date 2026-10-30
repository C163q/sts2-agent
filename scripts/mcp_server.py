import argparse
import json
import math
from pathlib import Path

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent

from controller_lease import ControllerLease
from game_tools import GameTools
from mcp_catalog import SERVER_INSTRUCTIONS, tool_definitions
from player_output import player_result
from roundtrip_client import Client


def tool_result(payload):
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
        structuredContent=payload,
        isError="error" in payload,
    )



def create_server(tools):
    server = Server("sts2-agent", version="0.12.0", instructions=SERVER_INSTRUCTIONS)
    definitions = tool_definitions()
    handlers = {tool.name: getattr(tools, tool.name) for tool in definitions}

    @server.list_tools()
    async def list_tools():
        return definitions

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if name not in handlers:
            return tool_result(player_result({"ok": False, "error": {"code": "invalid_request"}}))
        if name in {"inspect_deck", "inspect_pile", "select_card", "selection_option", "set_selection_view", "inspect_targets", "play_card"}:
            return tool_result(await handlers[name](arguments))
        if arguments:
            return tool_result(player_result({"ok": False, "error": {"code": "invalid_request"}}))
        return tool_result(await handlers[name]())

    return server


async def run_stdio(tools):
    server = create_server(tools)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description="通过 stdio MCP 提供 STS2 战斗观察、各类只读详情与结束回合。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=40, help="文件通信超时秒数，默认 40")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout 必须是有限正数。")
    lease = ControllerLease(args.ipc_dir)
    try:
        tools = GameTools(Client(lease.directory, timeout=args.timeout), controller=lease)
        anyio.run(run_stdio, tools)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"MCP controller startup failed: {error}\n")
    finally:
        lease.close()


if __name__ == "__main__":
    main()
