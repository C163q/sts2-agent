import copy
import unittest
from unittest.mock import patch

from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.roundtrip_client import player_result
from tests.python.test_output_boundaries import observation
from sts2_mcp.mcp_server import GameTools
import tests.game.verifiers.verify_end_turn as verify_end_turn


def transition():
    return {"stop_reason": "choice_required", "complete": True, "events": [
        {"sequence": 1, "type": "damage", "target": {"id": 0, "name": "Ironclad", "kind": "player"},
         "source": {"kind": "card", "name": "Wither"}, "hp_loss": 3, "blocked": 0},
    ]}


class EndTurnTests(unittest.TestCase):
    def test_verifier_rejects_nonisolated_ipc_before_constructing_client(self):
        with patch("sys.argv", ["verify_end_turn", "--ipc-dir", "/tmp/nonisolated-sts2-ipc",
                                "--scenario", "normal", "--report", "/tmp/unused-turn-report.json"]), \
                patch.object(verify_end_turn, "Client") as client:
            with self.assertRaises(SystemExit):
                verify_end_turn.main()
            client.assert_not_called()

    def test_action_keeps_events_and_filters_nested_private_fields(self):
        state = observation()
        state["transition"] = transition()
        state["transition"]["debug"] = "private"
        state["transition"]["events"][0]["target"]["hidden_power"] = "private"
        clean = inspection_details("end_turn", state)
        result = player_result({"ok": True, "state": clean})
        self.assertEqual(result["transition"], transition())
        self.assertNotIn("transition", inspection_details("get_state", state))

    def test_invalid_or_missing_transition_is_rejected(self):
        for value in [None, {}, {**transition(), "stop_reason": "invented"},
                      {**transition(), "complete": 1}, {**transition(), "events": [None]}]:
            with self.subTest(value=value), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details("end_turn", {**observation(), "transition": value})
        with self.assertRaises((ValueError, KeyError)):
            inspection_details("end_turn", observation())

    def test_event_sequence_and_kind_specific_fields_are_checked(self):
        for change in [{"sequence": 0}, {"sequence": True}, {"type": "private_rng"},
                       {"hp_loss": -1}, {"blocked": "0"}, {"source": {"kind": "rng", "name": "seed"}}]:
            state = {**observation(), "transition": transition()}
            state["transition"]["events"][0].update(change)
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details("end_turn", state)
        state = {**observation(), "transition": transition()}
        state["transition"]["events"].append(copy.deepcopy(state["transition"]["events"][0]))
        with self.assertRaises(ValueError):
            inspection_details("end_turn", state)

    def test_incomplete_and_choice_results_never_advertise_end_turn(self):
        for reason, complete in [("choice_required", True), ("timeout", False), ("interrupted", False)]:
            result = inspection_details("end_turn", {**observation(), "transition": {
                "stop_reason": reason, "complete": complete, "events": []}})
            self.assertEqual(result["available_actions"], [])

    def test_power_events_distinguish_icon_presence_from_numeric_counters(self):
        event = {"sequence": 1, "type": "power_changed", "target": {"id": 1, "kind": "enemy", "name": "Enemy"},
                 "name": "Reattach", "change": "removed", "before": None, "after": None}
        state = {**observation(), "transition": {"stop_reason": "player_ready", "complete": True, "events": [event]}}
        self.assertEqual(inspection_details("end_turn", state)["transition"]["events"], [event])
        state["transition"]["events"][0]["change"] = "secret"
        with self.assertRaises(ValueError):
            inspection_details("end_turn", state)

    def test_damage_can_keep_unreadable_hp_loss_unknown(self):
        state = {**observation(), "transition": transition()}
        state["transition"]["events"][0]["hp_loss"] = None
        self.assertIsNone(inspection_details("end_turn", state)["transition"]["events"][0]["hp_loss"])


class EndTurnSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_choice_and_timeout_keep_events_without_preparing_another_action(self):
        class Client:
            def call(self, operation, expected_state=None, arguments=None, response_options=None):
                return {"ok": True, "state": observation() if operation == "get_state" else state}

        for reason, complete in [("choice_required", True), ("timeout", False)]:
            state = {**observation(), "transition": {**transition(), "stop_reason": reason, "complete": complete}}
            tools = GameTools(Client())
            await tools.get_observation()
            result = await tools.end_turn()
            self.assertEqual(result["transition"], state["transition"])
            self.assertEqual(result["available_actions"], [])
            self.assertEqual((await tools.end_turn())["error"]["code"], "observation_required")


if __name__ == "__main__":
    unittest.main()
