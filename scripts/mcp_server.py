import argparse
import asyncio
import fcntl
import json
import logging
import math
from functools import partial
from pathlib import Path

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations

from inspection_details import inspection_details, potion_details
from deck_details import DECK_SCHEMA, deck_arguments
from map_details import map_arguments
from pile_details import PILE_SCHEMA, pile_arguments
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
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request("get_state")
            await anyio.lowlevel.checkpoint_if_cancelled()
            self.snapshot_id = snapshot_id
            return payload

    async def inspect_hand(self):
        return await self._inspect("inspect_hand")

    async def inspect_ui(self):
        return await self._inspect("inspect_ui")

    async def inspect_potions(self):
        return await self._inspect("inspect_potions")

    async def inspect_combatants(self):
        return await self._inspect("inspect_combatants")

    async def inspect_relics(self):
        return await self._inspect("inspect_relics")

    async def inspect_deck(self, arguments=None):
        try:
            arguments = deck_arguments(arguments)
        except ValueError:
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return await self._change_view("inspect_deck", arguments)

    async def close_card_view(self):
        return await self._change_view("close_card_view")

    async def inspect_map(self, arguments=None):
        return await self._map_view("inspect_map", arguments)

    async def close_map(self, arguments=None):
        return await self._map_view("close_map", arguments)

    async def _map_view(self, operation, arguments):
        try:
            map_arguments(arguments)
        except ValueError:
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return await self._change_view(operation)

    async def inspect_pile(self, arguments=None):
        try:
            arguments = pile_arguments(arguments)
        except ValueError:
            return player_result({"ok": False, "error": {"code": "invalid_request"}})
        return await self._change_view("inspect_pile", arguments)

    async def _change_view(self, operation, arguments=None):
        async with self.lock:
            self.snapshot_id = None
            if error := self._acquire_controller():
                return error
            payload, _ = await self._request(operation, arguments=arguments)
            await anyio.lowlevel.checkpoint_if_cancelled()
            return payload

    async def _inspect(self, operation):
        async with self.lock:
            previous, self.snapshot_id = self.snapshot_id, None
            if error := self._acquire_controller():
                return error
            payload, snapshot_id = await self._request(operation)
            await anyio.lowlevel.checkpoint_if_cancelled()
            if previous == snapshot_id:
                self.snapshot_id = previous
            return payload

    def _acquire_controller(self):
        if self.controller is None:
            return None
        try:
            self.controller.acquire()
        except BlockingIOError:
            return {"error": {
                "code": "controller_busy",
                "message": "Another MCP connection controls this game. Disconnect it before reading or acting here.",
                "recovery": "disconnect_other_client",
            }}
        except OSError as error:
            logging.getLogger(__name__).warning("Controller lock failed: %s", error)
            return player_result({"ok": False, "error": {"code": "transport_error"}})
        return None

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

    async def _request(self, operation, expected_state=None, arguments=None):
        try:
            response = await anyio.to_thread.run_sync(partial(self.client.call, operation, expected_state, arguments=arguments))
            if not isinstance(response, dict) or type(response.get("ok")) is not bool:
                raise ValueError("Invalid game response.")
            snapshot_id = None
            if response["ok"]:
                state = response["state"]
                snapshot_id = state["snapshot_id"]
                if not isinstance(snapshot_id, str) or not snapshot_id:
                    raise ValueError("Missing observation token.")
                response = {"ok": True, "state": inspection_details(operation, state, arguments)}
            else:
                if not isinstance(response["error"]["code"], str):
                    raise ValueError("Invalid game error.")
            payload = player_result(response)
            if response["ok"] and "available_actions" in payload:
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
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
        structuredContent=payload,
        isError="error" in payload,
    )


