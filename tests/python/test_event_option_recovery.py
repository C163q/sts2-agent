"""Verify event preflight evidence preserves existing permission only when safe."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_events import EventClient


class RejectingEventClient(EventClient):
    def __init__(self, rejection):
        super().__init__()
        self.rejection = rejection

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'choose_event_option' and arguments['option_id'] == 2147483647:
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.rejection)
        return super().call(operation, expected_state, arguments, response_options)


def rejection(**overrides):
    return {'ok': False, 'error': {'code': 'illegal_action',
        'public_message': 'No current event option matches option_id; inspect_event shows its current IDs.',
        'action_submitted': False, **overrides},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class EventOptionRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_rejection_keeps_reason_and_allows_direct_valid_choice(self):
        client = RejectingEventClient(rejection())
        tools = GameTools(client)
        await tools.inspect_event()
        result = await tools.choose_event_option({'option_id': 2147483647})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertIn('No current event option', result['error']['message'])
        result = await tools.choose_event_option({'option_id': 0})
        self.assertNotIn('error', result)
        self.assertEqual(result['transition'], {'stop_reason': 'action_completed', 'complete': True, 'events': []})
        self.assertEqual([call[0] for call in client.calls], ['inspect_event', 'choose_event_option', 'choose_event_option'])
        self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'transition'})

    async def test_stale_unknown_submitted_or_contradictory_rejections_revoke_permission(self):
        variants = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); variants.append(missing)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            contradictory = rejection(); contradictory['execution'][field] = True; variants.append(contradictory)
        for reply in variants:
            with self.subTest(reply=reply):
                client = RejectingEventClient(reply); tools = GameTools(client)
                await tools.get_observation()
                await tools.choose_event_option({'option_id': 2147483647})
                result = await tools.choose_event_option({'option_id': 0})
                self.assertEqual(result['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), 2)

    async def test_cold_choice_cannot_create_permission(self):
        client = RejectingEventClient(rejection()); tools = GameTools(client)
        for option_id in (2147483647, 0):
            result = await tools.choose_event_option({'option_id': option_id})
            self.assertEqual(result['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_local_invalid_arguments_preserve_permission_for_valid_choice(self):
        for arguments in ({}, {'option_id': True}, {'option_id': -1}, {'option_id': 2147483648},
                          {'option_id': 0, 'extra': True}, {'option_id': 0, 'preset': 'summary'}):
            with self.subTest(arguments=arguments):
                client = RejectingEventClient(rejection()); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.choose_event_option(arguments)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.choose_event_option({'option_id': 0}))
                self.assertEqual(len(client.calls), 2)
