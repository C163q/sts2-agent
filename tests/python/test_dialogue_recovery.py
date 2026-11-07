"""Exercise real dialogue permission handling across the native response boundary."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_ancients import AncientClient


def rejection(**overrides):
    return {'ok': False, 'error': {'code': 'illegal_action',
        'public_message': 'The dialogue is finished. Use proceed to continue.',
        'action_submitted': False, **overrides},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class DialogueClient(AncientClient):
    def __init__(self, reply, scene):
        super().__init__()
        self.reply = reply
        if scene == 'epilogue':
            self.raw.update(scene=scene, ancient=None, screen={'status': 'visible', 'view': 'epilogue'},
                epilogue={'status': 'visible', 'dialogue': {'speaker': 'The Architect', 'text': 'Welcome.'},
                          'continue': None, 'proceed': {'text': 'Continue', 'enabled': True}})
        self.raw['available_actions'] = ['proceed']

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'advance_dialogue':
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.reply)
        return super().call(operation, expected_state, arguments, response_options)


class DialogueRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_preflight_rejection_preserves_reason_and_allows_direct_proceed(self):
        for scene in ('ancient', 'epilogue'):
            with self.subTest(scene=scene):
                client = DialogueClient(rejection(), scene); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.advance_dialogue()
                self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                self.assertIn('proceed', result['error']['message'])
                result = await tools.proceed()
                self.assertNotIn('error', result)
                self.assertEqual(result['transition'], {'stop_reason': 'action_completed', 'complete': True, 'events': []})
                self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'transition'})
                self.assertEqual([c[0] for c in client.calls], ['get_state', 'advance_dialogue', 'proceed'])

    async def test_uncertain_stale_missing_or_contradictory_evidence_revokes_permission(self):
        replies = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); replies.append(missing)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            reply = rejection(); reply['execution'][field] = True; replies.append(reply)
        replies.append({'ok': False, 'error': []})
        for scene in ('ancient', 'epilogue'):
            for reply in replies:
                with self.subTest(scene=scene, reply=reply):
                    client = DialogueClient(reply, scene); tools = GameTools(client)
                    await tools.get_observation(); await tools.advance_dialogue()
                    self.assertEqual((await tools.proceed())['error']['code'], 'observation_required')
                    self.assertEqual(len(client.calls), 2)

    async def test_cold_rejected_dialogue_does_not_grant_permission(self):
        client = DialogueClient(rejection(), 'ancient'); tools = GameTools(client)
        self.assertEqual((await tools.advance_dialogue())['error']['code'], 'observation_required')
        self.assertEqual((await tools.proceed())['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_local_bad_arguments_keep_existing_permission(self):
        for arguments in ({'extra': True}, {'preset': 'summary'}, {'preset': None}):
            with self.subTest(arguments=arguments):
                client = DialogueClient(rejection(), 'ancient'); tools = GameTools(client)
                await tools.get_observation()
                self.assertEqual((await tools.advance_dialogue(arguments))['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.proceed())
                self.assertEqual(len(client.calls), 2)
