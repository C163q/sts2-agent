"""Exercise direct view switching and explicit unchanged rejection guarantees."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_divination import DivinationClient


class ViewClient(DivinationClient):
    def __init__(self, reply=None):
        super().__init__()
        self.reply = reply

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'set_divination_tool' and self.reply is not None:
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.reply)
        result = super().call(operation, expected_state, arguments, response_options)
        if operation == 'set_divination_tool': result['state'].pop('transition', None)
        return result


def rejection(**overrides):
    return {'ok': False, 'error': {'code': 'illegal_action', 'ui_unchanged': True,
        'public_message': 'Close the map with close_map before switching divination tools.', **overrides},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class DivinationToolViewTests(unittest.IsolatedAsyncioTestCase):
    async def test_cold_switch_returns_only_context_and_directly_authorizes_reveal(self):
        for preset in ('full', 'default'):
            with self.subTest(preset=preset):
                client = ViewClient(); tools = GameTools(client)
                result = await tools.set_divination_tool({'tool': 'small', 'preset': preset})
                self.assertEqual(result, {'scene': 'event', 'screen': {'status': 'visible', 'view': 'divination'},
                                         'available_actions': ['set_divination_tool', 'divine']})
                self.assertEqual(client.calls, [('set_divination_tool', None, {'tool': 'small'})])
                self.assertNotIn('error', await tools.divine({'x': 5, 'y': 5}))
                self.assertEqual(client.calls[-1], ('divine', 'sphere-1', {'x': 5, 'y': 5}))

    async def test_explicit_unchanged_rejection_preserves_reason_and_existing_permission(self):
        client = ViewClient(rejection()); tools = GameTools(client)
        await tools.get_observation()
        result = await tools.set_divination_tool({'tool': 'small'})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertIn('close_map', result['error']['message'])
        self.assertNotIn('error', await tools.divine({'x': 5, 'y': 5}))
        self.assertEqual([c[0] for c in client.calls], ['get_state', 'set_divination_tool', 'divine'])

    async def test_cold_rejection_never_creates_permission(self):
        client = ViewClient(rejection()); tools = GameTools(client)
        result = await tools.set_divination_tool({'tool': 'small'})
        self.assertEqual(result['error']['code'], 'illegal_action')
        self.assertEqual((await tools.divine({'x': 5, 'y': 5}))['error']['code'], 'observation_required')
        self.assertEqual(len(client.calls), 1)

    async def test_unknown_interacted_stale_and_missing_guarantee_revoke_permission(self):
        variants = [rejection(code='game_error'), rejection(code='stale_state'), rejection(ui_unchanged=False)]
        missing = rejection(); missing['error'].pop('ui_unchanged'); variants.append(missing)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            reply = rejection(); reply['execution'][field] = True; variants.append(reply)
        malformed = {'ok': True, 'state': {'snapshot_id': 'bad', 'scene': 'event'}}; variants.append(malformed)
        for reply in variants:
            with self.subTest(reply=reply):
                client = ViewClient(reply); tools = GameTools(client)
                await tools.get_observation()
                await tools.set_divination_tool({'tool': 'small'})
                self.assertEqual((await tools.divine({'x': 5, 'y': 5}))['error']['code'], 'observation_required')

    async def test_local_invalid_tool_preserves_existing_permission(self):
        for args in ({}, {'tool': 'large'}, {'tool': None}, {'tool': True}, {'tool': 'small', 'extra': 1}, {'tool': 'small', 'preset': 'summary'}):
            with self.subTest(args=args):
                client = ViewClient(); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.set_divination_tool(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.divine({'x': 5, 'y': 5}))
                self.assertEqual(len(client.calls), 2)
