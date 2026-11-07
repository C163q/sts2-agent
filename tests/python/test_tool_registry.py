"""Cross-tool normalization catches schema drift and conflated execution policies."""
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.output.relic_presets import relic_preset
from sts2_mcp.output.hand_presets import hand_arguments
from sts2_mcp.output.selection_presets import selection_inspection_arguments
from sts2_mcp.output.ui_presets import ui_arguments
from sts2_mcp.output.relic_presets import relic_arguments


class RegistryTests(unittest.TestCase):
    def test_registry_drives_catalog_and_normalization(self):
        from sts2_mcp.tool_registry import TOOLS
        from sts2_mcp.request_arguments import normalize_request
        catalog = {tool.name: tool for tool in tool_definitions(screenshots_enabled=True)}
        self.assertEqual(set(TOOLS), set(catalog))
        for name, spec in TOOLS.items():
            self.assertEqual(catalog[name].inputSchema, spec.input_schema)
            self.assertTrue(callable(getattr(GameTools, name)))
        request = normalize_request(TOOLS['inspect_hand'], {'preset': 'summary', 'card_ids': [2, 2, 1]})
        self.assertIsNone(request.native_arguments)
        self.assertEqual(request.output_arguments, {'preset': 'summary', 'card_ids': [2, 1]})
        self.assertEqual(normalize_request(TOOLS['get_observation'], {}).operation, 'get_state')
        self.assertNotIn('preset', TOOLS['capture_screenshot'].input_schema['properties'])

    def test_effect_permission_receipt_and_annotation_are_independent(self):
        from sts2_mcp.tool_registry import TOOLS
        from sts2_mcp.request_arguments import normalize_request
        plain = normalize_request(TOOLS['inspect_selection'], {})
        toggled = normalize_request(TOOLS['inspect_selection'], {'view_upgrades': False})
        self.assertEqual(plain.effect, 'read')
        self.assertEqual(toggled.effect, 'view')
        self.assertFalse(toggled.requires_permission)
        self.assertFalse(toggled.returns_transition)
        tool = normalize_request(TOOLS['set_divination_tool'], {'tool': 'small'})
        self.assertEqual(tool.effect, 'view')
        self.assertFalse(tool.requires_permission)
        self.assertFalse(tool.returns_transition)
        self.assertFalse(TOOLS['set_divination_tool'].records_events)
        self.assertFalse(TOOLS['set_divination_tool'].annotations['destructiveHint'])
        shot = normalize_request(TOOLS['capture_screenshot'], {})
        self.assertEqual(shot.effect, 'file')
        self.assertFalse(shot.refreshes_permission)

    def test_optional_filters_accept_null_and_keep_empty_distinct(self):
        for parse, field in [(hand_arguments, 'card_ids'), (selection_inspection_arguments, 'card_ids'),
                             (ui_arguments, 'sources'), (relic_arguments, 'relic_indices')]:
            with self.subTest(parser=parse.__name__):
                self.assertEqual(parse({field: None}), parse({}))
                self.assertEqual(parse({field: []})[field], [])

    def test_relic_help_uses_original_positions_after_compaction(self):
        payload = {'relics': [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}],
                   'hover_tips': [{'title': 'Block', 'description': 'Help', 'relic_indices': [0, 2]}]}
        result = relic_preset(payload, 'full', [2, 2, 9])
        self.assertEqual(result['relic_indices'], [2])
        self.assertEqual(result['hover_tips'][0]['relic_indices'], [2])
        self.assertEqual(result['errors'], [{'code': 'relic_indices_out_of_range', 'relic_indices': [9]}])
        self.assertEqual(payload['hover_tips'][0]['relic_indices'], [0, 2])

    def test_all_tools_reject_unknown_invalid_presets_and_scalar_type_confusion(self):
        import json
        import copy
        from sts2_mcp.tool_registry import TOOLS
        from sts2_mcp.request_arguments import normalize_request
        from tests.python.test_tool_contracts import DATA, ADDED_TOOL_ARGUMENTS
        cases = json.loads((DATA / 'cases.json').read_text())
        good = {case['tool']: case['arguments'] for case in cases
                if case['arguments'].get('preset') == 'full' and not case.get('error')
                and 'unknown_field' not in case['arguments']}
        good['capture_screenshot'] = {}
        good.update(ADDED_TOOL_ARGUMENTS)
        for name, spec in TOOLS.items():
            base = good[name]
            normalize_request(spec, base)
            bad = [{**base, 'unknown_field': True}, [], False, 0, '']
            if spec.presets:
                bad += [{**base, 'preset': value} for value in [None, [], True, 'FULL', 'unknown']]
            for field, shape in spec.input_schema['properties'].items():
                if field == 'preset': continue
                kinds = shape.get('type')
                if kinds == 'integer':
                    values = [True, 1.0, None, shape.get('minimum', 0)-1]
                    if 'maximum' in shape: values.append(shape['maximum']+1)
                elif kinds == 'boolean': values = [0, 1, None, 'true']
                elif kinds == 'string': values = [None, False, [], '']
                elif 'array' in (kinds or []): values = [False, {}, '1', [None], [True]]
                else: continue
                bad += [{**copy.deepcopy(base), field: value} for value in values]
            for arguments in bad:
                with self.subTest(tool=name, arguments=arguments), self.assertRaises(ValueError):
                    normalize_request(spec, arguments)

    def test_event_recording_matches_native_recorded_actions(self):
        import re
        from pathlib import Path
        from sts2_mcp.tool_registry import SPECS
        source = (Path(__file__).resolve().parents[2] / 'src/Sts2Agent/Adapter/GameAdapter.Resources.cs').read_text()
        recorded = set(re.findall(r'"([a-z_]+)"', source.split('RecordedActions = [', 1)[1].split('];', 1)[0]))
        self.assertEqual({spec.native_operation for spec in SPECS if spec.records_events}, recorded)

    def test_empty_filters_prune_linked_help_without_changing_slot_positions(self):
        from sts2_mcp.output.filtering import linked_help, filter_indices
        self.assertEqual(filter_indices(['A', 'B', 'C'], [2, 2, 9, 0]), ([0, 2], [9]))
        self.assertEqual(filter_indices(['A'], []), ([], []))
        tips = [{'title': 'X', 'sources': ['enemies.0', 'enemies.1']}]
        self.assertEqual(linked_help(tips, 'sources', lambda path: path == 'enemies.1'),
                         [{'title': 'X', 'sources': ['enemies.1']}])
        self.assertEqual(linked_help(tips, 'sources', lambda path: False), [])
