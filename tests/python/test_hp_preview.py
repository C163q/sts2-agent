"""Rendered health forecasts survive public projection and source selection."""
import copy
import unittest

from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.tool_registry import TOOLS
from tests.python.test_output_boundaries import observation


def state():
    raw = observation()
    raw['schema_version'] = 49
    raw['player'].update(hp_preview=None, powers=[], hp=70, max_hp=80, hp_display='numeric', block=0)
    for unit in raw['enemies']:
        unit.update(hp=20, max_hp=40, hp_display='numeric', block=0, powers=[],
                    hp_preview={'poison_damage': 7, 'doom_threshold': 15, 'lethal': 'doom'})
    raw['hover_tips'] = []
    return raw


def output(raw, tool, **arguments):
    request = normalize_request(TOOLS[tool], arguments)
    return request.project(decode_success(request.operation, raw, request.native_arguments))


class HealthPreviewTests(unittest.TestCase):
    def test_both_tools_keep_forecasts_in_all_combat_presets(self):
        expected = {'poison_damage': 7, 'doom_threshold': 15, 'lethal': 'doom'}
        for tool in ('get_observation', 'inspect_combatants'):
            for preset in ('full', 'default', 'summary'):
                with self.subTest(tool=tool, preset=preset):
                    result = output(state(), tool, preset=preset)
                    self.assertEqual(result['enemies'][0].get('hp_preview'), expected)

    def test_missing_or_invalid_forecasts_are_rejected_before_projection(self):
        for tool in ('get_observation', 'inspect_combatants'):
            for bad in ({}, {'poison_damage': True}, {'doom_threshold': -1}, {'lethal': 'dead'}):
                raw = state(); raw['enemies'][0]['hp_preview'] = {**raw['enemies'][0]['hp_preview'], **bad}
                if not bad: raw['enemies'][0].pop('hp_preview')
                with self.subTest(tool=tool, bad=bad), self.assertRaises((ValueError, KeyError, TypeError)):
                    output(raw, tool, **({'sources': []} if tool == 'inspect_combatants' else {'preset': 'actions_only'}))

    def test_forecast_children_are_selectable_with_original_enemy_identity(self):
        raw = state()
        result = output(raw, 'inspect_combatants', preset='summary', sources=['enemies.0.hp_preview.poison_damage'])
        self.assertEqual(result['enemies'], [{'id': raw['enemies'][0]['id'], 'name': raw['enemies'][0]['name'],
                                             'hp_preview': {'poison_damage': 7}}])
        self.assertNotIn('errors', result)

    def test_unknown_and_absent_forecasts_keep_normal_null_semantics(self):
        for preview in (None, {'poison_damage': None, 'doom_threshold': 15, 'lethal': None}):
            raw = state(); raw['enemies'][0]['hp_preview'] = copy.deepcopy(preview)
            full = output(raw, 'inspect_combatants', preset='full')
            self.assertEqual(full['enemies'][0].get('hp_preview'), preview)
            default = output(raw, 'get_observation', preset='default')
            if preview is None:
                self.assertNotIn('hp_preview', default['enemies'][0])
            else:
                self.assertEqual(default['enemies'][0]['hp_preview'], {'doom_threshold': 15})


if __name__ == '__main__':
    unittest.main()
