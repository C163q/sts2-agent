import argparse
import asyncio
import fcntl
import json
import logging
import math
from pathlib import Path

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations

from roundtrip_client import Client, player_result


class ControllerLease:
    def __init__(self, directory):
        self.directory = Path(directory).expanduser().resolve()
        self.file = None

    def acquire(self):
        if self.file is not None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        self.file = (self.directory / ".mcp-controller.lock").open("a")
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.close()
            raise

    def __enter__(self):
        self.acquire()
        return self

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def __exit__(self, *args):
        self.close()


class GameTools:
    def __init__(self, client, controller=None):
        self.client = client
        self.controller = controller
        self.lock = asyncio.Lock()
        self.snapshot_id = None

    async def get_observation(self):
        async with self.lock:
            self.snapshot_id = None
            if self.controller is not None:
                try:
                    self.controller.acquire()
                except BlockingIOError:
                    return {"error": {
                        "code": "controller_busy",
                        "message": "Another MCP connection controls this game. Disconnect it before observing or acting here.",
                        "recovery": "disconnect_other_client",
                    }}
                except OSError as error:
                    logging.getLogger(__name__).warning("Controller lock failed: %s", error)
                    return player_result({"ok": False, "error": {"code": "transport_error"}})
            payload, snapshot_id = await self._request("get_state")
            await anyio.lowlevel.checkpoint_if_cancelled()
            self.snapshot_id = snapshot_id
            return payload

    async def end_turn(self):
        async with self.lock:
            if self.snapshot_id is None:
                return {"error": {
                    "code": "observation_required",
                    "message": "Call get_observation before each action. Actions consume the previous observation.",
                    "recovery": "get_observation",
                }}
            snapshot_id, self.snapshot_id = self.snapshot_id, None
            payload, _ = await self._request("end_turn", snapshot_id)
            return payload

    async def _request(self, operation, expected_state=None):
        try:
            response = await anyio.to_thread.run_sync(self.client.call, operation, expected_state)
            if not isinstance(response, dict) or type(response.get("ok")) is not bool:
                raise ValueError("Invalid game response.")
            snapshot_id = None
            if response["ok"]:
                state = response["state"]
                snapshot_id = state["snapshot_id"]
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    raise ValueError("Missing observation token.")
            else:
                if not isinstance(response["error"]["code"], str):
                    raise ValueError("Invalid game error.")
            payload = player_result(response)
            if response["ok"]:
                payload["available_actions"] = [
                    action for action in payload.get("available_actions", []) if action == "end_turn"]
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
            code = "timeout" if isinstance(error, TimeoutError) else "transport_error"
            logging.getLogger(__name__).warning("Game request failed: %s", error)
            payload = player_result({"ok": False, "error": {"code": code}})
            snapshot_id = None
        if "error" in payload and payload["error"]["recovery"] == "get_state":
            payload["error"]["recovery"] = "get_observation"
        return payload, snapshot_id


def tool_result(payload):
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent=payload,
        isError="error" in payload,
    )


def create_server(tools):
    server = Server("sts2-agent", version="0.1.1", instructions=(
        "Control a local Slay the Spire 2 game. Call get_observation before each action. "
        "Only end_turn is currently implemented; card play and hand inspection are unavailable. "
        "Actions return the resulting observation but consume the action token. "
        "After any failed or timed-out action, read the state before deciding what to do. "
        "Never automatically repeat an action whose execution outcome is unknown."
    ))
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    @server.list_tools()
    async def list_tools():
        return [
            Tool(name="get_observation", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=True, openWorldHint=False), description=(
                    "Read the current visible game state and prepare one action. "
                    "Does not inspect hidden card effects.")),
            Tool(name="end_turn", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False),
                description="End the player's turn once and return the resulting state. Requires a fresh get_observation call."),
        ]

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        handlers = {"get_observation": tools.get_observation, "end_turn": tools.end_turn}
        if name not in handlers or arguments:
            return tool_result(player_result({"ok": False, "error": {"code": "invalid_request"}}))
        return tool_result(await handlers[name]())

    return server


async def run_stdio(tools):
    server = create_server(tools)
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description="通过 stdio MCP 提供 STS2 战斗观察与结束回合。")
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
