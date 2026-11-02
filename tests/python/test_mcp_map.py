import copy
import json
import sys
import unittest

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.roundtrip_client import Client
from tests.python.test_mcp_server import FakeGame, SERVER, map_payload


class MapStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_tools_keep_contract_and_reject_arguments_before_ipc(self):
        with FakeGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory), "--config", str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    names = {tool.name for tool in listed.tools}
                    self.assertTrue({"inspect_map", "close_map"} <= names, "Map MCP tools are missing.")
                    self.assertEqual(len(names), 42)
                    for tool in listed.tools:
                        if tool.name in {"inspect_map", "close_map"}:
                            if tool.name == 'close_map':
                                self.assertEqual(set(tool.inputSchema["properties"]), {"preset"})
                                self.assertFalse(tool.inputSchema["additionalProperties"])
                            else:
                                self.assertEqual(set(tool.inputSchema['properties']), {'preset', 'max_steps'})
                            self.assertFalse(tool.annotations.readOnlyHint)
                            self.assertFalse(tool.annotations.destructiveHint)
                            self.assertFalse(tool.annotations.idempotentHint)
                    await session.call_tool("get_observation", {})
                    for name in ("inspect_map", "close_map"):
                        result = await session.call_tool(name, {"act": 2})
                        self.assertTrue(result.isError)
                        self.assertEqual(result.structuredContent["error"]["code"], "invalid_request")
                    self.assertEqual([x["operation"] for x in game.operations], ["get_state"])
                    viewed = await session.call_tool("inspect_map", {})
                    self.assertFalse(viewed.isError)
                    self.assertEqual(viewed.structuredContent, map_payload())
                    self.assertEqual(json.loads(viewed.content[0].text), viewed.structuredContent)
                    permission = await session.call_tool("end_turn", {})
                    self.assertEqual(permission.structuredContent["error"]["code"], "illegal_action")
                    closed = await session.call_tool("close_map", {})
                    self.assertFalse(closed.isError)
                    self.assertEqual(closed.structuredContent["screen"], {"status": "visible"})
                    self.assertEqual(json.loads(closed.content[0].text), closed.structuredContent)
                    self.assertEqual({t.name for t in (await session.list_tools()).tools}, names)


class MapMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_repeat_and_close_refresh_state_while_game_rejects_covered_actions(self):
        from sts2_mcp.mcp_server import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            self.assertEqual(await tools.inspect_map(), map_payload())
            self.assertEqual(await tools.inspect_map(), map_payload())
            self.assertEqual((await tools.end_turn())["error"]["code"], "illegal_action")
            game.map_payload.update(can_travel=True, selectable_nodes=["map:1:2:1", "map:1:2:5"])
            viewed = await tools.inspect_map()
            self.assertEqual(viewed["selectable_nodes"], ["map:1:2:1", "map:1:2:5"])
            self.assertEqual(viewed["nodes"][1]["next"], ["map:1:2:1"])
            await tools.get_observation()
            self.assertEqual((await tools.close_map())["screen"], {"status": "visible"})
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([x["operation"] for x in game.operations],
                             ["get_state", "inspect_map", "inspect_map", "end_turn", "inspect_map", "get_state", "close_map", "end_turn"])

    async def test_invalid_arguments_preserve_permission_and_never_reach_game(self):
        from sts2_mcp.mcp_server import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            for method in (tools.inspect_map, tools.close_map):
                for arguments in ({"act": 2}, [], False, 0, ""):
                    self.assertEqual((await method(arguments))["error"]["code"], "invalid_request")
            self.assertEqual([x["operation"] for x in game.operations], ["get_state"])
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)

    async def test_errors_timeouts_and_cancellation_do_not_restore_permission_or_retry(self):
        from sts2_mcp.mcp_server import GameTools
        for operation in ("inspect_map", "close_map"):
            for failure in ("error", "timeout", "cancel"):
                with self.subTest(operation=operation, failure=failure), FakeGame() as game:
                    tools = GameTools(Client(game.directory, timeout=.1 if failure == "timeout" else 2))
                    game.map_open = operation == "close_map"
                    await tools.get_observation()
                    if failure == "cancel":
                        game.observation_started.clear()
                        game.release_observation.clear()
                        scopes = []

                        async def invoke():
                            with anyio.CancelScope() as scope:
                                scopes.append(scope)
                                await getattr(tools, operation)()

                        async with anyio.create_task_group() as group:
                            group.start_soon(invoke)
                            self.assertTrue(await anyio.to_thread.run_sync(game.observation_started.wait, 2))
                            scopes[0].cancel()
                            game.release_observation.set()
                    else:
                        field = ("drop_map_response" if operation == "inspect_map" else "drop_close_map_response") if failure == "timeout" else (
                            "map_error" if operation == "inspect_map" else "close_map_error")
                        setattr(game, field, True)
                        result = await getattr(tools, operation)()
                        self.assertEqual(result["error"]["code"], "timeout" if failure == "timeout" else "illegal_action")
                        self.assertNotIn("/private", json.dumps(result))
                    self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
                    self.assertEqual([x["operation"] for x in game.operations], ["get_state", operation])

    async def test_malformed_map_and_close_fail_without_action_permission(self):
        from sts2_mcp.mcp_server import GameTools
        for operation in ("inspect_map", "close_map"):
            with self.subTest(operation=operation), FakeGame() as game:
                tools = GameTools(Client(game.directory))
                await tools.get_observation()
                if operation == "inspect_map":
                    game.map_payload["nodes"][1]["next"] = ["map:2:2:1"]
                else:
                    game.map_open = True
                    game.close_payload = {"screen": {"status": "covered", "view": "map"}}
                self.assertEqual((await getattr(tools, operation)())["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")


class MapProjectionTests(unittest.TestCase):
    def test_projection_strips_nested_extras_and_keeps_visible_optional_fields(self):
        from sts2_mcp.output.map_details import map_details
        expected = map_payload()
        expected["nodes"][2].update(revealed_type="monster", marked=True)
        raw = copy.deepcopy(expected)
        raw.update(snapshot_id="control", seed="private", available_actions=["end_turn"], next_act={"secret": 1})
        raw["nodes"][1].update(encounter="private", name="hidden monster", hover_tips=[{"secret": 1}])
        raw["screen"]["secret"] = 1
        before = copy.deepcopy(raw)
        self.assertEqual(map_details(raw), expected)
        self.assertEqual(raw, before)

    def test_invalid_graph_types_ids_paths_and_choices_are_rejected(self):
        from sts2_mcp.output.map_details import map_details
        cases = [(("scene",), "combat"), (("screen",), {"status": "covered", "view": "map"}),
                 (("act",), True), (("act",), 0), (("nodes",), []), (("nodes",), None),
                 (("nodes", 1, "id"), "map:1:01:2"), (("nodes", 1, "row"), True),
                 (("nodes", 1, "column"), -1), (("nodes", 1, "id"), "map:2:1:2"),
                 (("nodes", 1, "next"), ["map:1:9:9"]), (("nodes", 1, "next"), ["map:1:2:1"] * 2),
                 (("nodes", 1, "type"), "event"), (("nodes", 0, "name"), None),
                 (("nodes", 2, "revealed_type"), "boss"), (("nodes", 2, "marked"), 1),
                 (("visited_path",), ["map:1:0:3"]), (("current_node",), None),
                 (("visited_path",), ["map:1:9:9"]), (("visited_path",), ["map:1:1:2"] * 2),
                 (("can_travel",), 1), (("can_travel",), True),
                 (("selectable_nodes",), ["map:1:2:5"]), (("selectable_nodes",), None)]
        for path, value in cases:
            with self.subTest(path=path, value=value), self.assertRaises((ValueError, KeyError, TypeError)):
                raw = map_payload()
                target = raw
                for key in path[:-1]: target = target[key]
                target[path[-1]] = value
                map_details(raw)
        raw = map_payload()
        raw["nodes"].append(copy.deepcopy(raw["nodes"][0]))
        with self.assertRaises(ValueError): map_details(raw)

    def test_unentered_act_and_visible_unknown_type_remain_distinct(self):
        from sts2_mcp.output.map_details import map_details
        raw = map_payload()
        raw.update(current_node=None, visited_path=[], can_travel=True, selectable_nodes=["map:1:0:3"])
        raw["nodes"][2]["type"] = "unrecognized"
        self.assertEqual(map_details(raw), raw)


if __name__ == "__main__":
    unittest.main()
