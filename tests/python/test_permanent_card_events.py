"""Validate identity-only permanent card mutation receipts."""
import unittest

from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


def change(kind='card_stats_changed'):
    return {'sequence': 1, 'type': kind, 'card': {'id': 8, 'name': 'Genetic Algorithm'}, 'pile': 'deck'}


class PermanentCardEventTests(unittest.TestCase):
    def test_identity_events_reject_fields_that_belong_to_other_event_types(self):
        extras = [{'before': 1}, {'after': 4}, {'name': 'Block'}, {'source': None},
                  {'actor': {'id': 0, 'kind': 'player', 'name': 'The Ironclad'}}, {'change': 'modified'}]
        for kind in ('card_stats_changed', 'card_energy_cost_changed', 'card_enchantment_changed'):
            for extra in extras:
                with self.subTest(kind=kind, extra=extra), self.assertRaises(ValueError):
                    inspection_details('play_card', {**observation(), 'transition': {
                        'stop_reason': 'player_ready', 'complete': True, 'events': [{**change(kind), **extra}]}})

    def test_direct_changes_keep_only_public_identity_in_compact_receipts(self):
        for kind in ('card_stats_changed', 'card_energy_cost_changed', 'card_enchantment_changed'):
            event = change(kind)
            for operation in ('play_card', 'end_turn', 'choose_event_option', 'selection_option'):
                raw = {**event, 'variable': 'Block', 'old_base': 1, 'new_base': 4, 'description': 'Unexpanded body'}
                with self.subTest(kind=kind, operation=operation):
                    clean = inspection_details(operation, {**observation(), 'transition': {
                        'stop_reason': 'player_ready', 'complete': True, 'events': [raw]}})
                    self.assertEqual(player_result({'ok': True, 'state': clean})['transition']['events'], [event])

    def test_direct_changes_require_a_permanent_scope_and_visible_identity(self):
        for kind in ('card_stats_changed', 'card_energy_cost_changed'):
            for patch in ({'pile': 'hand'}, {'pile': None}, {'card': {'id': 8, 'name': None}},
                          {'card': {'id': 8, 'name': ''}}, {'card': {'id': True, 'name': 'Card'}}):
                with self.subTest(kind=kind, patch=patch), self.assertRaises(ValueError):
                    inspection_details('end_turn', {**observation(), 'transition': {
                        'stop_reason': 'player_ready', 'complete': True, 'events': [{**change(kind), **patch}]}})
            event = change(kind)
            del event['pile']
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                inspection_details('end_turn', {**observation(), 'transition': {
                    'stop_reason': 'player_ready', 'complete': True, 'events': [event]}})


if __name__ == '__main__':
    unittest.main()
