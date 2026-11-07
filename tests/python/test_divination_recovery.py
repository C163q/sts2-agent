"""Verify safe divination refusals retain permission at the native boundary."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_divination import DivinationClient


class RejectingDivinationClient(DivinationClient):
    def __init__(self, reply):
        super().__init__()
        self.reply = reply

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'divine' and arguments == {'x': 0, 'y': 0}:
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.reply)
        return super().call(operation, expected_state, arguments, response_options)


def rejection(**overrides):
    return {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False,
        'public_message': 'This cell is already uncovered. Choose a # cell; inspect_event shows the board.', **overrides},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class DivinationRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_proven_preflight_rejection_retains_reason_and_allows_direct_reveals(self):
        for preset in ('full', 'default'):
            with self.subTest(preset=preset):
                client = RejectingDivinationClient(rejection()); tools = GameTools(client)
                await tools.inspect_event()
                result = await tools.divine({'x': 0, 'y': 0, 'preset': preset})
                self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertIn('already uncovered', result['error']['message'])
                first = await tools.divine({'x': 5, 'y': 5, 'preset': preset})
                self.assertEqual(first['transition'], {'stop_reason': 'action_completed', 'complete': True, 'events': []})
                self.assertEqual(set(first), {'scene', 'screen', 'available_actions', 'transition'})
                self.assertNotIn('error', await tools.divine({'x': 5, 'y': 6}))
                self.assertEqual([row[0] for row in client.calls], ['inspect_event', 'divine', 'divine', 'divine'])

    async def test_unknown_stale_interacted_and_missing_guarantee_revoke_permission(self):
        variants = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); variants.append(missing)
        view_only = copy.deepcopy(missing); view_only['error']['ui_unchanged'] = True; variants.append(view_only)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            contradictory = rejection(); contradictory['execution'][field] = True; variants.append(contradictory)
        for reply in variants:
            with self.subTest(reply=reply):
                client = RejectingDivinationClient(reply); tools = GameTools(client)
                await tools.get_observation()
                await tools.divine({'x': 0, 'y': 0})
                self.assertEqual((await tools.divine({'x': 5, 'y': 5}))['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), 2)

    async def test_malformed_success_revokes_permission(self):
        client = RejectingDivinationClient({'ok': True, 'state': {'snapshot_id': 'bad', 'scene': 'event'}})
        tools = GameTools(client)
        await tools.get_observation()
        self.assertEqual((await tools.divine({'x': 0, 'y': 0}))['error']['code'], 'transport_error')
        self.assertEqual((await tools.divine({'x': 5, 'y': 5}))['error']['code'], 'observation_required')

    async def test_cold_reveal_never_creates_permission(self):
        client = RejectingDivinationClient(rejection()); tools = GameTools(client)
        for x, y in ((0, 0), (5, 5)):
            self.assertEqual((await tools.divine({'x': x, 'y': y}))['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_local_invalid_coordinates_preserve_permission(self):
        for args in ({}, {'x': True, 'y': 5}, {'x': 0.0, 'y': 5}, {'x': 11, 'y': 5},
                     {'x': -1, 'y': 5}, {'x': None, 'y': 5}, {'x': 5}, {'x': 5, 'y': 5, 'extra': 1},
                     {'x': 5, 'y': 5, 'preset': 'summary'}):
            with self.subTest(args=args):
                client = RejectingDivinationClient(rejection()); tools = GameTools(client)
                await tools.get_observation()
                self.assertEqual((await tools.divine(args))['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.divine({'x': 5, 'y': 5}))
                self.assertEqual(len(client.calls), 2)
