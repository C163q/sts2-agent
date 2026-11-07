"""Verify ancient preflight evidence preserves existing permission only when safe."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_ancients import AncientClient


class RejectingAncientClient(AncientClient):
    def __init__(self, rejection):
        super().__init__()
        self.rejection = rejection

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'choose_ancient_option' and arguments['option_id'] == 2147483647:
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.rejection)
        return super().call(operation, expected_state, arguments, response_options)


def rejection(**overrides):
    return {'ok': False, 'error': {'code': 'illegal_action',
        'public_message': 'No current ancient option matches option_id; inspect_ancient shows its current IDs.',
        'action_submitted': False, **overrides},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class AncientChoiceRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_rejection_keeps_reason_and_allows_direct_valid_choice(self):
        client = RejectingAncientClient(rejection())
        tools = GameTools(client)
        await tools.inspect_ancient()
        result = await tools.choose_ancient_option({'option_id': 2147483647})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertIn('No current ancient option', result['error']['message'])
        result = await tools.choose_ancient_option({'option_id': 0})
        self.assertNotIn('error', result)
        self.assertEqual(result['transition'], {'stop_reason': 'action_completed', 'complete': True, 'events': []})
        self.assertEqual([call[0] for call in client.calls], ['inspect_ancient', 'choose_ancient_option', 'choose_ancient_option'])
        self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'transition'})

    async def test_stale_unknown_submitted_or_contradictory_rejections_revoke_permission(self):
        variants = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); variants.append(missing)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            contradictory = rejection(); contradictory['execution'][field] = True; variants.append(contradictory)
        for reply in variants:
            with self.subTest(reply=reply):
                client = RejectingAncientClient(reply); tools = GameTools(client)
                await tools.get_observation()
                await tools.choose_ancient_option({'option_id': 2147483647})
                result = await tools.choose_ancient_option({'option_id': 0})
                self.assertEqual(result['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), 2)

    async def test_cold_choice_cannot_create_permission(self):
        client = RejectingAncientClient(rejection()); tools = GameTools(client)
        for option_id in (2147483647, 0):
            result = await tools.choose_ancient_option({'option_id': option_id})
            self.assertEqual(result['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_local_invalid_arguments_preserve_permission_for_valid_choice(self):
        for arguments in ({}, {'option_id': True}, {'option_id': -1}, {'option_id': 2147483648},
                          {'option_id': 0, 'extra': True}, {'option_id': 0, 'preset': 'summary'}):
            with self.subTest(arguments=arguments):
                client = RejectingAncientClient(rejection()); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.choose_ancient_option(arguments)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.choose_ancient_option({'option_id': 0}))
                self.assertEqual(len(client.calls), 2)
