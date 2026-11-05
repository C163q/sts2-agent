"""Claim preflights and response identities govern safe action continuation."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_inspection_errors import Client
from tests.python.test_rewards import state


class ClaimRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_preserves_permission_for_another_action(self):
        for code in ('illegal_action', 'invalid_request'):
            with self.subTest(code=code):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                client.errors['claim_reward'] = {'ok': False, 'error': {'code': code,
                    'public_message': 'That reward is no longer available. Inspect current rewards.',
                    'action_submitted': False}}
                result = await tools.claim_reward({'reward_id': 12})
                self.assertEqual(result['error']['code'], code)
                self.assertIn('reward', result['error']['message'])
                self.assertNotIn('action_submitted', result['error'])
                if code == 'illegal_action':
                    self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertNotIn('error', await tools.end_turn())
                self.assertEqual([c[0] for c in client.calls], ['get_state', 'claim_reward', 'end_turn'])

    async def test_interacted_stale_uncertain_and_contradictory_rejections_require_observation(self):
        facts = {'ui_interaction_started': True, 'action_submission_observed': False, 'state_captured': True}
        cases = [({'code': 'illegal_action'}, None, 'illegal_action'),
            ({'code': 'stale_state', 'action_submitted': False}, None, 'stale_state'),
            ({'code': 'game_error', 'action_submitted': False}, None, 'game_error'),
            ({'code': 'illegal_action'}, facts, 'illegal_action'),
            ({'code': 'illegal_action', 'action_submitted': False}, facts, 'transport_error')]
        for error, execution, expected in cases:
            with self.subTest(error=error, execution=execution):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                reply = {'ok': False, 'error': error}
                if execution is not None: reply['execution'] = execution
                client.errors['claim_reward'] = reply
                self.assertEqual((await tools.claim_reward({'reward_id': 12}))['error']['code'], expected)
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_local_errors_preserve_existing_permission_and_no_read_creates_none(self):
        client = Client(); tools = GameTools(client)
        self.assertEqual((await tools.claim_reward({'reward_id': 12}))['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])
        await tools.get_observation()
        for args in ({'reward_id': True}, {'reward_id': -1}, {'reward_id': 12, 'preset': 'summary'}):
            self.assertEqual((await tools.claim_reward(args))['error']['code'], 'invalid_request')
        self.assertNotIn('error', await tools.end_turn())

    async def test_wrong_outcome_id_is_rejected_before_permission_or_compact_projection(self):
        for preset in ('full', 'default'):
            for status in ('claimed', 'not_claimed', 'not_obtained', 'pending'):
                with self.subTest(preset=preset, status=status):
                    client = OutcomeClient(status, wrong_id=True); tools = GameTools(client)
                    await tools.get_observation()
                    result = await tools.claim_reward({'reward_id': 12, 'preset': preset})
                    self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                    self.assertIsNone(tools.snapshot_id)
                    self.assertEqual((await tools.proceed())['error']['code'], 'observation_required')

    async def test_matching_outcomes_keep_receipts_and_allow_next_action(self):
        for status in ('claimed', 'not_claimed', 'not_obtained', 'pending'):
            with self.subTest(status=status):
                client = OutcomeClient(status); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.claim_reward({'reward_id': 12, 'preset': 'full'})
                self.assertEqual(result['reward_result'], {'reward_id': 12, 'status': status})
                self.assertNotIn('rewards', result)
                self.assertIsNotNone(tools.snapshot_id)


class OutcomeClient:
    def __init__(self, status, *, wrong_id=False):
        self.status = status
        self.wrong_id = wrong_id

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        result = copy.deepcopy(state())
        if operation != 'get_state':
            result['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
            result['reward_result'] = {'reward_id': 99 if self.wrong_id else 12, 'status': self.status}
        return {'ok': True, 'state': result}
