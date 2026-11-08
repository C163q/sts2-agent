import argparse
import json
import math
import signal
import sys
from pathlib import Path

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, ImageContent, TextContent
from sts2_mcp.output.media import ImagePayload

from sts2_mcp.controller_lease import ControllerLease
from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import SERVER_INSTRUCTIONS, tool_definitions
from sts2_mcp.output.player_output import player_result
from sts2_mcp.roundtrip_client import Client
from sts2_mcp.mcp_config import load_config
from sts2_mcp.screenshot_tool import screenshots_disabled
from sts2_mcp.stdio_transport import Stdin, Stdout


SERVER_VERSION = "0.85.0"

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
    server = Server("sts2-agent", version=SERVER_VERSION, instructions=SERVER_INSTRUCTIONS)
    definitions = tool_definitions(screenshots_enabled=screenshots_enabled)
    handlers = {tool.name: getattr(tools, tool.name) for tool in definitions}

    @server.list_tools()
    async def list_tools():
        return definitions

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        if name not in handlers:
            if name == 'capture_screenshot':
                return tool_result(screenshots_disabled())
            return tool_result(player_result({"ok": False, "error": {"code": "invalid_request"}}))
        return tool_result(await handlers[name](arguments))

    return server


async def run_stdio(tools, screenshots_enabled=False):
    server = create_server(tools, screenshots_enabled=screenshots_enabled)
    with anyio.open_signal_receiver(signal.SIGINT, signal.SIGTERM) as signals:
        async with anyio.create_task_group() as group:
            async def stop_on_signal():
                async for _ in signals:
                    group.cancel_scope.cancel()
                    return

            group.start_soon(stop_on_signal)
            stdin = Stdin(sys.stdin.fileno(), group.cancel_scope)
            stdout = Stdout(sys.stdout.fileno(), group.cancel_scope)
            async with stdio_server(stdin=stdin, stdout=stdout) as (read, write):
                await server.run(read, write, server.create_initialization_options())
            group.cancel_scope.cancel()


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
        tools = GameTools(Client(lease.directory, timeout=args.timeout,
                                 check_cancelled=anyio.from_thread.check_cancelled), controller=lease,
                          screenshot_directory=settings.screenshot_directory)
        anyio.run(run_stdio, tools, settings.screenshot_directory is not None)
    except KeyboardInterrupt:
        pass
    except (OSError, RuntimeError) as error:
        parser.exit(1, f"MCP controller startup failed: {error}\n")
    finally:
        lease.close()


if __name__ == "__main__":
    main()
