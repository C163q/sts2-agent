"""Inspection context describes the room and the opened UI separately."""
import unittest
from tests.python.test_mcp_server import map_payload
from sts2_mcp.output.map_details import map_details, map_preset
from sts2_mcp.output.deck_details import deck_details
from sts2_mcp.output.pile_details import pile_details
from sts2_mcp.output.player_output import player_result


class InspectionContextTests(unittest.TestCase):
    def test_map_keeps_underlying_event_and_page(self):
        data = map_payload()
        data['scene'] = 'event'
        result = map_details(data)
        self.assertEqual(result['scene'], 'event')
        self.assertEqual(result['screen'], {'status': 'covered', 'view': 'map'})
        self.assertEqual(map_preset(result, 'selectable', 0)['scene'], 'event')

    def test_deck_uses_underlying_epilogue(self):
        state = {'scene': 'epilogue', 'screen': {'status': 'covered', 'view': 'deck'},
                 'view_upgrades': False,
                 'sort': {'by': 'obtained', 'descending': False}, 'deck': []}
        result = deck_details(state)
        self.assertEqual(result['scene'], 'epilogue')
        self.assertEqual(result['screen'], state['screen'])

    def test_old_page_names_are_rejected_as_scenes(self):
        state = map_payload()
        state['scene'] = 'map'
        with self.assertRaises(ValueError): map_details(state)

    def test_pile_full_help_no_longer_depends_on_scene_card_pile(self):
        state = {'scene': 'combat', 'screen': {'status': 'covered', 'view': 'discard_pile'},
            'pile': 'discard', 'status': 'opened', 'message': 'Discard pile.',
            'cards': [{'id': 'pile:0', 'name': 'Defend', 'type': 'Skill', 'rarity': 'basic',
                'visual_card_pool': 'ironclad', 'energy_cost': '1', 'star_cost': None,
                'description': 'Gain 5 Block.', 'hover_tips': [{'title': 'Block', 'description': 'Block help.'}]}]}
        payload = pile_details(state, 'discard')
        result = player_result({'ok': True, 'state': payload}, operation='inspect_pile')
        self.assertEqual(result['scene'], 'combat')
        self.assertEqual(result['hover_tips'][0]['card_ids'], ['pile:0'])
        self.assertNotIn('hover_tips', result['cards'][0])


class CombatBackgroundContextTests(unittest.TestCase):
    def test_unrecognized_but_visible_background_keeps_native_context(self):
        from sts2_mcp.output.combatant_details import combatant_details
        state = {'scene': 'unrecognized', 'screen': {'status': 'visible'},
                 'player': None, 'enemies': [], 'hover_tips': []}
        self.assertEqual(combatant_details(state), state)
