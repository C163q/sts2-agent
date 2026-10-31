import argparse
import json
import math
from pathlib import Path

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ImageContent, TextContent
from divination_details import ImagePayload

from controller_lease import ControllerLease
from game_tools import GameTools
from mcp_catalog import SERVER_INSTRUCTIONS, tool_definitions
from player_output import player_result
from roundtrip_client import Client
from mcp_config import load_config


def tool_result(payload):
    content = [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))]
    if isinstance(payload, ImagePayload):
        content.append(ImageContent(type='image', mimeType='image/png', data=payload.image))
    return CallToolResult(
        content=content,
        structuredContent=payload,
        isError="error" in payload,
    )



def create_server(tools, *, screenshots_enabled=False):
    server = Server("sts2-agent", version="0.27.0", instructions=SERVER_INSTRUCTIONS)
    definitions = tool_definitions(screenshots_enabled=screenshots_enabled)
    handlers = {tool.name: getattr(tools, tool.name) for tool in definitions}

    @server.list_tools()
    async def list_tools():
        return definitions

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if name not in handlers:
            return tool_result(player_result({"ok": False, "error": {"code": "invalid_request"}}))
        if name in {"get_observation", "run_result_option", "travel_to_node", "end_turn", "inspect_deck", "inspect_pile", "select_card", "selection_option", "set_selection_view", "inspect_targets", "play_card", "use_potion", "discard_potion", "capture_screenshot", 'claim_reward', 'proceed', 'choose_rest_option', 'loot_treasure', 'open_shop', 'close_shop', 'buy_item', 'choose_ancient_option', 'advance_dialogue', 'choose_event_option', 'set_divination_tool', 'divine', 'respond_to_confirmation'}:
            return tool_result(await handlers[name](arguments))
        if arguments:
            return tool_result(player_result({"ok": False, "error": {"code": "invalid_request"}}))
        return tool_result(await handlers[name]())

    return server


async def run_stdio(tools, screenshots_enabled=False):
    server = create_server(tools, screenshots_enabled=screenshots_enabled)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description="通过 stdio MCP 提供 STS2 可见观察、按需详情与原生动作。")
    parser.add_argument("--ipc-dir", required=True, type=Path)
    parser.add_argument("--config", type=Path, help="MCP JSON 配置；默认读取仓库根 mcp-config.json，不存在时截图关闭")
    parser.add_argument("--timeout", type=float, default=40, help="文件通信超时秒数，默认 40")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout 必须是有限正数。")
    try:
        settings = load_config(args.config)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    lease = ControllerLease(args.ipc_dir)
    try:
        tools = GameTools(Client(lease.directory, timeout=args.timeout), controller=lease,
                          screenshot_directory=settings.screenshot_directory)
        anyio.run(run_stdio, tools, settings.screenshot_directory is not None)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"MCP controller startup failed: {error}\n")
    finally:
        lease.close()


if __name__ == "__main__":
    main()