def create_server(tools):
    server = Server("sts2-agent", version="0.9.0", instructions=(
        "Control a local Slay the Spire 2 game. Call get_observation before each action. "
        "Use inspect_hand to read all current hand descriptions and shared hover tips. "
        "Use inspect_ui to read hover explanations for visible interface elements and resources. "
        "Use inspect_potions to read all visible potion slots, descriptions and shared hover tips. "
        "Use inspect_combatants to read both sides' visible powers and enemies' currently displayed intents with shared explanations. "
        "Use inspect_relics to read all currently visible relic descriptions, displayed counters and shared hover tips. "
        "Use inspect_deck to open or reuse the deck page; it stays open and supports optional detail level, upgrade preview and sorting. "
        "Use inspect_pile for draw, discard or exhaust piles, with summary or full details. It clicks the native entry unless reusing the same page. "
        "Empty visible piles produce native feedback; hidden entries return unavailable with cards null. Draw pile order is display order, never draw order. "
        "Use close_card_view to close only the top card browsing page, preserving an underlying map. "
        "Use inspect_map to open or reuse the entire current-act map, including nodes, directed connections and actual selectable_nodes. "
        "Map connections do not imply current travel permission; Winged Boots can allow unconnected next-row choices. "
        "Use close_map to close only the visible map with an enabled native back button; it cannot close through a card page. "
        "Card and map view operations clear the action token; call get_observation again after closing before acting. "
        "Inspections do not prepare an action; only end_turn is implemented as an action. "
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
                    "Does not expand card descriptions or hover tips.")),
            Tool(name="inspect_hand", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=True, openWorldHint=False), description=(
                    "Read all currently visible hand cards at once, including descriptions and shared hover_tips linked by card_ids. "
                    "Does not play cards or prepare an action. Does not return enemy intents.")),
            Tool(name="inspect_ui", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=True, openWorldHint=False), description=(
                    "Read English hover explanations for currently visible combat interface elements and resources, linked by sources. "
                    "Excludes hand, potion, relic, power and enemy intent details. Does not open screens or prepare an action.")),
            Tool(name="inspect_potions", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=True, openWorldHint=False), description=(
                    "Read all currently visible potion slots and English descriptions at once. "
                    "Returns one slot_tip, positional potion_slots with null for empty slots, and shared hover_tips linked by zero-based slot_indices. "
                    "Does not use or discard potions, generate random choices, or prepare an action.")),
            Tool(name="inspect_combatants", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=True, openWorldHint=False), description=(
                    "Read English hover explanations for the player's and visible enemies' powers and currently displayed enemy intents. "
                    "Shared hover_tips use sources paths into this result. Intent damage already includes current preview modifiers. "
                    "Does not reveal future moves, play cards, or prepare an action. Unavailable while aiming or playing a card.")),
            Tool(name="inspect_relics", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=True, openWorldHint=False), description=(
                    "Read all currently visible, hoverable relics' English descriptions and displayed counters during combat. "
                    "Returns relics and shared hover_tips linked by zero-based relic_indices into this result. "
                    "Does not reveal hidden relics or counters, open screens, or prepare an action.")),
            Tool(name="inspect_deck", inputSchema=DECK_SCHEMA, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), description=(
                    "Open or reuse the native deck page and read the entire browsable deck. Repeated calls reuse the page. "
                    "Defaults to summary; full adds descriptions and shared hover_tips linked by card_ids. "
                    "Omitted page options preserve current settings; a new page uses game defaults. "
                    "Actually changes UI and pauses single-player combat. Upgrade preview does not upgrade owned cards. "
                    "Leaves the page open until close_card_view or manual return; clears action permission.")),
            Tool(name="inspect_pile", inputSchema=PILE_SCHEMA, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), description=(
                    "Open or reuse a native draw, discard or exhaust pile page and return the entire browsable pile in display order. "
                    "Summary is the default; full includes descriptions and shared hover_tips linked by card_ids. No upgrade or sorting controls. "
                    "Returns status opened, empty or unavailable and the actual screen. Empty draw/discard piles are actually clicked for native feedback; "
                    "a hidden exhaust entry is not clicked and returns cards null. Does not reveal draw order. "
                    "Replaces another card browsing page, leaves the opened page until close_card_view, and clears action permission.")),
            Tool(name="close_card_view", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), description=(
                    "Close only the currently visible read-only card browsing page: deck, draw, discard or exhaust pile. "
                    "Preserves an underlying map and does not close map, card selection or other screens. "
                    "Returns a basic observation; screen.view identifies a remaining map. Clears action permission; observe again before acting.")),
            Tool(name="inspect_map", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), description=(
                    "Open or reuse the native map and read the entire scrollable current-act map, including offscreen nodes. "
                    "Returns stable coordinate IDs, directed next connections, current_node, visited_path and actual selectable_nodes. "
                    "During combat there are no selectable nodes. Winged Boots may allow next-row nodes without connections. "
                    "Keeps unknown encounters hidden and does not read future acts, travel, or consume relic charges. "
                    "Uses the native map button to replace a covering card page; leaves the map open and clears action permission.")),
            Tool(name="close_map", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False), description=(
                    "Close only the currently exposed native map when its back button is enabled. "
                    "Does not close through card pages or force a mandatory starting map closed. "
                    "Returns a basic observation and clears action permission; observe again before acting.")),
            Tool(name="end_turn", inputSchema=parameters, annotations=ToolAnnotations(
                readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False),
                description="End the player's turn once and return the resulting state. Requires a fresh get_observation call."),
        ]

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        handlers = {"get_observation": tools.get_observation, "inspect_hand": tools.inspect_hand,
                    "inspect_ui": tools.inspect_ui, "inspect_potions": tools.inspect_potions,
                    "inspect_combatants": tools.inspect_combatants,
                    "inspect_relics": tools.inspect_relics,
                    "close_card_view": tools.close_card_view,
                    "end_turn": tools.end_turn}
        if name == "inspect_deck":
            return tool_result(await tools.inspect_deck(arguments))
        if name == "inspect_pile":
            return tool_result(await tools.inspect_pile(arguments))
        if name in {"inspect_map", "close_map"}:
            return tool_result(await getattr(tools, name)(arguments))
        if name not in handlers or arguments:
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
