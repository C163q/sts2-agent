"""Orb array positions and native slot numbers remain distinct through projection."""
import copy
import unittest

from tests.python.test_hp_preview import state as health_state, output


def state():
    raw = health_state()
    raw['schema_version'] = 50
    raw['player']['orb_slots'] = [None, {'slot_index': 1, 'name': 'Frost', 'passive': 2, 'evoke': None},
                                  {'slot_index': 0, 'name': 'Lightning', 'passive': 3, 'evoke': 8}]
    raw['hover_tips'] = [{'title': 'Lightning', 'description': 'Lightning help.', 'sources': ['player.orb_slots.2']}]
    return raw


class OrbLayoutTests(unittest.TestCase):
    def test_all_combat_presets_keep_native_numbers_in_visual_array_order(self):
        for tool in ('get_observation', 'inspect_combatants'):
            for preset in ('full', 'default', 'summary'):
                with self.subTest(tool=tool, preset=preset):
                    slots = output(state(), tool, preset=preset)['player']['orb_slots']
                    self.assertIsNone(slots[0])
                    self.assertEqual([slot['slot_index'] for slot in slots[1:]], [1, 0])
                    self.assertEqual([slot['name'] for slot in slots[1:]], ['Frost', 'Lightning'])

    def test_filter_uses_array_position_and_keeps_native_slot_number_and_help(self):
        result = output(state(), 'inspect_combatants', preset='full', sources=['player.orb_slots.2'])
        self.assertEqual(result['player']['orb_slots'], [state()['player']['orb_slots'][2]])
        self.assertEqual(result['source_indices'], {'player.orb_slots': [2]})
        self.assertEqual(result['hover_tips'][0]['sources'], ['player.orb_slots.2'])

    def test_bad_or_missing_numbers_are_rejected_before_empty_source_projection(self):
        for bad in (None, True, -1, 3, 1, '0'):
            for tool in ('get_observation', 'inspect_combatants'):
                raw = state()
                if bad is None:
                    raw['player']['orb_slots'][2].pop('slot_index')
                else:
                    raw['player']['orb_slots'][2]['slot_index'] = bad
                with self.subTest(tool=tool, bad=bad), self.assertRaises((ValueError, KeyError)):
                    output(raw, tool, **({'sources': []} if tool == 'inspect_combatants' else {'preset': 'actions_only'}))

    def test_legacy_native_order_without_explicit_numbers_still_decodes(self):
        raw = state(); raw['schema_version'] = 49
        slots = raw['player']['orb_slots'] = list(reversed(raw['player']['orb_slots']))
        for slot in slots:
            if slot: slot.pop('slot_index')
        raw['hover_tips'][0]['sources'] = ['player.orb_slots.0']
        expected = copy.deepcopy(slots)
        for tool in ('get_observation', 'inspect_combatants'):
            self.assertEqual(output(raw, tool, preset='full')['player']['orb_slots'], expected)


if __name__ == '__main__':
    unittest.main()
