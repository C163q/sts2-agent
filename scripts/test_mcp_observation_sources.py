import asyncio
import unittest

from game_tools import GameTools
from roundtrip_client import Client
from test_mcp_server import FakeGame


class ObservationSourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_map_details_support_travel_without_basic_observation(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=["map:1:2:1"])
            tools = GameTools(Client(game.directory))
            for _ in range(2):
                details = await tools.inspect_map()
                self.assertEqual(details["selectable_nodes"], ["map:1:2:1"])
            result = await tools.travel_to_node({"node_id": "map:1:2:1"})
            self.assertNotIn("error", result)
            self.assertEqual([r["operation"] for r in game.operations],
                             ["inspect_map", "inspect_map", "travel_to_node"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-1-ui-1")

    async def test_first_hand_inspection_supports_an_action_without_basic_observation(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            self.assertEqual((await tools.inspect_hand())["hand"][0]["id"], 9)
            result = await tools.end_turn()
            self.assertNotIn("error", result)
            self.assertEqual(game.turn, 2)
            self.assertEqual([r["operation"] for r in game.operations], ["inspect_hand", "end_turn"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")

    async def test_inspection_refreshes_an_outdated_state_before_action(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            await tools.inspect_combatants()
            self.assertNotIn("error", await tools.end_turn())
            self.assertEqual(game.turn, 3)
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_closed_deck_supports_action_but_open_deck_does_not(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.inspect_deck()
            self.assertEqual((await tools.end_turn())["error"]["code"], "illegal_action")
            await tools.close_card_view()
            self.assertNotIn("error", await tools.end_turn())
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1-ui-2")
            self.assertNotIn("get_state", [r["operation"] for r in game.operations])

    async def test_inspection_recovers_after_stale_state_without_basic_observation(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            self.assertEqual((await tools.end_turn())["error"]["code"], "stale_state")
            await tools.inspect_hand()
            self.assertNotIn("error", await tools.end_turn())
            self.assertEqual(game.turn, 3)
            self.assertEqual([r["operation"] for r in game.operations],
                             ["get_state", "end_turn", "inspect_hand", "end_turn"])

    async def test_queued_action_cannot_borrow_a_later_inspection(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            game.release_observation.clear()
            inspection = asyncio.create_task(tools.inspect_hand())
            self.assertTrue(await asyncio.to_thread(game.observation_started.wait, 2))
            action = asyncio.create_task(tools.end_turn())
            await asyncio.sleep(0)
            game.release_observation.set()
            await inspection
            self.assertEqual((await action)["error"]["code"], "observation_required")
            self.assertEqual(game.turn, 1)
            self.assertEqual([r["operation"] for r in game.operations], ["inspect_hand"])

    async def test_external_change_after_inspection_still_rejects_action(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.inspect_hand()
            game.turn = 2
            self.assertEqual((await tools.end_turn())["error"]["code"], "stale_state")
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")
