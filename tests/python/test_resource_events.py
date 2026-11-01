"""Validate visible player resource events through public action results."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_action_observations import Client
from tests.python.test_output_boundaries import observation


def resource(kind, before, after, sequence=1):
    return {'sequence': sequence, 'type': kind,
            'target': {'id': 0, 'kind': 'player', 'name': 'The Ironclad'}, 'before': before, 'after': after}


class ResourceEventTests(unittest.TestCase):
    def test_first_star_counter_reveal_preserves_unknown_previous_value(self):
        event = resource('stars_changed', None, 1)
        clean = inspection_details('play_card', {**observation(), 'transition': {
            'stop_reason': 'player_ready', 'complete': True, 'events': [event]}})
        self.assertEqual(player_result({'ok': True, 'state': clean})['transition']['events'], [event])

    def test_combat_resources_pass_through_compact_action_receipts(self):
        events = [resource('energy_changed', 3, 2), resource('stars_changed', 9, 1, 2)]
        for operation in ('play_card', 'end_turn', 'use_potion', 'selection_option', 'choose_event_option'):
            raw = copy.deepcopy(events)
            raw[0]['unrendered_intermediate'] = 0
            with self.subTest(operation=operation):
                clean = inspection_details(operation, {**observation(), 'transition': {
                    'stop_reason': 'player_ready', 'complete': True, 'events': raw}})
                self.assertEqual(player_result({'ok': True, 'state': clean})['transition']['events'], events)

    def test_combat_resources_require_valid_public_player_endpoints(self):
        for kind in ('energy_changed', 'stars_changed'):
            invalid = [{'before': None}, {'after': None}, {'before': True}, {'after': '1'},
                       {'before': -1}, {'after': -1},
                       {'target': {'id': 2, 'kind': 'enemy', 'name': 'Leaf Slime'}}]
            for change in invalid:
                if kind == 'stars_changed' and change == {'before': None}:
                    continue
                with self.subTest(kind=kind, change=change), self.assertRaises(ValueError):
                    inspection_details('end_turn', {**observation(), 'transition': {
                        'stop_reason': 'player_ready', 'complete': True,
                        'events': [{**resource(kind, 3, 2), **change}]}})

    def test_gold_and_maximum_hp_retain_actual_changes_and_drop_private_fields(self):
        events = [resource('gold_changed', 99, 74), resource('max_hp_changed', 80, 82, 2),
                  resource('hp_changed', 40, 39, 3), resource('gold_changed', 74, 99, 4)]
        for operation in ('choose_event_option', 'choose_rest_option', 'choose_ancient_option',
                          'buy_item', 'claim_reward', 'selection_option', 'proceed', 'use_potion', 'end_turn'):
            data = observation()
            data['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': copy.deepcopy(events)}
            data['transition']['events'][0]['hidden_inventory'] = 'private'
            if operation == 'claim_reward':
                data['reward_result'] = {'reward_id': 0, 'status': 'claimed'}
            with self.subTest(operation=operation):
                clean = inspection_details(operation, data)
                public = player_result({'ok': True, 'state': clean})
                self.assertEqual(public['transition']['events'], events)

    def test_new_resources_require_public_integer_player_values(self):
        for kind in ('gold_changed', 'max_hp_changed'):
            for change in ({'before': None}, {'after': None}, {'before': True}, {'after': '82'},
                           {'before': -1}, {'after': -1},
                           {'target': {'id': 1, 'kind': 'enemy', 'name': 'Hidden Enemy'}}):
                data = observation()
                data['transition'] = {'stop_reason': 'action_completed', 'complete': True,
                                      'events': [{**resource(kind, 80, 82), **change}]}
                with self.subTest(kind=kind, change=change), self.assertRaises(ValueError):
                    inspection_details('choose_event_option', data)

    def test_new_resources_require_both_change_endpoints(self):
        for field in ('before', 'after', 'target'):
            event = resource('gold_changed', 99, 100)
            del event[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                inspection_details('choose_event_option', {**observation(), 'transition': {
                    'stop_reason': 'action_completed', 'complete': True, 'events': [event]}})


class ResourcePermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_resource_receipt_stays_compact_and_can_continue_without_extra_read(self):
        client = Client()
        client.reason = 'action_completed'
        events = [resource('gold_changed', 99, 74), resource('max_hp_changed', 80, 82, 2)]
        client.mutate_reply = lambda state: state['transition'].update(events=events)
        tools = GameTools(client)
        await tools.get_observation()
        first = await tools.choose_event_option({'option_id': 0})
        self.assertEqual(first['transition']['events'], events)
        self.assertEqual(set(first), {'scene', 'screen', 'available_actions', 'transition'})
        self.assertNotIn('error', await tools.end_turn())
        self.assertEqual([call[0] for call in client.calls], ['get_state', 'choose_event_option', 'end_turn'])


if __name__ == '__main__':
    unittest.main()
