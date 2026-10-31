import copy
import json
import unittest

import anyio

from roundtrip_client import Client, player_result
from test_mcp_server import FakeGame


def opened(pile="draw", level="summary"):
    return {"scene": "card_pile", "pile": pile, "detail_level": level, "status": "opened",
            "screen": {"status": "covered", "view": pile + "_pile"}, "message": "Native pile information.",
            "cards": [{"id": "pile:0", "name": "Defend", "type": "Skill", "rarity": "basic",
                       "visual_card_pool": "ironclad", "energy_cost": "1", "star_cost": None,
                       "description": "Gain 5 Block.", "hover_tips": [
                           {"title": "Block", "description": "Prevents damage."}]}]}


class PileMcpTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_full_and_repeat_clear_permission_without_default_ui_options(self):
        from mcp_server import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            for pile in ("draw", "discard", "exhaust"):
                summary = await tools.inspect_pile({"pile": pile})
                self.assertEqual(summary["pile"], pile)
                self.assertEqual(summary["status"], "opened")
                self.assertEqual(summary["screen"], {"status": "covered", "view": pile + "_pile"})
                self.assertNotIn("description", summary["cards"][0])
                self.assertNotIn("hover_tips", summary)
                self.assertNotIn("notes", summary)
                self.assertEqual(game.operations[-1]["arguments"], {"pile": pile})
                full = await tools.inspect_pile({"pile": pile, "detail_level": "full"})
                self.assertEqual(full["cards"][0]["description"], "Gain 5 Block.")
                self.assertEqual(full["hover_tips"], [{"title": "Block", "description": "Prevents damage.",
                                                       "card_ids": ["pile:0"]}])
                self.assertEqual((await tools.inspect_pile({"pile": pile}))["cards"], summary["cards"])
                await tools.get_observation()
                await tools.inspect_pile({"pile": pile})
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
                await tools.close_card_view()

    async def test_invalid_arguments_do_not_reach_ipc_or_consume_existing_permission(self):
        from mcp_server import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            for args in (None, {}, [], False, {"pile": None}, {"pile": "deck"}, {"pile": 0},
                         {"pile": "draw", "view_upgrades": True}, {"pile": "draw", "sort_by": "cost"},
                         {"pile": "draw", "detail_level": None}, {"pile": "draw", "detail_level": "brief"}):
                with self.subTest(args=args):
                    self.assertEqual((await tools.inspect_pile(args))["error"]["code"], "invalid_request")
            self.assertEqual([op["operation"] for op in game.operations], ["get_state"])
            self.assertTrue((await tools.end_turn())["transition"]["complete"])
            self.assertEqual(game.turn, 2)

    async def test_empty_and_unavailable_are_successful_observations_not_action_authorization(self):
        from mcp_server import GameTools
        for status, pile, cards, screen in (("empty", "discard", [], {"status": "visible"}),
                                           ("unavailable", "exhaust", None, {"status": "covered", "view": "deck"})):
            with self.subTest(status=status), FakeGame() as game:
                game.pile_payload = {"scene": "card_pile", "pile": pile, "detail_level": "full",
                    "status": status, "screen": screen, "message": "An English explanation.", "cards": cards}
                if status == "unavailable": game.pile_payload["reason"] = "entry_not_visible"
                tools = GameTools(Client(game.directory))
                await tools.get_observation()
                result = await tools.inspect_pile({"pile": pile, "detail_level": "full"})
                self.assertNotIn("error", result)
                self.assertEqual(result["cards"], cards)
                self.assertEqual(result["screen"], screen)
                if cards is None: self.assertNotIn("hover_tips", result)
                else: self.assertEqual(result["hover_tips"], [])
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")

    async def test_malformed_payloads_fail_closed(self):
        from mcp_server import GameTools
        changes = [{"scene": "combat"}, {"pile": "discard"}, {"detail_level": "full"}, {"status": "unknown"},
                   {"screen": {}}, {"screen": {"status": "covered", "view": "deck"}}, {"cards": None},
                   {"cards": []}, {"message": None}, {"status": "empty"},
                   {"status": "unavailable", "reason": "entry_not_visible"}]
        for changeset in changes:
            with self.subTest(changes=changeset), FakeGame() as game:
                game.pile_payload = {**opened(), **changeset}
                tools = GameTools(Client(game.directory))
                await tools.get_observation()
                self.assertEqual((await tools.inspect_pile({"pile": "draw"}))["error"]["code"], "transport_error")
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
        for change in ({"id": "deck:0"}, {"id": "pile:00"}, {"energy_cost": 1}, {"name": None},
                       {"description": None}, {"hover_tips": [{"title": 1, "description": "x"}]}):
            with self.subTest(card=change), FakeGame() as game:
                game.pile_payload = opened(level="full")
                game.pile_payload["cards"][0].update(change)
                tools = GameTools(Client(game.directory))
                self.assertEqual((await tools.inspect_pile({"pile": "draw", "detail_level": "full"}))["error"]["code"],
                                 "transport_error")

    async def test_errors_timeouts_and_cancellation_never_retry_or_close(self):
        from mcp_server import GameTools
        for timeout in (False, True):
            with self.subTest(timeout=timeout), FakeGame() as game:
                tools = GameTools(Client(game.directory, timeout=.1))
                await tools.get_observation()
                if timeout: game.drop_pile_response = True
                else: game.pile_error = True
                result = await tools.inspect_pile({"pile": "draw"})
                self.assertEqual(result["error"]["code"], "timeout" if timeout else "illegal_action")
                self.assertNotIn("/private", json.dumps(result))
                self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
                self.assertEqual([op["operation"] for op in game.operations], ["get_state", "inspect_pile"])
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            game.observation_started.clear()
            game.release_observation.clear()
            scopes = []

            async def invoke():
                with anyio.CancelScope() as scope:
                    scopes.append(scope)
                    await tools.inspect_pile({"pile": "draw"})

            async with anyio.create_task_group() as group:
                group.start_soon(invoke)
                self.assertTrue(await anyio.to_thread.run_sync(game.observation_started.wait, 2))
                scopes[0].cancel()
                game.release_observation.set()
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")
            self.assertEqual([op["operation"] for op in game.operations], ["get_state", "inspect_pile"])


