"""Inspection context describes the room and the opened UI separately."""
import unittest
from sts2_mcp.output.response_pipeline import decode_success
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

    def test_browsing_only_page_names_are_rejected_as_scenes(self):
        state = map_payload()
        state['scene'] = 'deck'
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


INSPECTIONS = {
    'inspect_hand': {'hand': []},
    'inspect_potions': {'potion_slots': [], 'slot_tip': {'title': 'Potion Slot', 'description': 'Use potions.'}},
    'inspect_relics': {'relics': []},
    'inspect_targets': {'card': {'id': 0, 'name': 'Strike'}, 'playable': True,
                        'target_type': 'any_enemy', 'requires_target': True,
                        'targets': [{'id': 1, 'kind': 'enemy', 'name': 'Slime'}], 'reason': None},
}


class ModernInspectionContextTests(unittest.TestCase):
    def test_inspections_retain_context_after_schema_increments(self):
        for version in (35, 48, 49, 50, 51):
            for operation, fields in INSPECTIONS.items():
                with self.subTest(version=version, operation=operation):
                    state = {**fields, 'schema_version': version, 'snapshot_id': 'current',
                             'scene': 'map', 'screen': {'status': 'covered', 'view': 'map'}}
                    result = decode_success(operation, state, {'card_id': 0})
                    self.assertEqual(result.get('scene'), 'map')
                    self.assertEqual(result.get('screen'), {'status': 'covered', 'view': 'map'})
                    self.assertNotIn('snapshot_id', result)

    def test_current_inspections_reject_invalid_context(self):
        for operation, fields in INSPECTIONS.items():
            for context in ({}, {'scene': 'future', 'screen': {'status': 'visible'}},
                            {'scene': 'map', 'screen': {'status': 'unknown'}}):
                with self.subTest(operation=operation, context=context):
                    with self.assertRaises(ValueError):
                        decode_success(operation, {**fields, **context, 'schema_version': 50}, {'card_id': 0})
