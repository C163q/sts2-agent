"""Chest preflights retain permission only with explicit unchanged execution evidence."""
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_inspection_errors import Client


class LootRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_allows_a_different_legal_action_without_reading(self):
        for code in ('illegal_action', 'invalid_request'):
            with self.subTest(code=code):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                client.errors['loot_treasure'] = {'ok': False, 'error': {'code': code,
                    'public_message': 'No treasure room is available on the current screen.', 'action_submitted': False}}
                result = await tools.loot_treasure()
                self.assertEqual(result['error']['code'], code)
                self.assertIn('treasure room', result['error']['message'])
                self.assertNotIn('action_submitted', result['error'])
                if code == 'illegal_action':
                    self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertNotIn('error', await tools.end_turn())
                self.assertEqual([c[0] for c in client.calls], ['get_state', 'loot_treasure', 'end_turn'])

    async def test_uncertain_stale_interacted_and_contradictory_errors_revoke_permission(self):
        clicked = {'ui_interaction_started': True, 'action_submission_observed': False, 'state_captured': True}
        not_recorded = {**clicked, 'ui_interaction_started': False}
        cases = [({'code': 'illegal_action'}, None, 'illegal_action'),
            ({'code': 'illegal_action'}, not_recorded, 'illegal_action'),
            ({'code': 'stale_state', 'action_submitted': False}, None, 'stale_state'),
            ({'code': 'timeout'}, clicked, 'timeout'),
            ({'code': 'game_error', 'action_submitted': False}, None, 'game_error'),
            ({'code': 'illegal_action'}, clicked, 'illegal_action'),
            ({'code': 'illegal_action', 'action_submitted': False}, clicked, 'transport_error')]
        for error, facts, expected in cases:
            with self.subTest(error=error, facts=facts):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                response = {'ok': False, 'error': error}
                if facts is not None: response['execution'] = facts
                client.errors['loot_treasure'] = response
                result = await tools.loot_treasure({'open_only': True})
                self.assertEqual(result['error']['code'], expected)
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_no_initial_permission_and_local_argument_errors_keep_their_scope(self):
        client = Client(); tools = GameTools(client)
        self.assertEqual((await tools.loot_treasure())['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])
        await tools.get_observation()
        for args in ({'open_only': 1}, {'open_only': None}, {'open_only': False, 'repeat': True}, {'preset': 'summary'}):
            self.assertEqual((await tools.loot_treasure(args))['error']['code'], 'invalid_request')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.end_turn())
