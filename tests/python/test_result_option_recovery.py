"""Keep result action permission only when native evidence proves no interaction."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_run_ending import state


def rejection(**changes):
    return {'ok': False, 'error': {
        'code': 'illegal_action', 'public_message': 'This option is not offered. Choose an enabled result option.',
        'action_submitted': False, **changes},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class ResultOptionClient:
    def __init__(self, reply):
        self.raw = state()
        self.reply = reply
        self.calls = []

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'run_result_option':
            if arguments['option_id'] == 'missing': return copy.deepcopy(self.reply)
            self.raw = state('summary')
            self.raw['snapshot_id'] = 'result-2'
            self.raw['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class ResultOptionRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_preflight_reason_and_permission_allow_direct_correction(self):
        for preset in ('full', 'default'):
            for code in ('illegal_action', 'invalid_request'):
                with self.subTest(preset=preset, code=code):
                    client = ResultOptionClient(rejection(code=code)); tools = GameTools(client)
                    await tools.get_observation()
                    result = await tools.run_result_option({'option_id': 'missing', 'preset': preset})
                    self.assertEqual(result['error']['message'], client.reply['error']['public_message'])
                    self.assertEqual(result['error']['recovery'],
                                     'choose_legal_action' if code == 'illegal_action' else 'correct_request')
                    value = await tools.run_result_option({'option_id': 'continue'})
                    self.assertEqual(value['transition'], {'stop_reason': 'action_completed', 'complete': True, 'events': []})
                    self.assertEqual(set(value), {'scene', 'screen', 'available_actions', 'transition'})
                    self.assertEqual([c[0] for c in client.calls], ['get_state', 'run_result_option', 'run_result_option'])

    async def test_uncertain_stale_missing_and_contradictory_evidence_revoke_permission(self):
        replies = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); replies.append(missing)
        for field in ('ui_interaction_started', 'action_submission_observed'):
            changed = rejection(); changed['execution'][field] = True; replies.append(changed)
        replies.append({'ok': False, 'error': []})
        for reply in replies:
            with self.subTest(reply=reply):
                client = ResultOptionClient(reply); tools = GameTools(client)
                await tools.get_observation(); await tools.run_result_option({'option_id': 'missing'})
                result = await tools.run_result_option({'option_id': 'continue'})
                self.assertEqual(result['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), 2)

    async def test_scroll_rejection_without_unchanged_guarantee_requires_observation(self):
        reply = rejection(); reply['error'].pop('action_submitted')
        reply['execution']['ui_interaction_started'] = True
        client = ResultOptionClient(reply); tools = GameTools(client)
        await tools.get_observation(); await tools.run_result_option({'option_id': 'missing'})
        self.assertEqual((await tools.run_result_option({'option_id': 'continue'}))['error']['code'], 'observation_required')

    async def test_cold_calls_do_not_grant_permission(self):
        client = ResultOptionClient(rejection()); tools = GameTools(client)
        for option in ('missing', 'continue'):
            self.assertEqual((await tools.run_result_option({'option_id': option}))['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_local_argument_errors_keep_existing_permission(self):
        for arguments in ({}, {'option_id': None}, {'option_id': 'epoch:-1'},
                          {'option_id': 'continue', 'extra': 1}, {'option_id': 'continue', 'preset': 'summary'}):
            with self.subTest(arguments=arguments):
                client = ResultOptionClient(rejection()); tools = GameTools(client)
                await tools.get_observation()
                self.assertEqual((await tools.run_result_option(arguments))['error']['code'], 'invalid_request')
                self.assertNotIn('error', await tools.run_result_option({'option_id': 'continue'}))
                self.assertEqual(len(client.calls), 2)

    async def test_bad_success_cannot_publish_permission(self):
        reply = {'ok': True, 'state': {**state('summary'), 'screen': {'status': 'visible', 'view': 'shop'},
                 'transition': {'stop_reason': 'action_completed', 'complete': True, 'events': []}}}
        client = ResultOptionClient(reply); tools = GameTools(client)
        await tools.get_observation()
        self.assertEqual((await tools.run_result_option({'option_id': 'missing'}))['error']['code'], 'transport_error')
        self.assertEqual((await tools.run_result_option({'option_id': 'continue'}))['error']['code'], 'observation_required')
