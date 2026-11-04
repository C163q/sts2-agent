"""Potion preflight failures preserve an existing permission only with explicit proof."""
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_inspection_errors import Client


class PotionRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_unsubmitted_refusal_allows_another_action(self):
        for tool in ('use_potion', 'discard_potion'):
            with self.subTest(tool=tool):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                client.errors[tool] = {'ok': False, 'error': {'code': 'illegal_action',
                    'public_message': 'The specified potion slot is empty.', 'action_submitted': False}}
                result = await getattr(tools, tool)({'potion_slot': 0})
                self.assertEqual(result['error']['message'], 'The specified potion slot is empty.')
                self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertNotIn('action_submitted', result['error'])
                self.assertNotIn('error', await tools.end_turn())
                self.assertEqual([c[0] for c in client.calls], ['get_state', tool, 'end_turn'])

    async def test_missing_or_contradictory_proof_never_restores_permission(self):
        facts = {'ui_interaction_started': True, 'action_submission_observed': False, 'state_captured': True}
        replies = [
            {'ok': False, 'error': {'code': 'illegal_action'}},
            {'ok': False, 'error': {'code': 'game_error', 'action_submitted': False}},
            {'ok': False, 'error': {'code': 'stale_state', 'action_submitted': False}},
            {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False}, 'execution': facts},
        ]
        for tool in ('use_potion', 'discard_potion'):
            for reply in replies:
                with self.subTest(tool=tool, reply=reply):
                    client = Client(); tools = GameTools(client)
                    await tools.get_observation()
                    client.errors[tool] = reply
                    self.assertIn('error', await getattr(tools, tool)({'potion_slot': 0}))
                    self.assertIsNone(tools.snapshot_id)
                    self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_no_read_never_creates_permission_and_external_change_stays_stale(self):
        for tool in ('use_potion', 'discard_potion'):
            client = Client(); tools = GameTools(client)
            client.errors[tool] = {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False}}
            self.assertEqual((await getattr(tools, tool)({'potion_slot': 0}))['error']['code'], 'observation_required')
            self.assertEqual(client.calls, [])
            await tools.get_observation()
            await getattr(tools, tool)({'potion_slot': 0})
            client.revision += 1
            self.assertEqual((await tools.end_turn())['error']['code'], 'stale_state')
            self.assertIsNone(tools.snapshot_id)

    async def test_invalid_target_explains_the_accepted_values(self):
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        result = await tools.use_potion({'potion_slot': 0, 'target_id': None})
        self.assertEqual(result['error']['code'], 'invalid_request')
        self.assertIn('target_id', result['error']['message'])
        self.assertIn('merchant', result['error']['message'])
        self.assertIn('error', await tools.use_potion({'potion_slot': 0, 'target_id': True}))
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.end_turn())
