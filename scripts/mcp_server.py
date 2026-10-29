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

from combatant_details import combatant_details
from relic_details import relic_details
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


def potion_details(state):
    def tip_text(tip):
        if (not isinstance(tip, dict)
                or (tip["title"] is not None and not isinstance(tip["title"], str))
                or not isinstance(tip["description"], str)):
            raise ValueError("Invalid potion hover tip.")
        return {"title": tip["title"], "description": tip["description"]}

    common = tip_text(state["slot_tip"])
    slots = state["potion_slots"]
    if not isinstance(slots, list):
        raise ValueError("Invalid potion slots.")
    potions = []
    for potion in slots:
        if potion is None:
            potions.append(None)
            continue
        if (not isinstance(potion, dict)
                or (potion["name"] is not None and not isinstance(potion["name"], str))
                or not isinstance(potion["description"], str)
                or not isinstance(potion["hover_tips"], list)):
            raise ValueError("Invalid potion details.")
        potions.append({"name": potion["name"], "description": potion["description"],
                        "hover_tips": [tip_text(tip) for tip in potion["hover_tips"]]})
    return {"slot_tip": common, "potion_slots": potions}


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
                if operation == "inspect_hand":
                    hand = state.get("hand")
                    if not isinstance(hand, list) or any(not isinstance(card, dict) for card in hand):
                        raise ValueError("Invalid hand details.")
                    for card in hand:
                        tips = card.get("hover_tips")
                        if tips is not None and (not isinstance(tips, list)
                                or any(not isinstance(tip, dict) for tip in tips)):
                            raise ValueError("Invalid card hover tips.")
                    response = {"ok": True, "state": {"hand": hand}}
                elif operation == "inspect_ui":
                    tips = state.get("hover_tips")
                    if state.get("scene") != "combat" or not isinstance(tips, list):
                        raise ValueError("Invalid UI details.")
                    for tip in tips:
                        if (not isinstance(tip, dict)
                                or (tip.get("title") is not None and not isinstance(tip["title"], str))
                                or not isinstance(tip.get("description"), str)
                                or not isinstance(tip.get("sources"), list) or not tip["sources"]
                                or any(not isinstance(source, str) or not source for source in tip["sources"])):
                            raise ValueError("Invalid UI hover tip.")
                    response = {"ok": True, "state": {"scene": state["scene"], "hover_tips": [
                        {key: tip[key] for key in ("title", "description", "sources")} for tip in tips]}}
                elif operation == "inspect_potions":
                    response = {"ok": True, "state": potion_details(state)}
                elif operation == "inspect_combatants":
                    response = {"ok": True, "state": combatant_details(state)}
                elif operation == "inspect_relics":
                    response = {"ok": True, "state": relic_details(state)}
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
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
        structuredContent=payload,
        isError="error" in payload,
    )


def create_server(tools):
    server = Server("sts2-agent", version="0.6.0", instructions=(
        "Control a local Slay the Spire 2 game. Call get_observation before each action. "
        "Use inspect_hand to read all current hand descriptions and shared hover tips. "
        "Use inspect_ui to read hover explanations for visible interface elements and resources. "
        "Use inspect_potions to read all visible potion slots, descriptions and shared hover tips. "
        "Use inspect_combatants to read both sides' visible powers and enemies' currently displayed intents with shared explanations. "
        "Use inspect_relics to read all currently visible relic descriptions, displayed counters and shared hover tips. "
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
                    "end_turn": tools.end_turn}
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
