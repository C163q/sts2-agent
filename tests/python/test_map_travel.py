import copy
import unittest

from sts2_mcp.output.game_output import observation_details
from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import tool_definitions
from tests.python.test_output_boundaries import observation


def map_observation():
    state = observation()
    state.update(scene='unrecognized', screen={'status': 'covered', 'view': 'map'},
                 turn=None, player=None, enemies=None, buttons=None, snapshot_id='map-token',
                 map={'status': 'visible', 'act': 1, 'current_node': 'map:1:1:2',
                      'can_travel': True, 'selectable_nodes': ['map:1:2:1', 'map:1:2:5']},
                 available_actions=['travel_to_node'])
    return state


class MapSummaryTests(unittest.TestCase):
    def test_summary_preserves_native_flight_choices_and_filters_extra_fields(self):
        state = map_observation()
        state['map']['hidden_seed'] = 'private'
        result = observation_details(state)
        self.assertEqual(result.get('map'), map_observation()['map'])

    def test_corrupt_or_hidden_summary_never_authorizes_travel(self):
        cases = [lambda s: s.pop('map'), lambda s: s.update(map=None),
                 lambda s: s['screen'].update(view='deck'),
                 lambda s: s['map'].update(act=True), lambda s: s['map'].update(act=2),
                 lambda s: s['map'].update(current_node='map:2:1:2'),
                 lambda s: s['map'].update(can_travel=False),
                 lambda s: s['map'].update(selectable_nodes=[]),
                 lambda s: s['map'].update(selectable_nodes=['map:1:02:1']),
                 lambda s: s['map'].update(selectable_nodes=['map:1:2:1'] * 2),
                 lambda s: s['map'].update(status='covered'),
                 lambda s: s['available_actions'].append('claim_reward')]
        for mutate in cases:
            with self.subTest(mutate=mutate), self.assertRaises((ValueError, KeyError, TypeError)):
                state = map_observation(); mutate(state); observation_details(state)

    def test_map_with_no_choices_is_observable_without_travel(self):
        state = map_observation()
        state['map'].update(can_travel=False, selectable_nodes=[])
        state['available_actions'] = []
        self.assertEqual(observation_details(state).get('map'), state['map'])

    def test_tool_describes_native_destructive_travel(self):
        tools = {t.name: t for t in tool_definitions()}
        self.assertIn('travel_to_node', tools)
        tool = tools['travel_to_node']
        self.assertTrue(tool.annotations.destructiveHint)
        self.assertFalse(tool.annotations.idempotentHint)
        self.assertEqual(tool.inputSchema['required'], ['node_id'])


class NavigationClient:
    def __init__(self):
        self.calls = []
        self.state = map_observation()

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.calls.append((operation, expected_state, arguments))
        state = copy.deepcopy(self.state)
        if operation == 'travel_to_node':
            state = observation()
            state.update(snapshot_id='room-token', transition={'complete': True, 'stop_reason': 'player_ready', 'events': []})
        return {'ok': True, 'state': state}


class MapTravelTests(unittest.IsolatedAsyncioTestCase):
    async def test_legal_flight_action_uses_observation_token_and_can_chain(self):
        client = NavigationClient(); tools = GameTools(client)
        self.assertTrue(callable(getattr(tools, 'travel_to_node', None)), 'Missing travel_to_node')
        self.assertEqual((await tools.travel_to_node({'node_id': 'map:1:2:5'}))['error']['code'], 'observation_required')
        await tools.get_observation()
        result = await tools.travel_to_node({'node_id': 'map:1:2:5'})
        self.assertNotIn('error', result)
        self.assertEqual(client.calls[-1], ('travel_to_node', 'map-token', {'node_id': 'map:1:2:5'}))
        self.assertEqual(tools.snapshot_id, 'room-token')

    async def test_invalid_ids_are_rejected_before_ipc(self):
        client = NavigationClient(); tools = GameTools(client)
        self.assertTrue(callable(getattr(tools, 'travel_to_node', None)), 'Missing travel_to_node')
        for arguments in (None, {}, [], {'node_id': 1}, {'node_id': True}, {'node_id': ''},
                          {'node_id': 'map:01:2:3'}, {'node_id': 'map:0:2:3'},
                          {'node_id': 'map:1:-1:3'}, {'node_id': 'map:1:2:3\n'},
                          {'node_id': 'map:1:2147483648:3'}, {'node_id': 'map:1:2:3', 'force': True}):
            await tools.get_observation()
            count = len(client.calls)
            self.assertEqual((await tools.travel_to_node(arguments))['error']['code'], 'invalid_request')
            self.assertEqual(len(client.calls), count)
            self.assertEqual(tools.snapshot_id, 'map-token')

    async def test_corrupt_map_response_revokes_permission(self):
        client = NavigationClient(); tools = GameTools(client)
        await tools.get_observation()
        client.state['map']['selectable_nodes'] = ['map:2:2:1']
        result = await tools.get_observation()
        self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
        self.assertIsNone(tools.snapshot_id)


if __name__ == '__main__':
    unittest.main()
