import copy
import unittest

from game_output import observation_details
from game_tools import GameTools
from inspection_details import inspection_details
from mcp_catalog import tool_definitions
from player_output import player_result


def selection(status="visible"):
    visible = status == "visible"
    return {
        "type": "choose_one", "status": status, "prompt": "Choose a Card" if visible else None,
        "min_select": 1 if visible else None, "max_select": 1 if visible else None,
        "selected_ids": [] if visible else None,
        "cards": [{"id": 5, "name": "Defend", "description": "Gain 5 Block.",
                   "type": "Skill", "rarity": "basic", "visual_card_pool": "ironclad",
                   "energy_cost": "1", "star_cost": None}] if visible else None,
        "options": [{"id": "skip", "text": "Skip", "enabled": True}] if visible else [],
        "can_view_battlefield": True,
    }


def state():
    return {"snapshot_id": "fixture-1", "scene": "combat", "screen": {"status": "covered"},
            "turn": None, "player": None, "enemies": None, "top_bar": None, "buttons": None,
            "available_actions": ["select_card", "selection_option"], "selection": selection()}


class SelectionBoundaryTests(unittest.TestCase):
    def test_upgrade_preview_keeps_original_identity_and_filters_private_fields(self):
        data = state()
        data['selection']['type'] = 'hand_upgrade'
        data['selection']['selected_ids'] = [5]
        before = copy.deepcopy(data['selection']['cards'][0])
        after = {**before, 'name': 'Defend+', 'description': 'Gain 8 Block.', 'seed': 'private'}
        data['selection']['upgrade_preview'] = {'before': before, 'after': after, 'clone': 'private'}
        result = observation_details(data)['selection']
        self.assertEqual(result['upgrade_preview']['after']['description'], 'Gain 8 Block.')
        self.assertNotIn('clone', result['upgrade_preview'])
        self.assertNotIn('seed', result['upgrade_preview']['after'])
        self.assertEqual(result['upgrade_preview']['before']['id'], result['upgrade_preview']['after']['id'])
        public = player_result({'ok': True, 'state': observation_details(data)})
        self.assertIn('upgrade_preview', public['selection'])

    def test_upgrade_preview_rejects_wrong_identity_and_missing_halves(self):
        for malformed in ({'before': {'id': 5, 'name': 'Defend', 'description': 'Gain 5 Block.'}},
                          {'before': {'id': 5, 'name': 'Defend', 'description': 'Gain 5 Block.'},
                           'after': {'id': 8, 'name': 'Defend+', 'description': 'Gain 8 Block.'}}):
            data = state()
            data['selection'].update(type='hand_upgrade', selected_ids=[5], upgrade_preview=malformed)
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                observation_details(data)

    def test_upgrade_selection_requires_preview_field_but_allows_no_selected_card(self):
        data = state()
        data['selection']['type'] = 'hand_upgrade'
        with self.assertRaises(ValueError):
            observation_details(data)
        data['selection']['upgrade_preview'] = None
        self.assertIsNone(observation_details(data)['selection']['upgrade_preview'])

    def test_hidden_upgrade_preview_is_rejected(self):
        for status in ('battlefield', 'covered'):
            data = state()
            data['selection'] = selection(status)
            data['selection'].update(type='hand_upgrade', upgrade_preview=None)
            self.assertIsNone(observation_details(data)['selection']['upgrade_preview'])
            data['selection']['upgrade_preview'] = {
                'before': {'id': 5, 'name': 'Defend', 'description': 'Gain 5 Block.'},
                'after': {'id': 5, 'name': 'Defend+', 'description': 'Gain 8 Block.'}}
            with self.assertRaises(ValueError):
                observation_details(data)

    def test_notes_explain_eye_and_pending_selection(self):
        result = player_result({"ok": True, "state": state()})
        self.assertIn("eye", result.get("notes", {}).get("selection", ""))
        data = state()
        data["selection"] = selection("battlefield")
        result = player_result({"ok": True, "state": data})
        self.assertIn('view="selection"', result.get("notes", {}).get("selection", ""))

    def test_inspection_keeps_pending_selection_note_without_card_leak(self):
        raw = {"hand": [], "selection_view": "battlefield", "selection_secret": "private"}
        result = player_result({"ok": True, "state": inspection_details("inspect_hand", raw)})
        self.assertIn('view="selection"', result.get("notes", {}).get("selection", ""))
        self.assertNotIn("selection_view", result)
        self.assertNotIn("selection_secret", result)

    def test_observation_reports_choices_and_filters_nested_metadata(self):
        data = state()
        data["selection"]["cards"][0]["seed"] = "hidden"
        data["selection"]["cards"][0]["hover_tips"] = [{"title": "Block", "description": "Prevents damage"}]
        data["selection"]["options"][0]["callback"] = "private"
        result = observation_details(data)
        self.assertEqual(result.get("selection", {}).get("prompt"), "Choose a Card")
        card = result["selection"]["cards"][0]
        self.assertNotIn("seed", card)
        self.assertNotIn("hover_tips", card)
        self.assertNotIn("callback", result["selection"]["options"][0])

    def test_hidden_choices_reject_inconsistent_payload(self):
        for status in ("battlefield", "covered"):
            data = state()
            data["selection"] = selection(status)
            self.assertEqual(observation_details(data).get("selection", {}).get("cards", "missing"), None)
            data["selection"]["cards"] = selection()["cards"]
            with self.assertRaises(ValueError):
                observation_details(data)

    def test_malformed_choices_cannot_prepare_an_action(self):
        for field, value in (("cards", None), ("min_select", True), ("max_select", -1),
                             ("selected_ids", [True]), ("options", [{"id": "skip"}])):
            data = state()
            data["selection"][field] = value
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError, TypeError)):
                observation_details(data)

    def test_choice_transition_preserves_selection_actions(self):
        data = state()
        data["available_actions"].append("end_turn")
        data["transition"] = {"stop_reason": "choice_required", "complete": True, "events": []}
        result = inspection_details("end_turn", data)
        self.assertEqual(result["available_actions"], ["select_card", "selection_option"])

    def test_new_tools_expose_action_and_view_semantics(self):
        definitions = {tool.name: tool for tool in tool_definitions()}
        self.assertIn("select_card", definitions)
        self.assertTrue(definitions["select_card"].annotations.destructiveHint)
        self.assertFalse(definitions["set_selection_view"].annotations.destructiveHint)
        self.assertTrue(definitions["inspect_selection"].annotations.readOnlyHint)


