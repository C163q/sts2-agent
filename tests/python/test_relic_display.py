"""Displayed relics survive unavailable hover help and preserve canonical notes."""
import unittest

from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.tool_registry import TOOLS


class RelicDisplayTests(unittest.TestCase):
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
