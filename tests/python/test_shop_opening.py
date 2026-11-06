"""Exercise open_shop rejection evidence through the real MCP session."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_shop import ShopClient


def rejection(**patch):
    return {'ok': False, 'error': {'code': 'illegal_action',
        'message': 'The shop is already open.',
        'public_message': 'The shop is already open. Use inspect_shop or close_shop.',
        'action_submitted': False, **patch},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class OpeningClient(ShopClient):
    def __init__(self, reply):
        super().__init__()
        self.reply = reply

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'open_shop':
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.reply)
        return super().call(operation, expected_state, arguments, response_options)


class ShopOpeningTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_rejection_allows_legal_close(self):
        for preset in ('default', 'full'):
            with self.subTest(preset=preset):
                tools = GameTools(OpeningClient(rejection()))
                await tools.get_observation()
                result = await tools.open_shop({'preset': preset})
                self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertIn('close_shop', result['error']['message'])
                self.assertEqual(tools.snapshot_id, 'shop-1')
                closed = await tools.close_shop()
                self.assertNotIn('error', closed)
                self.assertEqual(closed['transition']['stop_reason'], 'action_completed')
                self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'open_shop', 'close_shop'])

    async def test_unknown_stale_and_interacted_errors_do_not_restore_permission(self):
        missing = rejection(); missing['error'].pop('action_submitted')
        interacted = rejection(); interacted['execution']['ui_interaction_started'] = True
        submitted = rejection(); submitted['execution']['action_submission_observed'] = True
        for reply in (missing, interacted, submitted, rejection(action_submitted=True),
                      rejection(code='stale_state'), rejection(code='game_error'), rejection(code='timeout')):
            with self.subTest(reply=reply):
                tools = GameTools(OpeningClient(reply))
                await tools.get_observation()
                await tools.open_shop()
                result = await tools.close_shop()
                self.assertEqual(result['error']['code'], 'observation_required')
                self.assertIsNone(tools.snapshot_id)

    async def test_initial_action_cannot_create_permission(self):
        tools = GameTools(OpeningClient(rejection()))
        self.assertEqual((await tools.open_shop())['error']['code'], 'observation_required')
        self.assertEqual((await tools.close_shop())['error']['code'], 'observation_required')
        self.assertEqual(tools.client.calls, [])

    async def test_local_invalid_arguments_keep_permission_to_close(self):
        tools = GameTools(OpeningClient(rejection()))
        await tools.get_observation()
        self.assertEqual((await tools.open_shop({'unexpected': True}))['error']['code'], 'invalid_request')
        self.assertNotIn('error', await tools.close_shop())
        self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'close_shop'])
