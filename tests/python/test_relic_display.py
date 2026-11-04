"""Displayed relics survive unavailable hover help and preserve canonical notes."""
import unittest

from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.tool_registry import TOOLS


class RelicDisplayTests(unittest.TestCase):
    def test_visible_flags_survive_full_and_summary_filters_with_original_mapping(self):
        state = self.payload()
        state['relics'][0].update(grayed_out=False, pulsing=False)
        state['relics'][1].update(grayed_out=True, pulsing=False)
        state['relics'][2].update(grayed_out=False, pulsing=True)
        full = self.project({'preset': 'full', 'relic_indices': [2, 0, 2]}, state)
        self.assertEqual(full['relic_indices'], [0, 2])
        self.assertIs(full['relics'][0]['grayed_out'], False)
        self.assertIs(full['relics'][0]['pulsing'], False)
        self.assertIs(full['relics'][1]['pulsing'], True)
        for preset in ('default', 'summary'):
            compact = self.project({'preset': preset, 'relic_indices': [2, 1, 2]}, state)
            self.assertEqual(compact['relic_indices'], [1, 2])
            self.assertIs(compact['relics'][0]['grayed_out'], True)
            self.assertIs(compact['relics'][1]['pulsing'], True)
            self.assertNotIn('pulsing', compact['relics'][0])
            self.assertNotIn('grayed_out', compact['relics'][1])

    def test_observation_uses_same_flags_and_default_false_rule_is_scoped(self):
        from tests.python.test_output_boundaries import observation
        from sts2_mcp.output.null_fields import apply_preset
        state = observation()
        state['top_bar']['relics'][0].update(grayed_out=False, pulsing=True)
        full = decode_success('get_state', state)
        self.assertEqual(full['top_bar']['relics'][0],
                         {'name': 'Anchor', 'counter': 0, 'grayed_out': False, 'pulsing': True})
        default = apply_preset(full, 'default')
        self.assertEqual(default['top_bar']['relics'][0], {'name': 'Anchor', 'counter': 0, 'pulsing': True})
        unrelated = {'grayed_out': False, 'pulsing': False, 'enabled': False,
                     'transition': {'events': [{'relic': {'grayed_out': False, 'pulsing': False}}]},
                     'relics': [{'melted': False, 'grayed_out': False, 'pulsing': False}]}
        compact = apply_preset(unrelated, 'default')
        self.assertIs(compact['enabled'], False)
        self.assertIs(compact['grayed_out'], False)
        self.assertEqual(compact['transition'], unrelated['transition'])
        self.assertEqual(compact['relics'], [{'melted': False}])

    def test_unknown_flags_full_keeps_null_compact_omits_without_filling_old_responses(self):
        state = self.payload()
        state['relics'][0].update(grayed_out=None, pulsing=None)
        full = self.project({'preset': 'full'}, state)
        self.assertIsNone(full['relics'][0]['grayed_out'])
        self.assertIsNone(full['relics'][0]['pulsing'])
        self.assertNotIn('pulsing', full['relics'][1])
        for preset in ('default', 'summary'):
            self.assertNotIn('pulsing', self.project({'preset': preset}, state)['relics'][0])

    def test_invalid_visual_flags_rejected_even_when_filter_is_empty(self):
        for field in ('grayed_out', 'pulsing'):
            for value in (0, 1, 'true', [], {}):
                state = self.payload()
                state['relics'][0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.project({'preset': 'summary', 'relic_indices': []}, state)

    def payload(self):
        return {
            'relics': [
                {'name': 'Anchor', 'counter': None, 'melted': None, 'description': 'Gain Block.',
                 'hover_tips': [{'title': 'Block', 'description': 'Prevents damage.'}]},
                {'name': 'Pen Nib', 'counter': 0, 'melted': None, 'description': None, 'hover_tips': []},
                {'name': 'Lantern', 'counter': None, 'melted': False, 'description': None, 'hover_tips': []},
            ],
            'unavailable_hover_sources': ['relics.1', 'relics.2'],
        }

    def project(self, arguments, state=None):
        request = normalize_request(TOOLS['inspect_relics'], arguments)
        return request.project(decode_success('inspect_relics', state or self.payload(), request.native_arguments))

    def test_full_retains_displayed_data_and_missing_help_note(self):
        result = self.project({'preset': 'full'})
        self.assertEqual(result['relics'][1], {'name': 'Pen Nib', 'counter': 0, 'melted': None, 'description': None})
        self.assertEqual(result['notes']['hover_tips_unavailable']['sources'], ['relics.1', 'relics.2'])
        self.assertEqual(result['hover_tips'][0]['relic_indices'], [0])

    def test_filter_prunes_notes_by_original_position(self):
        for preset in ('full', 'default'):
            with self.subTest(preset=preset):
                result = self.project({'preset': preset, 'relic_indices': [2, 0, 2]})
                self.assertEqual(result['relic_indices'], [0, 2])
                self.assertEqual(result['notes']['hover_tips_unavailable']['sources'], ['relics.2'])
                self.assertEqual(result['hover_tips'][0]['relic_indices'], [0])
                self.assertEqual('description' in result['relics'][1], preset == 'full')
        self.assertNotIn('notes', self.project({'relic_indices': [0]}))
        self.assertNotIn('notes', self.project({'relic_indices': []}))

    def test_summary_omits_all_hover_content_and_sends_summary_level(self):
        request = normalize_request(TOOLS['inspect_relics'], {'preset': 'summary'})
        self.assertEqual(request.native_arguments, {'level': 'summary'})
        result = self.project({'preset': 'summary', 'relic_indices': [1]})
        self.assertEqual(result, {'relics': [{'name': 'Pen Nib', 'counter': 0}], 'relic_indices': [1]})

    def test_invalid_or_contradictory_hover_sources_rejected_before_filter(self):
        for sources in (['relics.3'], ['relics.01'], ['relics.0'], ['relics.1', 'relics.1'], [False]):
            state = self.payload()
            state['unavailable_hover_sources'] = sources
            with self.subTest(sources=sources), self.assertRaises((ValueError, KeyError)):
                self.project({'preset': 'summary', 'relic_indices': []}, state)

    def test_compatibility_entry_preserves_new_relic_null_and_notes(self):
        from sts2_mcp.output.player_output import player_result
        raw = {'ok': True, 'state': self.payload()}
        expected = decode_success('inspect_relics', raw['state'])
        for operation in (None, 'inspect_relics'):
            with self.subTest(operation=operation):
                self.assertEqual(player_result(raw, operation=operation), expected)

    def test_legacy_partial_relic_compatibility_fragment_stays_valid(self):
        from sts2_mcp.output.player_output import player_result
        self.assertEqual(player_result({'ok': True, 'state': {'relics': [{'name': 'Anchor', 'counter': 0}]}}),
                         {'relics': [{'name': 'Anchor', 'counter': 0}], 'hover_tips': []})

    def test_null_description_requires_missing_help_evidence(self):
        state = self.payload()
        state.pop('unavailable_hover_sources')
        with self.assertRaises(ValueError):
            self.project({'preset': 'full'}, state)


if __name__ == '__main__': unittest.main()