class Client:
    def __init__(self):
        self.calls = []

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        result = state()
        if operation in ("select_card", "selection_option"):
            result["transition"] = {"stop_reason": "choice_required", "complete": True, "events": []}
        return {"ok": True, "state": result}


class SelectionPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_choice_consumes_observation_and_passes_card_id(self):
        client = Client()
        tools = GameTools(client)
        self.assertTrue(hasattr(tools, "select_card"), "Missing native selection action")
        first = await tools.select_card({"card_id": 5})
        self.assertEqual(first["error"]["code"], "observation_required")
        self.assertEqual(client.calls, [])
        observed = await tools.get_observation()
        self.assertIn("select_card", observed["available_actions"])
        result = await tools.select_card({"card_id": 5})
        self.assertNotIn("error", result)
        self.assertEqual(client.calls[-1], ("select_card", "fixture-1", {"card_id": 5}))
        again = await tools.selection_option({"option_id": "skip"})
        self.assertEqual(again["error"]["code"], "observation_required")

    async def test_bad_arguments_clear_permission_without_submitting_input(self):
        client = Client()
        tools = GameTools(client)
        self.assertTrue(hasattr(tools, "select_card"), "Missing native selection action")
        for arguments in ({"card_id": True}, {"card_id": -1}, {"card_id": 2, "seed": 1}, {}, None):
            await tools.get_observation()
            result = await tools.select_card(arguments)
            self.assertEqual(result["error"]["code"], "invalid_request")
            self.assertIsNone(tools.snapshot_id)
        self.assertTrue(all(call[0] == "get_state" for call in client.calls))

    async def test_view_change_clears_permission(self):
        tools = GameTools(Client())
        self.assertTrue(hasattr(tools, "set_selection_view"), "Missing explicit battlefield view")
        await tools.get_observation()
        result = await tools.set_selection_view({"view": "battlefield"})
        self.assertNotIn("error", result)
        self.assertIsNone(tools.snapshot_id)


if __name__ == "__main__":
    unittest.main()
