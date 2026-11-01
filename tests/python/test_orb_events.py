"""Validate public orb event receipts through the actual output boundary."""
import unittest

from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


TARGET = {'id': 0, 'kind': 'player', 'name': 'The Defect'}


def event(kind='orb_channeled'):
    result = {'sequence': 1, 'type': kind, 'target': TARGET}
    return {**result, **({'before': 3, 'after': 5} if kind == 'orb_slots_changed'
                        else {'orb': {'name': 'Lightning'}, 'slot_index': 0})}


def clean(value, operation='play_card'):
    return inspection_details(operation, {**observation(), 'transition': {
        'stop_reason': 'player_ready', 'complete': True, 'events': [value]}})


class OrbEventTests(unittest.TestCase):
    def test_public_orb_events_survive_compact_receipts(self):
        for kind in ('orb_channeled', 'orb_evoked', 'orb_removed', 'orb_slots_changed'):
            for operation in ('play_card', 'end_turn', 'use_potion', 'choose_event_option', 'selection_option'):
                with self.subTest(kind=kind, operation=operation):
                    self.assertEqual(player_result({'ok': True, 'state': clean(event(kind), operation)})
                                     ['transition']['events'], [event(kind)])

    def test_orb_identity_omits_unexpanded_values(self):
        raw = {**event(), 'orb': {'name': 'Lightning', 'passive': 3, 'evoke': 8,
                                'description': 'Unexpanded hover', 'internal_id': 7}}
        self.assertEqual(clean(raw)['transition']['events'], [event()])

    def test_orb_identity_and_position_are_required_and_bounded(self):
        for kind in ('orb_channeled', 'orb_evoked', 'orb_removed'):
            for patch in ({'orb': {}}, {'orb': {'name': ''}}, {'orb': {'name': None}},
                          {'slot_index': -1}, {'slot_index': 10}, {'slot_index': True},
                          {'slot_index': 1.5}, {'target': {**TARGET, 'kind': 'enemy'}},
                          {'before': 3}, {'source': None}, {'card': {'id': 1, 'name': 'Zap'}}):
                with self.subTest(kind=kind, patch=patch), self.assertRaises(ValueError):
                    clean({**event(kind), **patch})
            for missing in ('target', 'orb', 'slot_index'):
                raw = event(kind)
                del raw[missing]
                with self.subTest(kind=kind, missing=missing), self.assertRaises(ValueError):
                    clean(raw)

    def test_capacity_changes_accept_zero_and_ten_but_reject_invalid_or_no_change(self):
        for before, after in ((0, 1), (9, 10), (10, 0)):
            raw = {**event('orb_slots_changed'), 'before': before, 'after': after}
            self.assertEqual(clean(raw)['transition']['events'], [raw])
        for patch in ({'before': -1}, {'after': 11}, {'before': None}, {'after': True},
                      {'before': 5}, {'orb': {'name': 'Frost'}}, {'slot_index': 0},
                      {'target': {**TARGET, 'kind': 'enemy'}}):
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                clean({**event('orb_slots_changed'), **patch})


if __name__ == '__main__':
    unittest.main()
