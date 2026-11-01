import copy
import contextlib
import io
import json
import unittest
from unittest.mock import patch

import sts2_mcp.roundtrip_client as roundtrip_client
from sts2_mcp.mcp_server import GameTools, tool_result
from sts2_mcp.roundtrip_client import player_result


def observation():
    return {
        "snapshot_id": "test-state", "scene": "combat", "screen": {"status": "visible"},
        "turn": 1, "player": {"hp": 80, "hand": [{"id": 0, "name": "Strike"}]},
        "enemies": [{"id": 1, "name": "Slime", "intents": []}],
        "top_bar": {"potion_slots": [None, {"name": "Block Potion"}],
                    "relics": [{"name": "Anchor", "counter": 0}]},
        "buttons": {"end_turn": {"text": "End Turn 1", "enabled": True}},
        "available_actions": ["end_turn"],
    }


class ReplyClient:
    def __init__(self, state):
        self.state = state

    def call(self, operation, expected_state=None, arguments=None):
        return {"ok": True, "state": self.state}


class OutputBoundaryTests(unittest.TestCase):
    def test_cli_malformed_payload_returns_json_error_and_nonzero_exit(self):
        response = {"ok": True, "state": {"scene": "combat", "enemies": [None]}}
        output = io.StringIO()
        with patch("sys.argv", ["roundtrip_client.py", "--ipc-dir", "/tmp/unused", "get_state"]), \
                patch.object(roundtrip_client.Client, "call", return_value=response), \
                contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as raised:
                roundtrip_client.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(json.loads(output.getvalue())["error"]["code"], "transport_error")

    def test_observation_strips_nested_extras_and_unexpanded_card_effects(self):
        state = observation()
        expected = player_result({"ok": True, "state": copy.deepcopy(state)})
        for item in (state["screen"], state["player"], state["player"]["hand"][0],
                     state["enemies"][0], state["top_bar"], state["top_bar"]["potion_slots"][1],
                     state["top_bar"]["relics"][0], state["buttons"], state["buttons"]["end_turn"]):
            item["debug_future"] = "hidden"
        state["player"]["hand"][0].update(description="Unexpanded effect.", hover_tips=[])
        original = copy.deepcopy(state)
        self.assertEqual(player_result({"ok": True, "state": state}), expected)
        self.assertEqual(state, original)

    def test_hand_strips_nested_extras_but_keeps_description_and_newlines(self):
        state = {"hand": [{"id": 0, "name": "Strike", "description": "First line.\nSecond line.",
                           "debug_future": "hidden", "hover_tips": [{
                               "title": "Effect", "description": "Help.", "debug_future": "hidden"}]}]}
        result = player_result({"ok": True, "state": state})
        self.assertEqual(result["hand"], [{"id": 0, "name": "Strike", "description": "First line.\nSecond line."}])
        self.assertEqual(result["hover_tips"], [{"title": "Effect", "description": "Help.", "card_ids": [0]}])
        self.assertIn("debug_future", state["hand"][0])

    def test_output_json_is_compact_and_preserves_text(self):
        payload = {"hand": [{"description": "First line.\nSecond line. 中文"}]}
        result = tool_result(payload)
        self.assertEqual(result.content[0].text, '{"hand":[{"description":"First line.\\nSecond line. 中文"}]}')
        self.assertEqual(json.loads(result.content[0].text), result.structuredContent)


class ObservationValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_incomplete_observation_clears_action_permission(self):
        client = ReplyClient(observation())
        tools = GameTools(client)
        await tools.get_observation()
        for missing in ("scene", "screen", "turn", "player", "enemies", "top_bar", "buttons", "available_actions"):
            with self.subTest(missing=missing):
                client.state = observation()
                del client.state[missing]
                result = await tools.get_observation()
                self.assertEqual(result.get("error", {}).get("code"), "transport_error")
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_malformed_nested_observation_returns_structured_error(self):
        cases = [
            {"enemies": [None]}, {"enemies": "invalid"}, {"player": []},
            {"player": {"hp": True}}, {"player": {"hand": [{"id": True}]}},
            {"screen": None}, {"screen": {"status": 5}},
            {"available_actions": [5]}, {"top_bar": {"potion_slots": [False]}},
            {"buttons": {"end_turn": {"enabled": "yes"}}},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                state = {**observation(), **changes}
                tools = GameTools(ReplyClient(state))
                result = await tools.get_observation()
                self.assertEqual(result.get("error", {}).get("code"), "transport_error")
                self.assertIsNone(tools.snapshot_id)

    async def test_invalid_action_result_does_not_look_successful_or_restore_permission(self):
        client = ReplyClient(observation())
        tools = GameTools(client)
        await tools.get_observation()
        client.state = {"snapshot_id": "after-action"}
        result = await tools.end_turn()
        self.assertEqual(result.get("error", {}).get("code"), "transport_error")
        self.assertEqual(result["error"]["outcome"], "unknown")
        self.assertIsNone(tools.snapshot_id)

    async def test_malformed_hand_details_clear_action_permission(self):
        for hand in ([{"name": "Strike", "description": "Text.", "hover_tips": []}],
                     [{"id": False, "name": "Strike", "description": "Text.", "hover_tips": []}],
                     [{"id": 0, "name": "Strike", "description": [], "hover_tips": []}],
                     [{"id": 0, "name": "Strike", "description": "Text.", "hover_tips": [{"title": 3, "description": "Help."}]}]):
            with self.subTest(hand=hand):
                client = ReplyClient(observation())
                tools = GameTools(client)
                await tools.get_observation()
                client.state = {"snapshot_id": "test-state", "hand": hand}
                result = await tools.inspect_hand()
                self.assertEqual(result.get("error", {}).get("code"), "transport_error")
                self.assertIsNone(tools.snapshot_id)

    async def test_covered_observation_keeps_unknown_separate_from_empty_and_zero(self):
        state = {**observation(), "screen": {"status": "covered", "view": "map"},
                 "player": None, "enemies": None, "top_bar": None, "buttons": None,
                 "turn": None, "available_actions": []}
        result = await GameTools(ReplyClient(state)).get_observation()
        self.assertIsNone(result["player"])
        self.assertIsNone(result["enemies"])
        self.assertEqual(result["available_actions"], [])
        visible = await GameTools(ReplyClient(observation())).get_observation()
        self.assertEqual(visible["top_bar"]["relics"][0]["counter"], 0)


if __name__ == "__main__":
    unittest.main()
