from scripts._bootstrap import ROOT
import asyncio
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import anyio

from sts2_mcp.roundtrip_client import Client


SERVER = (ROOT / "scripts/mcp_server.py")


from tests.python.support.fake_game import FakeGame, map_payload


class GameToolsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.assertTrue(SERVER.exists(), "MCP server has not been implemented.")
        from sts2_mcp.mcp_server import GameTools
        self.tools_type = GameTools

    async def test_relic_inspection_shares_tips_and_supports_action(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            self.assertEqual(await tools.inspect_relics({"preset": "full"}), {
                "relics": [
                    {"name": "Anchor", "counter": None, "description": "Start with 10 Block."},
                    {"name": "Pen Nib", "counter": 0, "description": "Every 10th Attack."},
                    {"name": "Anchor", "counter": None, "description": "Start with 10 Block."},
                ], "hover_tips": [{"title": "Block", "description": "Prevents damage.", "relic_indices": [0, 2]}],
            })
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["inspect_relics", "end_turn"])

    async def test_relic_inspection_rejects_malformed_details_and_clears_token(self):
        missing = object()
        cases = [
            (("relics",), missing), (("relics",), None), (("relics",), {}), (("relics",), [None]),
            (("relics", 0, "name"), missing), (("relics", 0, "name"), 1),
            (("relics", 0, "counter"), missing), (("relics", 0, "counter"), True),
            (("relics", 0, "counter"), "2"), (("relics", 0, "counter"), 1.5),
            (("relics", 0, "counter"), -2147483649), (("relics", 0, "counter"), 2147483648),
            (("relics", 0, "description"), missing), (("relics", 0, "description"), None),
            (("relics", 0, "hover_tips"), missing), (("relics", 0, "hover_tips"), None),
            (("relics", 0, "hover_tips"), {}), (("relics", 0, "hover_tips"), [None]),
            (("relics", 0, "hover_tips", 0, "title"), missing),
            (("relics", 0, "hover_tips", 0, "title"), []),
            (("relics", 0, "hover_tips", 0, "description"), missing),
            (("relics", 0, "hover_tips", 0, "description"), False),
            (("snapshot_id",), None), (("snapshot_id",), ""),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                await tools.get_observation()
                target = game.relic_payload
                for key in path[:-1]:
                    target = target[key]
                if value is missing:
                    del target[path[-1]]
                else:
                    target[path[-1]] = value
                result = await tools.inspect_relics()
                self.assertEqual(result["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_relic_inspection_only_forwards_contract_fields(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            expected = await tools.inspect_relics()
            payload = game.relic_payload
            payload.update(scene="combat", hand=[{"id": 1}], enemies=[{"intents": [{"value": "7"}]}],
                           available_actions=["end_turn"], hover_tips=[{"seed": "private"}], notes={"secret": True})
            payload["relics"][0].update(model_id="private", relic_indices=[99], hidden_counter=100)
            payload["relics"][0]["hover_tips"][0].update(debug="private", relic_indices=[99])
            original = json.dumps(payload)
            self.assertEqual(await tools.inspect_relics(), expected)
            self.assertEqual(json.dumps(payload), original)

    async def test_relic_inspection_accepts_empty_nullable_and_counter_boundaries(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            game.relic_payload = {"relics": []}
            self.assertEqual(await tools.inspect_relics({"preset": "full"}), {"relics": [], "hover_tips": []})
            for counter in [None, 0, -2147483648, 2147483647]:
                game.relic_payload["relics"] = [{"name": None, "counter": counter, "description": "Text", "hover_tips": [
                    {"title": None, "description": "One"}, {"title": None, "description": "One"},
                    {"title": None, "description": "Two"}]}]
                self.assertEqual(await tools.inspect_relics({"preset": "full"}), {
                    "relics": [{"name": None, "counter": counter, "description": "Text"}],
                    "hover_tips": [{"title": None, "description": "One", "relic_indices": [0]},
                                   {"title": None, "description": "Two", "relic_indices": [0]}],
                })

    async def test_relic_inspection_preserves_an_unchanged_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            await tools.inspect_relics()
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")

    async def test_relic_inspection_refreshes_a_changed_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            self.assertNotIn("error", await tools.inspect_relics())
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_relics", "end_turn"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_rejected_relic_inspection_retains_token_and_sanitizes_game_error(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.relic_error = True
            result = await tools.inspect_relics()
            self.assertEqual(result["error"]["code"], "illegal_action")
            self.assertEqual(result["error"]["recovery"], "choose_legal_action")
            self.assertNotIn("/private", json.dumps(result))
            self.assertTrue((await tools.end_turn())["transition"]["complete"])

    async def test_timed_out_relic_inspection_clears_token_without_retry(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory, timeout=0.1))
            await tools.get_observation()
            game.drop_relic_response = True
            self.assertEqual((await tools.inspect_relics())["error"]["code"], "timeout")
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_relics"])

    async def test_cancelled_relic_inspection_does_not_restore_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.observation_started.clear()
            game.release_observation.clear()
            scopes = []

            async def inspect():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.inspect_relics()

            async with anyio.create_task_group() as group:
                group.start_soon(inspect)
                started = await anyio.to_thread.run_sync(game.observation_started.wait, 2)
                self.assertTrue(started, "Relic inspection did not reach the game transport.")
                scopes[0].cancel()
                game.release_observation.set()
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_relics"])

    async def test_combatant_inspection_is_read_only_and_preserves_shared_sources(self):
        from sts2_mcp.roundtrip_client import ENEMY_ATTACK_INTENT_NOTE
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            self.assertEqual(await tools.inspect_combatants(), {
                "scene": "combat", "screen": {"status": "visible"}, "player": {"powers": [{"name": "Vulnerable", "amount": 2}]},
                "enemies": [{"id": 7, "name": "Twig Slime (M)",
                             "powers": [{"name": "Vulnerable", "amount": 2}],
                             "intents": [{"category": "attack", "value": "11"}]}],
                "hover_tips": [
                    {"title": "Vulnerable", "description": "Receive 50% more damage for 2 turns.",
                     "sources": ["player.powers.0", "enemies.0.powers.0"]},
                    {"title": "Aggressive", "description": "This enemy intends to Attack for 11 damage.",
                     "sources": ["enemies.0.intents.0"]},
                ],
                "notes": {"enemy_attack_intents": ENEMY_ATTACK_INTENT_NOTE},
            })
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["inspect_combatants", "end_turn"])

    async def test_combatant_inspection_preserves_an_unchanged_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            await tools.inspect_combatants()
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")

    async def test_combatant_inspection_refreshes_a_changed_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            self.assertNotIn("error", await tools.inspect_combatants())
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_combatants", "end_turn"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_combatant_inspection_rejects_malformed_data_or_sources_and_clears_token(self):
        missing = object()
        cases = [
            (("scene",), missing), (("scene",), "invalid_scene"), (("player",), missing), (("player",), []),
            (("player", "powers"), missing), (("player", "powers"), {}),
            (("player", "powers"), [None]), (("player", "powers", 0, "name"), missing),
            (("player", "powers", 0, "name"), 1), (("player", "powers", 0, "amount"), missing),
            (("player", "powers", 0, "amount"), True), (("player", "powers", 0, "amount"), "2"),
            (("enemies",), missing), (("enemies",), None), (("enemies",), [None]),
            (("enemies", 0, "id"), missing), (("enemies", 0, "id"), True),
            (("enemies", 0, "id"), -1), (("enemies", 0, "id"), 4294967296),
            (("enemies", 0, "name"), missing), (("enemies", 0, "name"), {}),
            (("enemies", 0, "powers"), [False]), (("enemies", 0, "intents"), missing),
            (("enemies", 0, "intents"), {}), (("enemies", 0, "intents"), [None]),
            (("enemies", 0, "intents", 0, "category"), missing),
            (("enemies", 0, "intents", 0, "category"), []),
            (("enemies", 0, "intents", 0, "value"), missing), (("enemies", 0, "intents", 0, "value"), 11),
            (("hover_tips",), missing), (("hover_tips",), None), (("hover_tips",), [None]),
            (("hover_tips", 0, "title"), missing), (("hover_tips", 0, "title"), 1),
            (("hover_tips", 0, "description"), missing), (("hover_tips", 0, "description"), None),
            (("hover_tips", 0, "sources"), missing), (("hover_tips", 0, "sources"), []),
            (("hover_tips", 0, "sources"), "player.powers.0"), (("hover_tips", 0, "sources"), [None]),
            (("hover_tips", 0, "sources"), ["player.hand.0"]),
            (("hover_tips", 0, "sources"), ["enemies.3.powers.0"]),
            (("hover_tips", 0, "sources"), ["enemies.0.powers.9"]),
            (("hover_tips", 0, "sources"), ["enemies.-1.powers.0"]),
            (("hover_tips", 0, "sources"), ["enemies.00.powers.0"]),
            (("hover_tips", 0, "sources"), ["player.powers.0", "player.powers.0"]),
            (("hover_tips", 1), {"title": "Vulnerable", "description": "Receive 50% more damage for 2 turns.",
                                  "sources": ["enemies.0.intents.0"]}),
            (("player", "powers"), None),
        ]
        for path, value in cases:
            with self.subTest(path=path, value=value), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                await tools.get_observation()
                target = game.combatant_payload
                for key in path[:-1]:
                    target = target[key]
                if value is missing:
                    del target[path[-1]]
                else:
                    target[path[-1]] = value
                result = await tools.inspect_combatants()
                self.assertEqual(result["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_combatant_inspection_only_forwards_contract_fields(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            expected = await tools.inspect_combatants()
            payload = game.combatant_payload
            payload.update(hand=[{"id": 9}], available_actions=["end_turn"], top_bar={"seed": "private"},
                           notes={"card_values": "private"})
            payload["player"].update(hand=[{"seed": "private"}], hp=80)
            payload["player"]["powers"][0]["model_id"] = "private"
            payload["enemies"][0].update(next_move="private", hp=20)
            payload["enemies"][0]["powers"][0]["model_id"] = "private"
            payload["enemies"][0]["intents"][0]["future"] = "private"
            payload["hover_tips"][0]["debug"] = "private"
            self.assertEqual(await tools.inspect_combatants(), expected)
            self.assertEqual(payload["hover_tips"][0]["debug"], "private")

    async def test_combatant_inspection_preserves_unknown_and_empty_containers_without_notes(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            game.combatant_payload = {"scene": "combat", "screen": {"status": "visible"}, "player": None, "enemies": [], "hover_tips": []}
            self.assertEqual(await tools.inspect_combatants({"preset": "full"}), game.combatant_payload)
            for powers, intents in ((None, None), ([], [])):
                game.combatant_payload = {
                    "scene": "combat", "screen": {"status": "visible"}, "player": {"powers": powers},
                    "enemies": [{"id": None, "name": None, "powers": powers, "intents": intents}], "hover_tips": [],
                }
                self.assertEqual(await tools.inspect_combatants({"preset": "full"}), game.combatant_payload)
            game.combatant_payload["player"]["powers"] = [{"name": None, "amount": None}]
            game.combatant_payload["hover_tips"] = [{"title": None, "description": "Text", "sources": ["player.powers.0"]}]
            self.assertEqual(await tools.inspect_combatants({"preset": "full"}), game.combatant_payload)
            game.combatant_payload["player"]["powers"][0]["amount"] = -2
            game.combatant_payload["enemies"][0].update(id=4294967295, intents=[{"category": None, "value": None}])
            from sts2_mcp.roundtrip_client import ENEMY_ATTACK_INTENT_NOTE
            self.assertEqual(await tools.inspect_combatants({"preset": "full"}), {
                **game.combatant_payload, "notes": {"enemy_attack_intents": ENEMY_ATTACK_INTENT_NOTE}})

    async def test_rejected_combatant_inspection_retains_token_and_sanitizes_private_message(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.combatant_error = True
            result = await tools.inspect_combatants()
            self.assertEqual(result["error"]["code"], "illegal_action")
            self.assertEqual(result["error"]["recovery"], "choose_legal_action")
            self.assertNotIn("/private", json.dumps(result))
            self.assertTrue((await tools.end_turn())["transition"]["complete"])

    async def test_timed_out_combatant_inspection_clears_token_without_retry(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory, timeout=0.1))
            await tools.get_observation()
            game.drop_combatant_response = True
            self.assertEqual((await tools.inspect_combatants())["error"]["code"], "timeout")
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_combatants"])

    async def test_cancelled_combatant_inspection_does_not_restore_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.observation_started.clear()
            game.release_observation.clear()
            scopes = []

            async def inspect():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.inspect_combatants()

            async with anyio.create_task_group() as group:
                group.start_soon(inspect)
                started = await anyio.to_thread.run_sync(game.observation_started.wait, 2)
                self.assertTrue(started, "Combatant inspection did not reach the game transport.")
                scopes[0].cancel()
                game.release_observation.set()
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_combatants"])

    async def test_potion_inspection_shares_tips_preserves_slots_and_supports_action(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            self.assertEqual(await tools.inspect_potions(), {
                "slot_tip": {"title": "Potion Slot", "description": "Use potions during combat."},
                "potion_slots": [{"name": "Block Potion", "description": "Gain 12 Block."}, None,
                                 {"name": "Block Potion", "description": "Gain 12 Block."}],
                "hover_tips": [{"title": "Block", "description": "Prevents damage.", "slot_indices": [0, 2]}],
            })
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["inspect_potions", "end_turn"])

    async def test_potion_inspection_preserves_an_unchanged_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            await tools.inspect_potions()
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")

    async def test_potion_inspection_refreshes_a_changed_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            self.assertNotIn("error", await tools.inspect_potions())
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_potions", "end_turn"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_potion_inspection_rejects_malformed_details_and_clears_token(self):
        cases = [
            {}, {"slot_tip": None}, {"slot_tip": {"description": "Text"}},
            {"slot_tip": {"title": 3, "description": "Text"}},
            {"slot_tip": {"title": "Potion Slot", "description": None}},
            {"potion_slots": None}, {"potion_slots": {}}, {"potion_slots": [False]},
            {"potion_slots": [{}]},
            {"potion_slots": [{"name": 3, "description": "Text", "hover_tips": []}]},
            {"potion_slots": [{"description": "Text", "hover_tips": []}]},
            {"potion_slots": [{"name": "Potion", "description": None, "hover_tips": []}]},
            {"potion_slots": [{"name": "Potion", "description": "Text"}]},
            {"potion_slots": [{"name": "Potion", "description": "Text", "hover_tips": None}]},
        ]
        for tip in [None, {}, {"description": "Text"}, {"title": [], "description": "Text"},
                    {"title": "Block", "description": 3}]:
            cases.append({"potion_slots": [{"name": "Potion", "description": "Text", "hover_tips": [tip]}]})
        for malformed in cases:
            with self.subTest(malformed=malformed), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                await tools.get_observation()
                if malformed:
                    game.potion_payload.update(malformed)
                else:
                    game.potion_payload.clear()
                result = await tools.inspect_potions()
                self.assertEqual(result["error"]["code"], "transport_error")
                self.assertNotIn("/private", json.dumps(result))
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_potion_inspection_only_forwards_potion_fields(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            expected = await tools.inspect_potions()
            game.potion_payload.update(scene="combat", enemies=[{"intents": [{"value": "7"}]}],
                                      hand=[{"id": 9}], available_actions=["end_turn"], hover_tips=[{"seed": "private"}])
            game.potion_payload["slot_tip"]["debug"] = "private"
            game.potion_payload["potion_slots"][0].update(model_id="private", slot_indices=[99])
            game.potion_payload["potion_slots"][0]["hover_tips"][0]["debug"] = "private"
            self.assertEqual(await tools.inspect_potions(), expected)
            self.assertEqual(game.potion_payload["slot_tip"]["debug"], "private")

    async def test_potion_inspection_accepts_empty_slots_nullable_text_and_distinct_tip_bodies(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            game.potion_payload["potion_slots"][0]["name"] = None
            game.potion_payload["potion_slots"][0]["hover_tips"][0]["title"] = None
            game.potion_payload["slot_tip"]["title"] = None
            game.potion_payload["potion_slots"][2]["hover_tips"].append({"title": "Block", "description": "Different."})
            result = await tools.inspect_potions({"preset": "full"})
            self.assertIsNone(result["slot_tip"]["title"])
            self.assertIsNone(result["potion_slots"][0]["name"])
            self.assertEqual(result["hover_tips"], [
                {"title": None, "description": "Prevents damage.", "slot_indices": [0]},
                {"title": "Block", "description": "Prevents damage.", "slot_indices": [2]},
                {"title": "Block", "description": "Different.", "slot_indices": [2]},
            ])
            for slots in ([None, None], []):
                game.potion_payload["potion_slots"] = slots
                self.assertEqual(await tools.inspect_potions({"preset": "full"}), {
                    "slot_tip": {"title": None, "description": "Use potions during combat."},
                    "potion_slots": slots, "hover_tips": [],
                })

    async def test_rejected_potion_inspection_retains_token_and_sanitizes_game_error(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.potion_error = True
            result = await tools.inspect_potions()
            self.assertEqual(result["error"]["code"], "illegal_action")
            self.assertEqual(result["error"]["recovery"], "choose_legal_action")
            self.assertNotIn("/private", json.dumps(result))
            self.assertTrue((await tools.end_turn())["transition"]["complete"])

    async def test_timed_out_potion_inspection_clears_token_without_retry(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory, timeout=0.1))
            await tools.get_observation()
            game.drop_potion_response = True
            self.assertEqual((await tools.inspect_potions())["error"]["code"], "timeout")
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_potions"])

    async def test_cancelled_potion_inspection_does_not_restore_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.observation_started.clear()
            game.release_observation.clear()
            scopes = []

            async def inspect():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.inspect_potions()

            async with anyio.create_task_group() as group:
                group.start_soon(inspect)
                started = await anyio.to_thread.run_sync(game.observation_started.wait, 2)
                self.assertTrue(started, "Potion inspection did not reach the game transport.")
                scopes[0].cancel()
                game.release_observation.set()
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_potions"])

    async def test_ui_inspection_supports_an_action(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            self.assertEqual(await tools.inspect_ui(), game.ui_payload)
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["inspect_ui", "end_turn"])

    async def test_ui_inspection_preserves_an_unchanged_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            await tools.inspect_ui()
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")

    async def test_ui_inspection_refreshes_a_changed_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            self.assertNotIn("error", await tools.inspect_ui())
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_ui", "end_turn"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_ui_inspection_rejects_malformed_details_and_clears_token(self):
        cases = [
            {"scene": "invalid_scene"}, {"hover_tips": None}, {"hover_tips": [None]},
            {"hover_tips": [{"title": 3, "description": "Text", "sources": ["player.energy"]}]},
            {"hover_tips": [{"title": "Energy", "description": None, "sources": ["player.energy"]}]},
            {"hover_tips": [{"title": "Energy", "description": "Text", "sources": "player.energy"}]},
            {"hover_tips": [{"title": "Energy", "description": "Text", "sources": []}]},
            {"hover_tips": [{"title": "Energy", "description": "Text", "sources": [None]}]},
        ]
        for malformed in cases:
            with self.subTest(malformed=malformed), FakeGame() as game:
                tools = self.tools_type(Client(game.directory))
                await tools.get_observation()
                game.ui_payload.update(malformed)
                self.assertEqual((await tools.inspect_ui())["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_rejected_ui_inspection_preserves_token_and_sanitizes_private_message(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.ui_error = True
            result = await tools.inspect_ui()
            self.assertEqual(result["error"]["code"], "illegal_action")
            self.assertEqual(result["error"]["recovery"], "choose_legal_action")
            self.assertNotIn("/private", result["error"]["message"])
            self.assertNotIn('error', await tools.end_turn())

    async def test_ui_inspection_only_forwards_ui_fields(self):
        with FakeGame() as game:
            expected = json.loads(json.dumps(game.ui_payload))
            game.ui_payload.update(enemies=[{"intents": [{"value": "7"}]}],
                                   available_actions=["end_turn"], hand=[{"id": 9}], overlay={"seed": "private"})
            game.ui_payload["hover_tips"][0]["debug"] = "private"
            result = await self.tools_type(Client(game.directory)).inspect_ui()
            self.assertEqual(result, expected)
            self.assertEqual(game.ui_payload["hover_tips"][0]["debug"], "private")

    async def test_ui_inspection_accepts_empty_tips_and_nullable_titles(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            game.ui_payload["hover_tips"][0]["title"] = None
            self.assertIsNone((await tools.inspect_ui({"preset": "full"}))["hover_tips"][0]["title"])
            game.ui_payload["hover_tips"] = []
            self.assertEqual(await tools.inspect_ui({"preset": "full"}), {"scene": "combat", "screen": {"status": "visible"}, "hover_tips": []})

    async def test_cancelled_ui_inspection_does_not_restore_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.observation_started.clear()
            game.release_observation.clear()
            scopes = []

            async def inspect():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.inspect_ui()

            async with anyio.create_task_group() as group:
                group.start_soon(inspect)
                started = await anyio.to_thread.run_sync(game.observation_started.wait, 2)
                self.assertTrue(started, "UI inspection did not reach the game transport.")
                scopes[0].cancel()
                game.release_observation.set()
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_ui"])

    async def test_inspection_supports_an_action(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            result = await tools.inspect_hand()
            self.assertEqual(set(result), {"hand", "hover_tips", "notes"})
            self.assertEqual([card["id"] for card in result["hand"]], [9, 2])
            self.assertEqual(result["hover_tips"], [{"title": "Block",
                "description": "Until next turn, prevents damage.", "card_ids": [9, 2]}])
            self.assertEqual(set(result["notes"]), {"card_values"})
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["inspect_hand", "end_turn"])

    async def test_inspection_preserves_an_unchanged_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            await tools.inspect_hand()
            result = await tools.end_turn()
            self.assertTrue(result["transition"]["complete"])
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")

    async def test_inspection_does_not_forward_combat_fields_from_game_response(self):
        with FakeGame() as game:
            game.hand_extra_state = True
            result = await self.tools_type(Client(game.directory)).inspect_hand()
            self.assertEqual(set(result), {"hand", "hover_tips", "notes"})
            self.assertEqual(set(result["notes"]), {"card_values"})

    async def test_malformed_hand_card_is_reported_as_a_transport_error(self):
        with FakeGame() as game:
            game.malformed_hand_item = True
            result = await self.tools_type(Client(game.directory)).inspect_hand()
            self.assertEqual(result["error"]["code"], "transport_error")

    async def test_inspection_refreshes_a_changed_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.turn = 2
            self.assertNotIn("error", await tools.inspect_hand())
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_hand", "end_turn"])
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")

    async def test_failed_inspection_invalidates_the_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.malformed_hand = True
            result = await tools.inspect_hand()
            self.assertEqual(result["error"]["code"], "transport_error")
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_cancelled_inspection_does_not_restore_the_observation_token(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            await tools.get_observation()
            game.observation_started.clear()
            game.release_observation.clear()
            scopes = []

            async def inspect():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.inspect_hand()

            async with anyio.create_task_group() as group:
                group.start_soon(inspect)
                started = await anyio.to_thread.run_sync(game.observation_started.wait, 2)
                self.assertTrue(started, "Hand inspection did not reach the game transport.")
                scopes[0].cancel()
                game.release_observation.set()
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([item["operation"] for item in game.operations], ["get_state", "inspect_hand"])

    async def test_action_requires_explicit_observation_without_sending_request(self):
        with FakeGame() as game:
            result = await self.tools_type(Client(game.directory)).end_turn()
            self.assertEqual(result["error"]["code"], "observation_required")
            self.assertEqual(result["error"]["recovery"], "get_observation")
            self.assertEqual(game.operations, [])

    async def test_observation_filters_metadata_and_actions_advance_tokens(self):
        with FakeGame() as game:
            tools = self.tools_type(Client(game.directory))
            before = await tools.get_observation()
            self.assertEqual(before["turn"], 1)
            self.assertEqual(before["available_actions"], ["end_turn"])
            self.assertFalse({"ok", "state", "snapshot_id", "session", "schema_version", "overlay"} & before.keys())
            after = await tools.end_turn()
            self.assertTrue(after["transition"]["complete"])
            self.assertEqual(game.turn, 2)
            self.assertEqual(game.operations[-1]["expected_state"], "state-1")
            following = await tools.end_turn()
            self.assertTrue(following["transition"]["complete"])
            self.assertEqual(game.turn, 3)
            self.assertEqual(len(game.operations), 3)
            self.assertEqual(game.operations[-1]["expected_state"], "state-2")
            self.assertEqual((await tools.get_observation())["turn"], 3)
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 4)
            self.assertEqual(game.operations[-1]["expected_state"], "state-3")

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
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 3)

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
            self.assertEqual([result.get("transition", {}).get("stop_reason") for result in results], ["player_ready", None])
            self.assertEqual(game.turn, 2)
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
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory), "--config", str(game.config)])
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    listed = await session.list_tools()
                    self.assertEqual({tool.name for tool in listed.tools}, {"inspect_run_result", "run_result_option", "get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map", "inspect_selection", "select_card", "selection_option", "set_selection_view", "inspect_targets", "play_card", "play_cards", "use_potion", "discard_potion", "end_turn", "inspect_rewards", "claim_reward", "proceed", "inspect_rest_site", "choose_rest_option", "loot_treasure", "inspect_treasure", "open_shop", "close_shop", "inspect_shop", "buy_item", "inspect_ancient", "choose_ancient_option", "advance_dialogue", "inspect_event", "choose_event_option", "set_divination_tool", "divine", "respond_to_confirmation", "travel_to_node"})
                    inspection_tool = next(tool for tool in listed.tools if tool.name == "inspect_hand")
                    self.assertTrue(inspection_tool.annotations.readOnlyHint)
                    self.assertEqual(set(inspection_tool.inputSchema["properties"]), {"preset", "card_ids"})
                    ui_tool = next(tool for tool in listed.tools if tool.name == "inspect_ui")
                    self.assertTrue(ui_tool.annotations.readOnlyHint)
                    potion_tool = next(tool for tool in listed.tools if tool.name == "inspect_potions")
                    self.assertTrue(potion_tool.annotations.readOnlyHint)
                    self.assertEqual(set(potion_tool.inputSchema["properties"]), {"preset", "slot_indices"})
                    combatant_tool = next(tool for tool in listed.tools if tool.name == "inspect_combatants")
                    self.assertTrue(combatant_tool.annotations.readOnlyHint)
                    self.assertEqual(set(combatant_tool.inputSchema["properties"]), {"preset", "sources"})
                    relic_tool = next(tool for tool in listed.tools if tool.name == "inspect_relics")
                    self.assertTrue(relic_tool.annotations.readOnlyHint)
                    self.assertEqual(set(relic_tool.inputSchema['properties']), {'preset', 'relic_indices'})
                    deck_tool = next(tool for tool in listed.tools if tool.name == "inspect_deck")
                    self.assertFalse(deck_tool.annotations.readOnlyHint)
                    self.assertFalse(deck_tool.annotations.destructiveHint)
                    self.assertFalse(deck_tool.annotations.idempotentHint)
                    self.assertEqual(set(deck_tool.inputSchema["properties"]), {"preset", "card_ids", "view_upgrades", "sort_by", "descending"})
                    pile_tool = next(tool for tool in listed.tools if tool.name == "inspect_pile")
                    self.assertFalse(pile_tool.annotations.readOnlyHint)
                    self.assertFalse(pile_tool.annotations.destructiveHint)
                    self.assertFalse(pile_tool.annotations.idempotentHint)
                    self.assertEqual(pile_tool.inputSchema["required"], ["pile"])
                    self.assertEqual(set(pile_tool.inputSchema["properties"]), {"preset", "pile", "card_ids"})
                    close_tool = next(tool for tool in listed.tools if tool.name == "close_card_view")
                    self.assertFalse(close_tool.annotations.readOnlyHint)
                    self.assertEqual(set(close_tool.inputSchema["properties"]), {"preset"})
                    reward_tool = next(tool for tool in listed.tools if tool.name == "inspect_rewards")
                    self.assertEqual(set(reward_tool.inputSchema["properties"]), {"preset", "reward_ids"})
                    for tool in listed.tools:
                        if tool.name not in {"inspect_potions", "inspect_combatants", "inspect_ui", "get_observation", "inspect_hand", "inspect_selection", "inspect_relics", "inspect_map", "inspect_deck", "inspect_pile", "inspect_rewards", "select_card", "selection_option", "set_selection_view", "inspect_targets", "play_card", "play_cards", "use_potion", "discard_potion", "claim_reward", "choose_rest_option", "loot_treasure", "buy_item", "choose_ancient_option", "choose_event_option", "set_divination_tool", "divine", "respond_to_confirmation", "travel_to_node", "run_result_option"}:
                            self.assertEqual(set(tool.inputSchema["properties"]), {"preset"})
                    missing = await session.call_tool("end_turn", {})
                    self.assertTrue(missing.isError)
                    self.assertEqual(missing.structuredContent["error"]["code"], "observation_required")
                    before = await session.call_tool("get_observation", {})
                    self.assertFalse(before.isError)
                    self.assertEqual(before.structuredContent["turn"], 1)
                    self.assertEqual(json.loads(before.content[0].text), before.structuredContent)
                    self.assertNotIn("snapshot_id", before.structuredContent)
                    inspected = await session.call_tool("inspect_hand", {})
                    self.assertFalse(inspected.isError)
                    self.assertEqual(set(inspected.structuredContent), {"hand", "hover_tips", "notes"})
                    self.assertEqual(json.loads(inspected.content[0].text), inspected.structuredContent)
                    ui = await session.call_tool("inspect_ui", {})
                    self.assertFalse(ui.isError)
                    self.assertEqual(ui.structuredContent, game.ui_payload)
                    self.assertEqual(json.loads(ui.content[0].text), ui.structuredContent)
                    potions = await session.call_tool("inspect_potions", {})
                    self.assertFalse(potions.isError)
                    self.assertEqual(set(potions.structuredContent), {"slot_tip", "potion_slots", "hover_tips"})
                    self.assertIsNone(potions.structuredContent["potion_slots"][1])
                    self.assertEqual(potions.structuredContent["hover_tips"][0]["slot_indices"], [0, 2])
                    self.assertEqual(json.loads(potions.content[0].text), potions.structuredContent)
                    invalid_potions = await session.call_tool("inspect_potions", {"slot_index": 0})
                    self.assertTrue(invalid_potions.isError)
                    self.assertEqual(invalid_potions.structuredContent["error"]["code"], "invalid_request")
                    combatants = await session.call_tool("inspect_combatants", {})
                    self.assertFalse(combatants.isError)
                    self.assertEqual(set(combatants.structuredContent), {"scene", "screen", "player", "enemies", "hover_tips", "notes"})
                    self.assertEqual(combatants.structuredContent["enemies"][0]["intents"][0]["value"], "11")
                    self.assertEqual(json.loads(combatants.content[0].text), combatants.structuredContent)
                    relics = await session.call_tool("inspect_relics", {})
                    self.assertFalse(relics.isError)
                    self.assertEqual(set(relics.structuredContent), {"relics", "hover_tips"})
                    self.assertEqual(relics.structuredContent["relics"][1]["counter"], 0)
                    self.assertEqual(relics.structuredContent["hover_tips"][0]["relic_indices"], [0, 2])
                    self.assertEqual(json.loads(relics.content[0].text), relics.structuredContent)
                    invalid_relics = await session.call_tool("inspect_relics", {"relic_index": 0})
                    self.assertTrue(invalid_relics.isError)
                    self.assertEqual(invalid_relics.structuredContent["error"]["code"], "invalid_request")
                    invalid_combatants = await session.call_tool("inspect_combatants", {"enemy_id": 7})
                    self.assertTrue(invalid_combatants.isError)
                    self.assertEqual(invalid_combatants.structuredContent["error"]["code"], "invalid_request")
                    invalid_ui = await session.call_tool("inspect_ui", {"target": "energy"})
                    self.assertTrue(invalid_ui.isError)
                    self.assertEqual(invalid_ui.structuredContent["error"]["code"], "invalid_request")
                    invalid_inspection = await session.call_tool("inspect_hand", {"card_id": 9})
                    self.assertTrue(invalid_inspection.isError)
                    self.assertEqual(invalid_inspection.structuredContent["error"]["code"], "invalid_request")
                    invalid = await session.call_tool("end_turn", {"unexpected": True})
                    self.assertTrue(invalid.isError)
                    self.assertEqual(game.turn, 1)
                    executed = await session.call_tool("end_turn", {})
                    self.assertFalse(executed.isError)
                    self.assertTrue(executed.structuredContent["transition"]["complete"])
                    self.assertEqual(game.turn, 2)
                    following = await session.call_tool("end_turn", {})
                    self.assertFalse(following.isError)
                    self.assertTrue(following.structuredContent["transition"]["complete"])
                    self.assertEqual(game.turn, 3)
                    self.assertEqual([item["expected_state"] for item in game.operations if item["operation"] == "end_turn"],
                                     ["state-1", "state-2"])

                    deck = await session.call_tool("inspect_deck", {"preset": "full", "view_upgrades": True})
                    self.assertFalse(deck.isError)
                    self.assertEqual(json.loads(deck.content[0].text), deck.structuredContent)
                    self.assertEqual(deck.structuredContent["hover_tips"][0]["card_ids"], ["deck:0", "deck:1"])
                    repeated = await session.call_tool("inspect_deck", {})
                    self.assertTrue(repeated.structuredContent["view_upgrades"])
                    self.assertNotIn("detail_level", repeated.structuredContent)
                    self.assertIn("hover_tips", repeated.structuredContent)
                    invalid_deck = await session.call_tool("inspect_deck", {"view_upgrades": 1})
                    self.assertTrue(invalid_deck.isError)
                    self.assertEqual(invalid_deck.structuredContent["error"]["code"], "invalid_request")
                    invalid_close = await session.call_tool("close_card_view", {"screen": "map"})
                    self.assertTrue(invalid_close.isError)
                    self.assertEqual(invalid_close.structuredContent["error"]["code"], "invalid_request")
                    closed = await session.call_tool("close_card_view", {})
                    self.assertFalse(closed.isError)
                    self.assertEqual(json.loads(closed.content[0].text), closed.structuredContent)
                    self.assertFalse((await session.call_tool("end_turn", {})).isError)

                    invalid_pile = await session.call_tool("inspect_pile", {})
                    self.assertTrue(invalid_pile.isError)
                    self.assertEqual(invalid_pile.structuredContent["error"]["code"], "invalid_request")
                    for pile in ("draw", "discard", "exhaust"):
                        inspected = await session.call_tool("inspect_pile", {"pile": pile, "preset": "full"})
                        self.assertFalse(inspected.isError)
                        self.assertEqual(json.loads(inspected.content[0].text), inspected.structuredContent)
                        self.assertEqual(inspected.structuredContent["pile"], pile)
                        self.assertEqual(inspected.structuredContent["hover_tips"][0]["card_ids"], ["pile:0"])
                        self.assertEqual((await session.call_tool("end_turn", {})).structuredContent["error"]["code"], "illegal_action")
                    self.assertFalse((await session.call_tool("close_card_view", {})).isError)

    async def test_handshake_succeeds_when_another_controller_owns_game(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from sts2_mcp.mcp_server import ControllerLease
        with FakeGame() as game:
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory), "--config", str(game.config)])
            async with stdio_client(parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    with ControllerLease(game.directory):
                        await session.initialize()
                        listed = await session.list_tools()
                        self.assertEqual({tool.name for tool in listed.tools}, {"inspect_run_result", "run_result_option", "get_observation", "inspect_hand", "inspect_ui", "inspect_potions", "inspect_combatants", "inspect_relics", "inspect_deck", "inspect_pile", "close_card_view", "inspect_map", "close_map", "inspect_selection", "select_card", "selection_option", "set_selection_view", "inspect_targets", "play_card", "play_cards", "use_potion", "discard_potion", "end_turn", "inspect_rewards", "claim_reward", "proceed", "inspect_rest_site", "choose_rest_option", "loot_treasure", "inspect_treasure", "open_shop", "close_shop", "inspect_shop", "buy_item", "inspect_ancient", "choose_ancient_option", "advance_dialogue", "inspect_event", "choose_event_option", "set_divination_tool", "divine", "respond_to_confirmation", "travel_to_node"})
                        busy = await session.call_tool("get_observation", {})
                        self.assertTrue(busy.isError)
                        self.assertEqual(busy.structuredContent["error"]["code"], "controller_busy")
                        busy_hand = await session.call_tool("inspect_hand", {})
                        self.assertTrue(busy_hand.isError)
                        self.assertEqual(busy_hand.structuredContent["error"]["code"], "controller_busy")
                        busy_ui = await session.call_tool("inspect_ui", {})
                        self.assertTrue(busy_ui.isError)
                        self.assertEqual(busy_ui.structuredContent["error"]["code"], "controller_busy")
                        busy_potions = await session.call_tool("inspect_potions", {})
                        self.assertTrue(busy_potions.isError)
                        self.assertEqual(busy_potions.structuredContent["error"]["code"], "controller_busy")
                        busy_combatants = await session.call_tool("inspect_combatants", {})
                        self.assertTrue(busy_combatants.isError)
                        self.assertEqual(busy_combatants.structuredContent["error"]["code"], "controller_busy")
                        busy_relics = await session.call_tool("inspect_relics", {})
                        self.assertTrue(busy_relics.isError)
                        self.assertEqual(busy_relics.structuredContent["error"]["code"], "controller_busy")
                        busy_deck = await session.call_tool("inspect_deck", {})
                        self.assertEqual(busy_deck.structuredContent["error"]["code"], "controller_busy")
                        busy_pile = await session.call_tool("inspect_pile", {"pile": "draw"})
                        self.assertEqual(busy_pile.structuredContent["error"]["code"], "controller_busy")
                        busy_close = await session.call_tool("close_card_view", {})
                        self.assertEqual(busy_close.structuredContent["error"]["code"], "controller_busy")
                        self.assertEqual(game.operations, [])
                    inspected = await session.call_tool("inspect_ui", {})
                    self.assertFalse(inspected.isError)
                    recovered = await session.call_tool("get_observation", {})
                    self.assertFalse(recovered.isError)
                    self.assertEqual(recovered.structuredContent["turn"], 1)
            with ControllerLease(game.directory):
                pass

    async def test_idle_connection_does_not_own_controller_lock(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from sts2_mcp.mcp_server import ControllerLease
        with FakeGame() as game:
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory), "--config", str(game.config)])
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
            parameters = StdioServerParameters(command=sys.executable, args=[str(SERVER), "--ipc-dir", str(game.directory), "--config", str(game.config)])
            async with stdio_client(parameters) as (second_read, second_write):
                async with ClientSession(second_read, second_write) as second:
                    await second.initialize()
                    async with stdio_client(parameters) as (first_read, first_write):
                        async with ClientSession(first_read, first_write) as first:
                            await first.initialize()
                            self.assertFalse((await first.call_tool("inspect_deck", {})).isError)
                            busy = await second.call_tool("get_observation", {})
                            self.assertEqual(busy.structuredContent["error"]["code"], "controller_busy")
                            blocked = await second.call_tool("end_turn", {})
                            self.assertEqual(blocked.structuredContent["error"]["code"], "observation_required")
                            self.assertEqual(len(game.operations), 1)
                    recovered = await second.call_tool("get_observation", {})
                    self.assertFalse(recovered.isError)
                    self.assertEqual(recovered.structuredContent["turn"], 1)
                    self.assertEqual([item["operation"] for item in game.operations], ["inspect_deck", "get_state"])


if __name__ == "__main__":
    unittest.main()
