"""Validate public orb slots and the distinction between melted and removed relics."""
import copy
import unittest

from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation
from tests.python.test_resource_events import resource


class CapacityObservationTests(unittest.TestCase):
    def test_combatant_orb_tips_reference_only_occupied_public_slots(self):
        state = {'scene': 'combat', 'screen': {'status': 'visible'}, 'player': {'powers': [], 'orb_slots': [
            {'name': 'Lightning', 'passive': 3, 'evoke': None}, None]}, 'enemies': [],
            'hover_tips': [{'title': 'Lightning', 'description': 'Passive: deal 3 damage. Evoke: deal 8 damage.',
                            'sources': ['player.orb_slots.0']}]}
        clean = inspection_details('inspect_combatants', state)
        self.assertEqual(clean, state)
        for source in ('player.orb_slots.1', 'player.orb_slots.2', 'player.orb_slots.-1'):
            invalid = copy.deepcopy(state)
            invalid['hover_tips'][0]['sources'] = [source]
            with self.subTest(source=source), self.assertRaises(ValueError):
                inspection_details('inspect_combatants', invalid)

    def test_relic_details_preserve_visible_melting_state(self):
        relic = {'name': 'Lantern', 'counter': None, 'melted': True,
                 'description': 'Melted.', 'hover_tips': []}
        self.assertEqual(inspection_details('inspect_relics', {'relics': [relic]}), {'relics': [relic]})
        with self.assertRaises(ValueError):
            inspection_details('inspect_relics', {'relics': [{**relic, 'melted': 1}]})

    def test_orb_slots_keep_queue_order_empty_slots_and_only_public_numbers(self):
        state = observation()
        slots = [{'name': 'Lightning', 'passive': 3, 'evoke': None},
                 {'name': 'Dark', 'passive': 6, 'evoke': 12}, None,
                 {'name': 'Plasma', 'passive': None, 'evoke': None}]
        state['player']['orb_slots'] = copy.deepcopy(slots)
        state['player']['orb_slots'][0].update(hidden_evoke=8, description='Hover-only help')
        state['top_bar']['relics'][0]['melted'] = True
        result = player_result({'ok': True, 'state': state})
        self.assertEqual(result['player']['orb_slots'], slots)
        self.assertTrue(result['top_bar']['relics'][0]['melted'])

    def test_unknown_orb_area_differs_from_no_slots_and_empty_slots(self):
        for slots in (None, [], [None, None, None]):
            state = observation()
            state['player']['orb_slots'] = slots
            self.assertEqual(player_result({'ok': True, 'state': state})['player']['orb_slots'], slots)

    def test_malformed_slots_cannot_silently_become_public_observations(self):
        for slots in ([{'name': '', 'passive': 3, 'evoke': None}],
                      [{'name': 'Lightning', 'passive': True, 'evoke': None}],
                      [{'name': 'Lightning', 'passive': 3}], [None] * 11, [5]):
            state = observation()
            state['player']['orb_slots'] = slots
            with self.subTest(slots=slots), self.assertRaises(ValueError):
                inspection_details('get_state', state)

    def test_capacity_and_melting_survive_compact_action_receipts(self):
        events = [resource('max_energy_changed', 3, 4),
                  {'sequence': 2, 'type': 'relic_melted', 'relic': {'name': 'Lantern'}}]
        clean = inspection_details('end_turn', {**observation(), 'transition': {
            'stop_reason': 'player_ready', 'complete': True, 'events': events}})
        self.assertEqual(player_result({'ok': True, 'state': clean})['transition']['events'], events)

    def test_capacity_requires_public_endpoints_and_melting_requires_identity(self):
        for change in ({'before': None}, {'after': True}, {'before': -1},
                       {'target': {'id': 1, 'kind': 'enemy', 'name': 'Slime'}}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspection_details('end_turn', {**observation(), 'transition': {
                    'stop_reason': 'player_ready', 'complete': True,
                    'events': [{**resource('max_energy_changed', 3, 4), **change}]}})
        for relic in ({}, {'name': ''}, {'name': None}):
            with self.subTest(relic=relic), self.assertRaises(ValueError):
                inspection_details('end_turn', {**observation(), 'transition': {
                    'stop_reason': 'player_ready', 'complete': True,
                    'events': [{'sequence': 1, 'type': 'relic_melted', 'relic': relic}]}})


if __name__ == '__main__':
    unittest.main()
