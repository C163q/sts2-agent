"""Basic observations expose faces; dedicated inspections retain complete cards."""
import copy
import unittest
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.tool_registry import TOOLS
from sts2_mcp.output.response_pipeline import decode_success
from tests.python.test_selection import state as selection_state
from tests.python.test_run_ending import state as result_state


def output(tool, state, preset):
    request = normalize_request(TOOLS[tool], {'preset': preset})
    return request.project(decode_success(request.operation, state, request.native_arguments))


class ObservationFaceTests(unittest.TestCase):
    def test_candidates_bundles_and_all_comparison_sides_use_faces(self):
        data = selection_state()
        card = {**data['selection']['cards'][0], 'enchantment': None,
                'hover_tips': [{'title': 'Block', 'description': 'Prevents damage.'}]}
        data['selection'].update(type='hand_upgrade', selected_ids=[card['id']], cards=[card],
                                 upgrade_preview={'before': card, 'after': {**card, 'name': 'Defend+'}})
        for preset in ('full', 'default', 'summary'):
            with self.subTest(preset=preset):
                result = output('get_observation', copy.deepcopy(data), preset)['selection']
                for value in (result['cards'][0], result['upgrade_preview']['before'], result['upgrade_preview']['after']):
                    self.assertNotIn('description', value)
                    self.assertNotIn('hover_tips', value)
                    self.assertEqual(value['id'], card['id'])
                if preset == 'full': self.assertIsNone(result['cards'][0]['enchantment'])
        for kind, field, after in (('deck_upgrade', 'upgrade_previews', card),
                                   ('deck_enchant', 'enchant_previews', card),
                                   ('deck_transform', 'transform_previews', None)):
            data = selection_state()
            data['selection'].update(type=kind, selected_ids=[card['id']], cards=[], **{field: [{'before': card, 'after': after}]})
            if kind == 'deck_transform': data['selection'][field][0]['random'] = True
            if kind == 'deck_enchant': data['selection']['enchantment'] = {'title': 'Sharp', 'description': 'Extra damage.'}
            for preset in ('full', 'default', 'summary'):
                result = output('get_observation', copy.deepcopy(data), preset)['selection'][field][0]
                self.assertNotIn('description', result['before'])
                self.assertNotIn('hover_tips', result['before'])
                if after is None: self.assertIsNone(result['after'])
                else: self.assertNotIn('description', result['after'])
        data = selection_state()
        data['selection'].update(type='bundle', cards=[], bundles=[{'id': 'bundle:0', 'cards': [card]}])
        for preset in ('full', 'default', 'summary'):
            value = output('get_observation', copy.deepcopy(data), preset)['selection']['bundles'][0]['cards'][0]
            self.assertNotIn('description', value)
            self.assertNotIn('hover_tips', value)

    def test_result_observation_faces_do_not_reduce_dedicated_details(self):
        data = result_state('unlock')
        data['run_result'].update(cards=[{'id': 'card:0', 'name': 'Defend', 'type': 'Skill',
            'energy_cost': '1', 'description': 'Gain 5 Block.', 'enchantment': None,
            'hover_tips': [{'title': 'Block', 'description': 'Prevents damage.'}]}], hover_tips=[])
        for preset in ('full', 'default', 'summary'):
            card = output('get_observation', copy.deepcopy(data), preset)['run_result']['cards'][0]
            self.assertNotIn('description', card)
            self.assertNotIn('hover_tips', card)
            self.assertEqual(card['id'], 'card:0')
        for preset in ('full', 'default'):
            card = output('inspect_run_result', copy.deepcopy(data), preset)['run_result']['cards'][0]
            self.assertEqual(card['description'], 'Gain 5 Block.')
            self.assertEqual(card['hover_tips'][0]['title'], 'Block')

    def test_selection_inspection_keeps_text_and_side_specific_help(self):
        data = selection_state()
        card = {**data['selection']['cards'][0], 'hover_tips': [{'title': 'Block', 'description': 'Before.'}]}
        data['selection'].update(type='hand_upgrade', cards=[card], selected_ids=[card['id']],
            upgrade_preview={'before': card, 'after': {**card, 'description': 'Gain 8 Block.',
                              'hover_tips': [{'title': 'Block', 'description': 'After.'}]}})
        result = output('inspect_selection', data, 'full')['selection']
        self.assertIn('description', result['cards'][0])
        self.assertEqual(result['upgrade_preview']['after']['description'], 'Gain 8 Block.')
        self.assertEqual(result['upgrade_preview']['before']['hover_tips'][0]['description'], 'Before.')
        self.assertEqual(result['upgrade_preview']['after']['hover_tips'][0]['description'], 'After.')
