"""An exposed map covers its underlying room, like a deck or pile browser."""
import copy
import unittest

from sts2_mcp.output.observation_details import observation_details
from sts2_mcp.output.map_details import map_details
from tests.python.test_map_travel import map_observation
from tests.python.support.fake_game import map_payload


class MapCoverageTests(unittest.TestCase):
    def test_map_observation_covers_room_without_changing_map_content(self):
        state = map_observation()
        expected = copy.deepcopy(state['map'])
        state['screen'] = {'status': 'covered', 'view': 'map'}
        result = observation_details(state)
        self.assertEqual(result['screen'], state['screen'])
        self.assertEqual(result['map'], expected)
        self.assertEqual(result['available_actions'], state['available_actions'])

    def test_covered_map_without_readable_summary_remains_observable(self):
        state = map_observation()
        state.update(map=None, screen={'status': 'covered', 'view': 'map'}, available_actions=[])
        result = observation_details(state)
        self.assertIsNone(result['map'])
        self.assertEqual(result['screen'], state['screen'])

    def test_map_details_share_the_same_covered_context(self):
        state = map_payload()
        state['screen'] = {'status': 'covered', 'view': 'map'}
        self.assertEqual(map_details(state)['screen'], state['screen'])

    def test_visible_map_context_is_no_longer_accepted(self):
        for factory, reader in ((map_observation, observation_details), (map_payload, map_details)):
            state = factory()
            state['screen'] = {'status': 'visible', 'view': 'map'}
            with self.assertRaises(ValueError): reader(state)


class MapContinuationTests(unittest.TestCase):
    def test_only_exposed_noncombat_map_completion_continues(self):
        from sts2_mcp.game_session import can_continue
        payload = map_observation()
        payload['screen'] = {'status': 'covered', 'view': 'map'}
        payload['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
        self.assertTrue(can_continue(payload))
        for changed in ({'scene': 'combat'}, {'screen': {'status': 'covered', 'view': 'deck'}},
                        {'transition': {'stop_reason': 'timeout', 'complete': False, 'events': []}},
                        {'transition': {'stop_reason': 'action_canceled', 'complete': True, 'events': []}}):
            with self.subTest(changed=changed): self.assertFalse(can_continue({**payload, **changed}))


class MapPotionChainTests(unittest.IsolatedAsyncioTestCase):
    async def test_map_potion_discard_and_travel_do_not_require_extra_reads(self):
        from sts2_mcp.game_tools import GameTools

        class Client:
            def __init__(self):
                self.state = map_observation()
                self.state['screen']['status'] = 'covered'
                self.state['available_actions'] = ['use_potion', 'discard_potion', 'travel_to_node']
                self.calls = []
            def call(self, operation, expected_state=None, arguments=None, response_options=None):
                self.calls.append(operation)
                if operation != 'get_state':
                    if expected_state != self.state['snapshot_id']:
                        return {'ok': False, 'error': {'code': 'stale_state'}}
                    self.state['snapshot_id'] += 'x'
                    self.state['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
                    self.state.pop('potion_discard', None)
                    if operation == 'discard_potion':
                        self.state['potion_discard'] = {'slot_index': 1, 'name': 'Block Potion', 'status': 'discarded'}
                        self.state['transition']['events'] = [{'sequence': 1, 'type': 'potion_discarded',
                            'potion': {'slot_index': 1, 'name': 'Block Potion'}}]
                return {'ok': True, 'state': copy.deepcopy(self.state)}

        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        self.assertNotIn('error', await tools.use_potion({'potion_slot': 0}))
        self.assertNotIn('error', await tools.discard_potion({'potion_slot': 1}))
        self.assertNotIn('error', await tools.travel_to_node({'node_id': 'map:1:2:1'}))
        self.assertEqual(client.calls, ['get_state', 'use_potion', 'discard_potion', 'travel_to_node'])
