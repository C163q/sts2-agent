import copy
import unittest

from sts2_mcp.output.game_output import observation_details
from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.output.player_output import player_result
from sts2_mcp.output.selection_details import inspect_selection_details


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
    def test_inspection_preserves_room_scene_and_complete_card_details(self):
        for scene in ('combat', 'ancient', 'event', 'rest_site', 'shop', 'rewards', 'treasure', 'unrecognized'):
            raw = {'scene': scene, 'selection': selection()}
            raw['selection']['cards'][0]['hover_tips'] = [{'title': 'Block', 'description': 'Prevents damage.'}]
            raw['selection']['cards'][0]['private'] = 'hidden'
            with self.subTest(scene=scene):
                details = inspect_selection_details(raw)
                public = player_result({'ok': True, 'state': details}, operation='inspect_selection')
                self.assertEqual(public['scene'], scene)
                self.assertEqual(public['selection']['cards'][0]['description'], 'Gain 5 Block.')
                self.assertEqual(public['hover_tips'], [{'title': 'Block', 'description': 'Prevents damage.', 'card_ids': [5]}])
                self.assertNotIn('private', str(public))

    def test_bundle_inspection_preserves_full_cards_without_changing_scene(self):
        choice = selection()
        card = {**choice['cards'][0], 'hover_tips': []}
        choice.update(type='bundle', cards=[], bundles=[{'id': 'bundle:0', 'cards': [card]}])
        public = player_result({'ok': True, 'state': inspect_selection_details(
            {'scene': 'ancient', 'selection': choice})}, operation='inspect_selection')
        self.assertEqual(public['scene'], 'ancient')
        self.assertEqual(public['selection']['bundles'][0]['cards'][0]['description'], 'Gain 5 Block.')
        self.assertEqual(public['selection']['bundles'][0]['cards'][0]['hover_tips'], [])

    def test_inspection_rejects_unknown_scene_and_hidden_selection(self):
        for scene, status in [('card_selection', 'visible'), ('unknown', 'visible'), (None, 'visible'),
                              ('ancient', 'covered'), ('combat', 'battlefield')]:
            choice = selection(status)
            if choice['cards']:
                choice['cards'][0]['hover_tips'] = []
            with self.subTest(scene=scene, status=status), self.assertRaises(ValueError):
                inspect_selection_details({'scene': scene, 'selection': choice})

    def test_upgrade_preview_keeps_original_identity_and_filters_private_fields(self):
        data = state()
        data['selection']['type'] = 'hand_upgrade'
        data['selection']['selected_ids'] = [5]
        before = copy.deepcopy(data['selection']['cards'][0])
        after = {**before, 'name': 'Defend+', 'description': 'Gain 8 Block.', 'seed': 'private'}
        data['selection']['upgrade_preview'] = {'before': before, 'after': after, 'clone': 'private'}
        result = observation_details(data)['selection']
        self.assertEqual(result['upgrade_preview']['after']['name'], 'Defend+')
        self.assertNotIn('description', result['upgrade_preview']['after'])
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
        self.assertNotIn("description", card)
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
        self.assertFalse(definitions["inspect_selection"].annotations.readOnlyHint)


class Client:
    def __init__(self):
        self.calls = []

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.calls.append((operation, expected_state, arguments))
        result = state()
        if operation in ("select_card", "selection_option"):
            result["transition"] = {"stop_reason": "choice_required", "complete": True, "events": []}
        return {"ok": True, "state": result}


class SelectionPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_selection_view_returns_only_context_actions_and_choice_status(self):
        for preset in ('default', 'full'):
            tools = GameTools(Client())
            result = await tools.set_selection_view({'view': 'selection', 'preset': preset})
            self.assertEqual(result, {'scene': 'combat', 'screen': {'status': 'covered'},
                'available_actions': ['select_card', 'selection_option'],
                'selection': {'type': 'choose_one', 'status': 'visible'}})
            self.assertEqual(tools.snapshot_id, 'fixture-1')
            self.assertNotIn('error', await tools.select_card({'card_id': 5}))

    async def test_compact_view_still_validates_full_state_and_keeps_existing_presets(self):
        class Broken(Client):
            def call(self, *args, **kwargs):
                result = super().call(*args, **kwargs)
                result['state']['selection']['selected_ids'] = 'invalid'
                return result
        tools = GameTools(Broken()); tools.snapshot_id = 'existing'
        self.assertEqual((await tools.set_selection_view({'view': 'selection'}))['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)
        tools = GameTools(Client()); tools.snapshot_id = 'existing'
        for preset in ('summary', 'actions_only'):
            self.assertEqual((await tools.set_selection_view({'view': 'selection', 'preset': preset}))['error']['code'], 'invalid_request')
            self.assertEqual(tools.snapshot_id, 'existing')

    async def test_choice_passes_card_id_and_supplies_confirmation_observation(self):
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
        self.assertNotIn("error", again)
        self.assertEqual(client.calls[-1], ("selection_option", "fixture-1", {"option_id": "skip"}))

    async def test_bad_arguments_preserve_permission_without_submitting_input(self):
        client = Client()
        tools = GameTools(client)
        self.assertTrue(hasattr(tools, "select_card"), "Missing native selection action")
        for arguments in ({"card_id": True}, {"card_id": -1}, {"card_id": 2, "seed": 1}, {}, None):
            await tools.get_observation()
            result = await tools.select_card(arguments)
            self.assertEqual(result["error"]["code"], "invalid_request")
            self.assertEqual(tools.snapshot_id, 'fixture-1')
        self.assertTrue(all(call[0] == "get_state" for call in client.calls))

    async def test_view_change_returns_current_action_state(self):
        tools = GameTools(Client())
        self.assertTrue(hasattr(tools, "set_selection_view"), "Missing explicit battlefield view")
        await tools.get_observation()
        result = await tools.set_selection_view({"view": "battlefield"})
        self.assertNotIn("error", result)
        self.assertEqual(tools.snapshot_id, "fixture-1")


if __name__ == "__main__":
    unittest.main()
