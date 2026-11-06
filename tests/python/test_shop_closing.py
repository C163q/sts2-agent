"""Exercise close_shop evidence and continuation through the real session."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_shop import ShopClient, state


def rejection(**patch):
    return {'ok': False, 'error': {'code': 'illegal_action',
        'message': 'The shop is already closed.',
        'public_message': 'The shop is already closed. Use open_shop to view its goods.',
        'action_submitted': False, **patch},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class ClosingClient(ShopClient):
    def __init__(self, reply):
        super().__init__()
        self.raw = state(opened=False)
        self.raw['available_actions'] = ['open_shop', 'proceed']
        self.reply = reply

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'close_shop':
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.reply)
        if operation == 'open_shop': self.raw = state(opened=True)
        return super().call(operation, expected_state, arguments, response_options)


class ShopClosingTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_rejection_allows_legal_open(self):
        for preset in ('default', 'full'):
            with self.subTest(preset=preset):
                tools = GameTools(ClosingClient(rejection()))
                await tools.get_observation()
                result = await tools.close_shop({'preset': preset})
                self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertIn('open_shop', result['error']['message'])
                self.assertEqual(tools.snapshot_id, 'shop-1')
                opened = await tools.open_shop()
                self.assertNotIn('error', opened)
                self.assertEqual(opened['transition']['stop_reason'], 'action_completed')
                self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'close_shop', 'open_shop'])

    async def test_unknown_stale_and_interacted_errors_do_not_restore_permission(self):
        missing = rejection(); missing['error'].pop('action_submitted')
        interacted = rejection(); interacted['execution']['ui_interaction_started'] = True
        submitted = rejection(); submitted['execution']['action_submission_observed'] = True
        for reply in (missing, interacted, submitted, rejection(action_submitted=True),
                      rejection(code='stale_state'), rejection(code='game_error'), rejection(code='timeout')):
            with self.subTest(reply=reply):
                tools = GameTools(ClosingClient(reply))
                await tools.get_observation()
                await tools.close_shop()
                self.assertEqual((await tools.open_shop())['error']['code'], 'observation_required')
                self.assertIsNone(tools.snapshot_id)

    async def test_initial_action_cannot_create_permission(self):
        tools = GameTools(ClosingClient(rejection()))
        self.assertEqual((await tools.close_shop())['error']['code'], 'observation_required')
        self.assertEqual((await tools.open_shop())['error']['code'], 'observation_required')
        self.assertEqual(tools.client.calls, [])

    async def test_local_invalid_arguments_keep_permission_to_open(self):
        tools = GameTools(ClosingClient(rejection()))
        await tools.get_observation()
        self.assertEqual((await tools.close_shop({'unexpected': True}))['error']['code'], 'invalid_request')
        self.assertNotIn('error', await tools.open_shop())
        self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'open_shop'])
