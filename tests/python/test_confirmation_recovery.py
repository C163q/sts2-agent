"""Verify Trial response preflights retain only proven unchanged permission."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_event_confirmation import ConfirmationClient


class RejectingConfirmationClient(ConfirmationClient):
    def __init__(self, reply):
        super().__init__()
        self.reply = reply

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'respond_to_confirmation' and arguments == {'option': 'confirm'}:
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.reply)
        return super().call(operation, expected_state, arguments, response_options)


def rejection(**overrides):
    return {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False,
        'public_message': 'This confirmation button is disabled. Choose an enabled option.', **overrides},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class ConfirmationRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_keeps_reason_and_allows_cancel_then_reopen(self):
        for preset in ('full', 'default'):
            with self.subTest(preset=preset):
                client = RejectingConfirmationClient(rejection()); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.respond_to_confirmation({'option': 'confirm', 'preset': preset})
                self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertIn('disabled', result['error']['message'])
                cancelled = await tools.respond_to_confirmation({'option': 'cancel'})
                self.assertEqual(cancelled['transition'], {'stop_reason': 'action_completed', 'complete': True, 'events': []})
                self.assertEqual(set(cancelled), {'scene', 'screen', 'available_actions', 'transition'})
                self.assertNotIn('error', await tools.choose_event_option({'option_id': 0}))
                self.assertEqual([c[0] for c in client.calls], ['get_state', 'respond_to_confirmation', 'respond_to_confirmation', 'choose_event_option'])

    async def test_unknown_stale_submitted_and_missing_guarantee_revoke_permission(self):
        variants = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); variants.append(missing)
        view_only = copy.deepcopy(missing); view_only['error']['ui_unchanged'] = True; variants.append(view_only)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            contradictory = rejection(); contradictory['execution'][field] = True; variants.append(contradictory)
        for reply in variants:
            with self.subTest(reply=reply):
                client = RejectingConfirmationClient(reply); tools = GameTools(client)
                await tools.get_observation()
                await tools.respond_to_confirmation({'option': 'confirm'})
                self.assertEqual((await tools.respond_to_confirmation({'option': 'cancel'}))['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), 2)

    async def test_malformed_success_revokes_permission(self):
        client = RejectingConfirmationClient({'ok': True, 'state': {'snapshot_id': 'bad', 'scene': 'event'}})
        tools = GameTools(client)
        await tools.get_observation()
        self.assertEqual((await tools.respond_to_confirmation({'option': 'confirm'}))['error']['code'], 'transport_error')
        self.assertEqual((await tools.respond_to_confirmation({'option': 'cancel'}))['error']['code'], 'observation_required')

    async def test_cold_response_cannot_create_permission(self):
        client = RejectingConfirmationClient(rejection()); tools = GameTools(client)
        for option in ('confirm', 'cancel'):
            self.assertEqual((await tools.respond_to_confirmation({'option': option}))['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_local_invalid_option_preserves_permission(self):
        for arguments in ({}, {'option': True}, {'option': 1}, {'option': None}, {'option': 'yes'},
                          {'option': ['cancel']}, {'option': 'cancel', 'extra': 1}, {'option': 'cancel', 'preset': 'summary'}):
            with self.subTest(arguments=arguments):
                client = RejectingConfirmationClient(rejection()); tools = GameTools(client)
                await tools.get_observation()
                self.assertEqual((await tools.respond_to_confirmation(arguments))['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.respond_to_confirmation({'option': 'cancel'}))
                self.assertEqual(len(client.calls), 2)
