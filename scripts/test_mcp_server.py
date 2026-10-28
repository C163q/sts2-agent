import asyncio
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import anyio

from roundtrip_client import Client


SERVER = Path(__file__).with_name("mcp_server.py")


class FakeGame:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.requests = self.directory / "requests"
        self.responses = self.directory / "responses"
        self.requests.mkdir()
        self.responses.mkdir()
        self.operations = []
        self.turn = 1
        self.drop_action_response = False
        self.malformed_observation = False
        self.observation_started = threading.Event()
        self.release_observation = threading.Event()
        self.release_observation.set()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stopped.set()
        self.release_observation.set()
        self.thread.join()
        self.temporary.cleanup()

    def run(self):
        while not self.stopped.wait(0.002):
            for path in self.requests.glob("*.json"):
                request = json.loads(path.read_text())
                self.operations.append(request)
                operation = request["operation"]
                if operation == "get_state":
                    self.observation_started.set()
                    self.release_observation.wait(timeout=5)
                response = {"id": request["id"], "ok": True}
                if operation == "end_turn":
                    if request.get("expected_state") != f"state-{self.turn}":
                        response.update(ok=False, error={"code": "stale_state", "message": "/private/game/path"})
                    else:
                        self.turn += 1
                if response["ok"]:
                    response["state"] = {
                        "snapshot_id": f"state-{self.turn}", "schema_version": 3, "language": "en",
                        "session": "fixture", "combat_generation": 1, "scene": "combat",
                        "screen": {"status": "visible"}, "turn": self.turn,
                        "player": {"hp": 80, "max_hp": 80, "hand": []}, "enemies": [],
                        "top_bar": {}, "buttons": {}, "available_actions": ["end_turn", "start_test_combat"],
                        "overlay": {"seed": "private"},
                    }
                if operation == "get_state" and self.malformed_observation:
                    response.pop("state")
                if operation != "end_turn" or not self.drop_action_response:
                    target = self.responses / path.name
                    temporary = target.with_suffix(".tmp")
                    temporary.write_text(json.dumps(response))
                    temporary.replace(target)
                path.unlink()


class GameToolsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertTrue(SERVER.exists(), "MCP server has not been implemented.")
        from mcp_server import GameTools
        self.tools_type = GameTools

    async def test_action_requires_explicit_observation_without_sending_request(self):
        with FakeGame() as game:
            result = await self.tools_type(Client(game.directory)).end_turn()
            self.assertEqual(result["error"]["code"], "observation_required")
            self.assertEqual(result["error"]["recovery"], "get_observation")
            self.assertEqual(game.operations, [])

    async def test_observation_filters_metadata_and_action_consumes_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            before = await tools.get_observation()
            self.assertEqual(before["turn"], 1)
            self.assertEqual(before["available_actions"], ["end_turn"])
            self.assertFalse({"ok", "state", "snapshot_id", "session", "schema_version", "overlay"} & before.keys())
            after = await tools.end_turn()
            self.assertEqual(after["turn"], 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")
            duplicate = await tools.end_turn()
            self.assertEqual(duplicate["error"]["code"], "observation_required")
            self.assertEqual(len(game.operations), 2)
            self.assertEqual((await tools.get_observation())["turn"], 2)
            self.assertEqual((await tools.end_turn())["turn"], 3)
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_stale_state_is_reported_without_refresh_or_retry(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            result = await tools.end_turn()
            self.assertEqual(result["error"]["code"], "stale_state")
            self.assertEqual(result["error"]["recovery"], "get_observation")
            self.assertNotIn("/private", json.dumps(result))
            self.assertEqual(len(game.operations), 2)
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual((await tools.get_observation())["turn"], 2)
            self.assertEqual((await tools.end_turn())["turn"], 3)

    async def test_timed_out_action_is_not_repeated(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory, timeout=0.1))
            await tools.get_observation()
            game.drop_action_response = True
            result = await tools.end_turn()
            self.assertEqual(result["error"]["code"], "timeout")
            self.assertEqual(result["error"]["outcome"], "unknown")
            self.assertEqual(result["error"]["recovery"], "get_observation")
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual((await tools.get_observation())["turn"], 2)
            self.assertEqual(len(game.operations), 3)

    async def test_failed_observation_invalidates_previous_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.malformed_observation = True
            result = await tools.get_observation()
            self.assertEqual(result["error"]["code"], "transport_error")
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual(len(game.operations), 2)

    async def test_concurrent_actions_only_execute_once(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            results = await asyncio.gather(tools.end_turn(), tools.end_turn())
            self.assertEqual([result.get("turn") for result in results], [2, None])
            self.assertEqual(results[1]["error"]["code"], "observation_required")
            self.assertEqual(len(game.operations), 2)

    async def test_cancelled_observation_does_not_authorize_action(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            game.release_observation.clear()
            scopes = []

            async def observe():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.get_observation()

            async with anyio.create_task_group() as group:
                group.start_soon(observe)
                await anyio.to_thread.run_sync(game.observation_started.wait)
                scopes[0].cancel()
                game.release_observation.set()
            result = await tools.end_turn()
            self.assertIn("error", result)
            self.assertEqual(result["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state"])


class StdioTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertTrue(SERVER.exists(), "MCP server has not been implemented.")

    async def test_stdio_tools_and_structured_errors(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with FakeGame() as game:
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory)])
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    self.assertEqual({tool.name for tool in listed.tools}, {"get_observation", "end_turn"})
                    for tool in listed.tools:
                        self.assertEqual(tool.inputSchema.get("properties", {}), {})
                    missing = await session.call_tool("end_turn", {})
                    self.assertTrue(missing.isError)
                    self.assertEqual(missing.structuredContent["error"]["code"], "observation_required")
                    before = await session.call_tool("get_observation", {})
                    self.assertFalse(before.isError)
                    self.assertEqual(before.structuredContent["turn"], 1)
                    self.assertEqual(json.loads(before.content[0].text), before.structuredContent)
                    self.assertNotIn("snapshot_id", before.structuredContent)
                    invalid = await session.call_tool("end_turn", {"unexpected": True})
                    self.assertTrue(invalid.isError)
                    self.assertEqual(game.turn, 1)
                    executed = await session.call_tool("end_turn", {})
                    self.assertFalse(executed.isError)
                    self.assertEqual(executed.structuredContent["turn"], 2)
                    duplicate = await session.call_tool("end_turn", {})
                    self.assertTrue(duplicate.isError)
                    self.assertEqual(game.turn, 2)

    async def test_handshake_succeeds_when_another_controller_owns_game(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp_server import ControllerLease
        with FakeGame() as game:
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory)])
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    with ControllerLease(game.directory):
                        await session.initialize()
                        listed = await session.list_tools()
                        self.assertEqual({tool.name for tool in listed.tools}, {"get_observation", "end_turn"})
                        busy = await session.call_tool("get_observation", {})
                        self.assertTrue(busy.isError)
                        self.assertEqual(busy.structuredContent["error"]["code"], "controller_busy")
                        self.assertEqual(game.operations, [])
                    recovered = await session.call_tool("get_observation", {})
                    self.assertFalse(recovered.isError)
                    self.assertEqual(recovered.structuredContent["turn"], 1)
            with ControllerLease(game.directory):
                pass

    async def test_idle_connection_does_not_own_controller_lock(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from mcp_server import ControllerLease
        with FakeGame() as game:
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory)])
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.list_tools()
                    with ControllerLease(game.directory):
                        pass
                    self.assertEqual(game.operations, [])

    async def test_two_connections_keep_control_until_owner_disconnects(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        with FakeGame() as game:
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory)])
            async with stdio_client(parameters) as (second_read, second_write):
                async with ClientSession(second_read, second_write) as second:
                    await second.initialize()
                    async with stdio_client(parameters) as (first_read, first_write):
                        async with ClientSession(first_read, first_write) as first:
                            await first.initialize()
                            self.assertFalse((await first.call_tool("get_observation", {})).isError)
                            busy = await second.call_tool("get_observation", {})
                            self.assertEqual(busy.structuredContent["error"]["code"], "controller_busy")
                            blocked = await second.call_tool("end_turn", {})
                            self.assertEqual(blocked.structuredContent["error"]["code"], "observation_required")
                            self.assertEqual(len(game.operations), 1)
                    recovered = await second.call_tool("get_observation", {})
                    self.assertFalse(recovered.isError)
                    self.assertEqual(recovered.structuredContent["turn"], 1)
                    self.assertEqual([item["operation"] for item in game.operations], ["get_state", "get_state"])


if __name__ == "__main__":
    unittest.main()
