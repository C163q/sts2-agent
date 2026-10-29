import json
import unittest

import roundtrip_client


class PlayerResultTests(unittest.TestCase):
    def test_potion_inspection_preserves_common_tip_and_empty_slot(self):
        tip = {"title": "Potion Slot", "description": "Potions can be used during combat."}
        slots = [{"name": "Skill Potion", "description": "Choose 1 of 3 Skills.", "hover_tips": []}, None]
        result = roundtrip_client.player_result({"ok": True, "state": {
            "snapshot_id": "token", "slot_tip": tip, "potion_slots": slots,
        }})
        self.assertEqual(result, {"slot_tip": tip, "potion_slots": [
            {"name": "Skill Potion", "description": "Choose 1 of 3 Skills."}, None], "hover_tips": []})
        self.assertIn("hover_tips", slots[0])

    def test_potion_shared_tips_preserve_slot_indices_without_modifying_raw(self):
        tip = {"title": "Block", "description": "Prevents damage."}
        slots = [{"name": "Block Potion", "description": "Gain 12 Block.", "hover_tips": [tip, tip]},
                 None, {"name": "Block Potion", "description": "Gain 12 Block.", "hover_tips": [tip]}]
        result = roundtrip_client.player_result({"ok": True, "state": {"potion_slots": slots}})
        self.assertEqual(result["hover_tips"], [{**tip, "slot_indices": [0, 2]}])
        self.assertIsNone(result["potion_slots"][1])
        self.assertTrue(all("hover_tips" not in slot for slot in result["potion_slots"] if slot))
        self.assertEqual(slots[0]["hover_tips"], [tip, tip])
        self.assertNotIn("slot_indices", tip)

    def test_potion_common_tip_appears_once_for_empty_and_full_belts(self):
        tip = {"title": "Potion Slot", "description": "Potions can be used during combat."}
        for slots in [[], [None, None], [{"name": "Skill Potion", "description": "Choose.", "hover_tips": []}]]:
            with self.subTest(slots=slots):
                result = roundtrip_client.player_result({"ok": True, "state": {"slot_tip": tip, "potion_slots": slots}})
                self.assertEqual(result["slot_tip"], tip)
                self.assertEqual(result["hover_tips"], [])
                self.assertEqual(json.dumps(result).count(tip["description"]), 1)

    def test_potion_tip_same_title_with_different_text_stays_separate(self):
        slots = [{"name": "A", "description": "A", "hover_tips": [{"title": "Effect", "description": "One."}]},
                 {"name": "B", "description": "B", "hover_tips": [{"title": "Effect", "description": "Two."}]}]
        result = roundtrip_client.player_result({"ok": True, "state": {"potion_slots": slots}})
        self.assertEqual(result["hover_tips"], [
            {"title": "Effect", "description": "One.", "slot_indices": [0]},
            {"title": "Effect", "description": "Two.", "slot_indices": [1]}])

    def test_ui_inspection_preserves_shared_tips_without_gameplay_notes(self):
        tips = [{"title": "Energy", "description": "Your current <Energy>.",
                 "sources": ["player.energy", "player.max_energy"]}]
        state = {"snapshot_id": "token", "scene": "combat", "hover_tips": tips}
        self.assertEqual(roundtrip_client.player_result({"ok": True, "state": state}), {
            "scene": "combat", "hover_tips": tips,
        })
        self.assertEqual(state["snapshot_id"], "token")

    def test_empty_ui_inspection_stays_empty_without_hand_or_intent_notes(self):
        self.assertEqual(roundtrip_client.player_result({"ok": True, "state": {
            "snapshot_id": "token", "scene": "combat", "hover_tips": [],
        }}), {"scene": "combat", "hover_tips": []})

    def test_hand_inspection_preserves_details_with_only_card_notes(self):
        hand = [{"id": 7, "name": "Strike", "description": "Deal 6 damage.", "hover_tips": []}]
        result = roundtrip_client.player_result({"ok": True, "state": {
            "snapshot_id": "token", "hand": hand,
        }})
        self.assertIn("hand", result)
        self.assertEqual(result["hand"], [{"id": 7, "name": "Strike", "description": "Deal 6 damage."}])
        self.assertEqual(result["hover_tips"], [])
        self.assertIn("hover_tips", hand[0])
        self.assertEqual(set(result["notes"]), {"card_values"})
        self.assertNotIn("snapshot_id", result)
        self.assertNotIn("enemies", result)

    def test_hand_tips_are_shared_without_modifying_the_raw_response(self):
        tip = {"title": "Block", "description": "Until next turn, prevents damage."}
        hand = [{"id": card_id, "name": "Defend", "description": "Gain 5 Block.",
                 "hover_tips": [tip, tip]} for card_id in (9, 2, 8, 5, 4)]
        result = roundtrip_client.player_result({"ok": True, "state": {"hand": hand}})
        self.assertEqual(result["hover_tips"], [{
            "title": "Block", "description": "Until next turn, prevents damage.",
            "card_ids": [9, 2, 8, 5, 4],
        }])
        self.assertTrue(all("hover_tips" not in card for card in result["hand"]))
        self.assertTrue(all(card["hover_tips"] == [tip, tip] for card in hand))
        self.assertNotIn("card_ids", tip)

    def test_same_tip_title_with_different_descriptions_is_not_merged(self):
        hand = [
            {"id": 0, "hover_tips": [{"title": "Replay", "description": "Play twice."}]},
            {"id": 1, "hover_tips": [{"title": "Replay", "description": "Play three times."}]},
            {"id": 2, "hover_tips": [{"title": "Replay", "description": "Play twice."}]},
        ]
        result = roundtrip_client.player_result({"ok": True, "state": {"hand": hand}})
        self.assertEqual(result["hover_tips"], [
            {"title": "Replay", "description": "Play twice.", "card_ids": [0, 2]},
            {"title": "Replay", "description": "Play three times.", "card_ids": [1]},
        ])

    def test_success_preserves_gameplay_without_control_metadata(self):
        state = {
            "snapshot_id": "token", "schema_version": 3, "language": "en",
            "session": "session", "combat_generation": 4, "scene": "combat",
            "screen": {"status": "visible"}, "player": {"hand": [{"id": 0}]},
            "enemies": [{"intents": [{"category": "attack", "value": "7"}]}],
            "available_actions": ["end_turn"],
        }
        result = roundtrip_client.player_result({"id": "request", "ok": True, "state": state})
        self.assertEqual(result, {
            "scene": "combat", "screen": {"status": "visible"},
            "player": {"hand": [{"id": 0}]}, "available_actions": ["end_turn"],
            "enemies": [{"intents": [{"category": "attack", "value": "7"}]}],
            "notes": {"enemy_attack_intents": roundtrip_client.ENEMY_ATTACK_INTENT_NOTE},
        })
        self.assertEqual(state["snapshot_id"], "token")

    def test_stale_state_has_an_observation_recovery(self):
        result = roundtrip_client.player_result({"ok": False, "error": {
            "code": "stale_state", "message": "Internal transport message."}})
        self.assertEqual(result["error"]["recovery"], "get_state")
        self.assertNotIn("ok", result)

    def test_unrecognized_wire_fields_are_not_forwarded_to_player(self):
        result = roundtrip_client.player_result({"ok": True, "state": {
            "scene": "combat", "overlay": {"seed": "diagnostic"}, "debug_state": {"future": "hidden"}}})
        self.assertEqual(result, {"scene": "combat"})

    def test_timeout_explicitly_forbids_automatic_retry(self):
        result = roundtrip_client.player_result({"ok": False, "error": {
            "code": "timeout", "message": "transport timeout"}})
        self.assertEqual(result["error"]["outcome"], "unknown")
        self.assertEqual(result["error"]["recovery"], "get_state")
        self.assertIn("do not retry", result["error"]["message"].lower())

    def test_internal_errors_do_not_expose_exception_details(self):
        result = roundtrip_client.player_result({"ok": False, "error": {
            "code": "game_error", "message": "/private/path/stack trace"}})
        self.assertNotIn("/private", result["error"]["message"])
        self.assertEqual(result["error"]["outcome"], "unknown")

    def test_invalid_request_needs_corrected_arguments(self):
        result = roundtrip_client.player_result({"ok": False, "error": {
            "code": "invalid_request", "message": "bad request"}})
        self.assertEqual(result["error"]["recovery"], "correct_request")


if __name__ == "__main__":
    unittest.main()
