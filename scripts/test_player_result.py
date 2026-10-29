import unittest

import roundtrip_client


class PlayerResultTests(unittest.TestCase):
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