class PileProjectionTests(unittest.TestCase):
    def test_strict_projection_and_shared_tips_do_not_leak_raw_metadata(self):
        from pile_details import pile_details
        raw = opened(level="full")
        second = copy.deepcopy(raw["cards"][0])
        second["id"] = "pile:7"
        raw["cards"].append(second)
        raw.update(snapshot_id="control", hand=[{"secret": 1}], available_actions=["end_turn"], sort={"secret": 1})
        raw["cards"][0]["secret"] = 1
        raw["cards"][0]["hover_tips"][0]["secret"] = 1
        raw["screen"]["secret"] = 1
        before = copy.deepcopy(raw)
        result = player_result({"ok": True, "state": pile_details(raw, "draw", "full")})
        self.assertEqual(set(result), {"scene", "pile", "status", "screen", "detail_level", "message", "cards", "hover_tips"})
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(result["hover_tips"][0]["card_ids"], ["pile:0", "pile:7"])
        self.assertEqual(raw, before)

    def test_invalid_status_combinations_and_duplicate_ids_are_rejected(self):
        from pile_details import pile_details
        cases = [dict(status="empty"), dict(status="unavailable", cards=[]),
                 dict(status="unavailable", cards=None, reason="unknown"),
                 dict(status="unavailable", cards=None), dict(status="empty", cards=None)]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises((ValueError, KeyError)):
                pile_details({**opened(), **changes}, "draw", "summary")
        value = opened()
        value["cards"] *= 2
        with self.assertRaises(ValueError): pile_details(value, "draw", "summary")


if __name__ == "__main__":
    unittest.main()
