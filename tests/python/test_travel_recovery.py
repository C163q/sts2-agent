"""Map travel preflights preserve permission only with explicit no-interaction proof."""
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_inspection_errors import Client


class TravelRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_can_continue_without_reading_again(self):
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        client.errors['travel_to_node'] = {'ok': False, 'error': {'code': 'illegal_action',
            'public_message': 'The requested node is not selectable on the current map.', 'action_submitted': False}}
        result = await tools.travel_to_node({'node_id': 'map:1:2:0'})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertEqual(result['error']['message'], client.errors['travel_to_node']['error']['public_message'])
        self.assertNotIn('action_submitted', result['error'])
        self.assertNotIn('error', await tools.end_turn())
        self.assertEqual([c[0] for c in client.calls], ['get_state', 'travel_to_node', 'end_turn'])

    async def test_uncertain_stale_and_interacted_failures_revoke_permission(self):
        facts = {'ui_interaction_started': True, 'action_submission_observed': False, 'state_captured': True}
        cases = [({'code': 'illegal_action'}, None, 'illegal_action'),
            ({'code': 'stale_state', 'action_submitted': False}, None, 'stale_state'),
            ({'code': 'game_error', 'action_submitted': False}, None, 'game_error'),
            ({'code': 'illegal_action'}, facts, 'illegal_action'),
            ({'code': 'illegal_action', 'action_submitted': False}, facts, 'transport_error')]
        for error, execution, want in cases:
            with self.subTest(error=error, execution=execution):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                reply = {'ok': False, 'error': error}
                if execution is not None: reply['execution'] = execution
                client.errors['travel_to_node'] = reply
                result = await tools.travel_to_node({'node_id': 'map:1:2:0'})
                self.assertEqual(result['error']['code'], want)
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_no_initial_permission_and_local_errors_do_not_create_or_lose_it(self):
        client = Client(); tools = GameTools(client)
        self.assertEqual((await tools.travel_to_node({'node_id': 'map:1:2:0'}))['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])
        await tools.get_observation()
        for arguments in ({'node_id': 'map:01:2:0'}, {'node_id': 'map:1:2:0', 'force': True},
                          {'node_id': 'map:1:2:0', 'preset': 'summary'}):
            self.assertEqual((await tools.travel_to_node(arguments))['error']['code'], 'invalid_request')
        self.assertNotIn('error', await tools.end_turn())
