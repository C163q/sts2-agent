import json
import unittest

import anyio

from sts2_mcp.roundtrip_client import Client
from tests.python.test_mcp_server import FakeGame


class DeckMcpTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from sts2_mcp.mcp_server import GameTools
        self.tools_type = GameTools

    async def test_repeated_inspection_preserves_omitted_options_and_summary_privacy(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            summary = await tools.inspect_deck()
            self.assertEqual(summary, {"scene": "combat", "screen": {"status": "covered", "view": "deck"}, "detail_level": "summary", "view_upgrades": False,
                "sort": {"by": "obtained", "descending": False}, "deck": [
                    {"id": "deck:0", "name": "Defend+", "type": "Skill", "rarity": "basic",
                     "visual_card_pool": "ironclad", "energy_cost": "1"},
                    {"id": "deck:1", "name": "Defend+", "type": "Skill", "rarity": "basic",
                     "visual_card_pool": "ironclad", "energy_cost": "1"}]})
            options = {"detail_level": "full", "view_upgrades": True, "sort_by": "cost", "descending": True}
            full = await tools.inspect_deck(options)
            self.assertEqual(full["hover_tips"], [{"title": "Block", "description": "Prevents damage.",
                                                   "card_ids": ["deck:0", "deck:1"]}])
            repeated = await tools.inspect_deck()
            self.assertEqual(repeated["detail_level"], "summary")
            self.assertTrue(repeated["view_upgrades"])
            self.assertEqual(repeated["sort"], {"by": "cost", "descending": True})
            self.assertNotIn("description", repeated["deck"][0])
            self.assertNotIn("hover_tips", repeated)
            self.assertEqual(game.operations[1]["arguments"], options)
            self.assertFalse(game.operations[0].get("arguments"))
            self.assertFalse(game.operations[2].get("arguments"))
            self.assertEqual((await tools.end_turn())["error"]["code"], "illegal_action")
            self.assertEqual([op["operation"] for op in game.operations], ["inspect_deck"] * 3 + ["end_turn"])

    async def test_explicit_false_is_forwarded_without_resetting_unspecified_sort(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.inspect_deck({"view_upgrades": True, "sort_by": "name", "descending": True})
            result = await tools.inspect_deck({"view_upgrades": False})
            self.assertFalse(result["view_upgrades"])
            self.assertEqual(result["sort"], {"by": "name", "descending": True})
            self.assertEqual(game.operations[-1]["arguments"], {"view_upgrades": False})

    async def test_close_returns_action_state_without_redundant_observation(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            await tools.inspect_deck()
            self.assertEqual((await tools.end_turn())["error"]["code"], "illegal_action")
            closed = await tools.close_card_view()
            self.assertEqual(closed["screen"], {"status": "visible"})
            self.assertEqual(closed["available_actions"], ["end_turn"])
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)

    async def test_invalid_parameters_never_reach_game_or_change_existing_permission(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            for invalid in [[], False, {"unknown": True}, {"detail_level": None}, {"detail_level": "brief"},
                            {"view_upgrades": 1}, {"view_upgrades": None}, {"sort_by": "rarity"},
                            {"sort_by": None}, {"descending": False}, {"sort_by": "cost", "descending": 1}]:
                with self.subTest(arguments=invalid):
                    result = await tools.inspect_deck(invalid)
                    self.assertEqual(result["error"]["code"], "invalid_request")
            self.assertEqual([op["operation"] for op in game.operations], ["get_state"])
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)

    async def test_malformed_deck_fields_clear_permission(self):
        missing = object()
        cases = [(("scene",), "deck"), (("detail_level",), "full"), (("view_upgrades",), 1),
                 (("sort",), None), (("sort",), {"by": "bad", "descending": False}),
                 (("sort",), {"by": "cost", "descending": 0}), (("sort",), {}),
                 (("deck",), None), (("deck",), [None]), (("deck", 0, "id"), missing),
                 (("deck", 0, "id"), "9"), (("deck", 0, "id"), "deck:00"),
                 (("deck", 1, "id"), "deck:0"), (("deck", 0, "name"), None),
                 (("deck", 0, "type"), missing), (("deck", 0, "rarity"), 1),
                 (("deck", 0, "visual_card_pool"), {}), (("deck", 0, "energy_cost"), 1),
                 (("deck", 0, "star_cost"), False), (("snapshot_id",), "")]
        for path, value in cases:
            with self.subTest(path=path, value=value), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                await tools.get_observation()
                target = game.deck_payload
                for part in path[:-1]:
                    target = target[part]
                if value is missing:
                    del target[path[-1]]
                else:
                    target[path[-1]] = value
                self.assertEqual((await tools.inspect_deck())["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_full_validates_body_and_tips_and_projects_every_level(self):
        cases = [{"description": None}, {"hover_tips": None}, {"hover_tips": [None]},
                 {"hover_tips": [{}]}, {"hover_tips": [{"title": 1, "description": "x"}]},
                 {"hover_tips": [{"title": None, "description": False}]}]
        for invalid in cases:
            with self.subTest(invalid=invalid), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                game.deck_payload["deck"][0].update(invalid)
                self.assertEqual((await tools.inspect_deck({"detail_level": "full"}))["error"]["code"], "transport_error")
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            expected = await tools.inspect_deck({"detail_level": "full"})
            game.deck_payload.update(hand=[{"secret": 1}], notes={"secret": 1}, available_actions=["end_turn"])
            game.deck_payload["deck"][0].update(secret=1, card_ids=["bad"])
            game.deck_payload["deck"][0]["hover_tips"][0].update(secret=1, card_ids=["bad"])
            original = json.dumps(game.deck_payload)
            self.assertEqual(await tools.inspect_deck({"detail_level": "full"}), expected)
            self.assertEqual(json.dumps(game.deck_payload), original)
            game.deck_payload["deck"] = []
            self.assertEqual((await tools.inspect_deck())["deck"], [])
            self.assertEqual((await tools.inspect_deck({"detail_level": "full"}))["hover_tips"], [])

    async def test_close_only_returns_basic_observation_fields(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.inspect_deck()
            game.close_payload.update(deck=[{"secret": 1}], detail_level="full", sort={}, view_upgrades=True,
                                      hover_tips=[{"secret": 1}], slot_tip={}, relics=[{"secret": 1}], ui_generation=99)
            result = await tools.close_card_view()
            self.assertEqual(set(result), {"scene", "screen", "turn", "player", "enemies", "top_bar", "buttons", "available_actions"})

    async def test_close_preserves_underlying_map_and_rejects_combat_input(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.inspect_deck()
            game.map_open = True
            game.close_payload.update(screen={"status": "covered", "view": "map", "private": True},
                                      player=None, enemies=None, top_bar=None, buttons=None, available_actions=[])
            result = await tools.close_card_view()
            self.assertEqual(result["screen"], {"status": "covered", "view": "map"})
            self.assertEqual(result["available_actions"], [])
            self.assertEqual((await tools.end_turn())["error"]["code"], "illegal_action")

    async def test_malformed_close_observation_clears_permission(self):
        for invalid in [{"screen": None}, {"screen": {}}, {"screen": {"status": False}},
                        {"screen": {"status": "covered", "view": 1}}, {"scene": None}, {"available_actions": None}]:
            with self.subTest(invalid=invalid), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                await tools.inspect_deck()
                await tools.get_observation()
                game.close_payload.update(invalid)
                self.assertEqual((await tools.close_card_view())["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_ui_errors_and_timeouts_do_not_restore_permission_or_retry(self):
        for operation in ("inspect_deck", "close_card_view"):
            for timeout in (False, True):
                with self.subTest(operation=operation, timeout=timeout), FakeGame() as game:
                    tools = self.tools_type(Client(game.directory, timeout=.1))
                    if operation == "close_card_view":
                        await tools.inspect_deck()
                    await tools.get_observation()
                    attribute = ("drop_deck_response" if operation == "inspect_deck" else "drop_close_response") if timeout else (
                        "deck_error" if operation == "inspect_deck" else "close_error")
                    setattr(game, attribute, True)
                    before = len(game.operations)
                    result = await getattr(tools, operation)()
                    self.assertEqual(result["error"]["code"], "timeout" if timeout else "illegal_action")
                    self.assertNotIn("/private", json.dumps(result))
                    self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
                    self.assertEqual([op["operation"] for op in game.operations[before:]], [operation])

    async def test_cancelled_ui_operation_does_not_send_cleanup_or_restore_permission(self):
        for operation in ("inspect_deck", "close_card_view"):
            with self.subTest(operation=operation), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                if operation == "close_card_view": await tools.inspect_deck()
                await tools.get_observation()
                game.observation_started.clear()
                game.release_observation.clear()
                scopes = []

                async def invoke():
                    with anyio.CancelScope() as scope:
                        scopes.append(scope)
                        await getattr(tools, operation)()

                before = len(game.operations)
                async with anyio.create_task_group() as group:
                    group.start_soon(invoke)
                    self.assertTrue(await anyio.to_thread.run_sync(game.observation_started.wait, 2))
                    scopes[0].cancel()
                    game.release_observation.set()
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
                self.assertEqual([op["operation"] for op in game.operations[before:]], [operation])


if __name__ == "__main__":
    unittest.main()
