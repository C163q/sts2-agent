"""Verify battle boundaries without exposing hidden encounter data."""
import unittest

from inspection_details import inspection_details
from player_output import player_result
from test_output_boundaries import observation


def clean(events, operation='play_card'):
    state = {**observation(), 'transition': {'stop_reason': 'player_ready', 'complete': True, 'events': events}}
    return player_result({'ok': True, 'state': inspection_details(operation, state)})['transition']['events']


class CombatHandoffTests(unittest.TestCase):
    def test_boundary_separates_reused_card_ids_without_losing_either_combat(self):
        events = [
            {'sequence': 1, 'type': 'card_played', 'card': {'id': 0, 'name': 'Defend'}, 'autoplay': False},
            {'sequence': 2, 'type': 'combat_started'},
            {'sequence': 3, 'type': 'card_drawn', 'card': {'id': 0, 'name': 'Strike'}},
            {'sequence': 4, 'type': 'combat_started'},
            {'sequence': 5, 'type': 'card_drawn', 'card': {'id': 0, 'name': 'Bash'}},
        ]
        for operation in ('play_card', 'end_turn', 'use_potion', 'selection_option', 'choose_event_option'):
            with self.subTest(operation=operation):
                self.assertEqual(clean(events, operation), events)

    def test_boundary_does_not_forward_hidden_encounter_fields(self):
        self.assertEqual(clean([{'sequence': 1, 'type': 'combat_started', 'encounter': 'Unknown',
                                 'enemies': [{'name': 'Unseen'}], 'future': True}]),
                         [{'sequence': 1, 'type': 'combat_started'}])

    def test_boundary_rejects_gameplay_fields_from_other_event_types(self):
        for extra in ({'name': 'Unseen'}, {'target': {'id': 1, 'kind': 'enemy', 'name': 'Unseen'}},
                      {'before': 1}, {'after': 2}, {'source': None}, {'orb': {'name': 'Lightning'}}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                clean([{'sequence': 1, 'type': 'combat_started', **extra}])


if __name__ == '__main__':
    unittest.main()
