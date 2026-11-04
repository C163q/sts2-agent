"""Rejected reads and unsubmitted plays retain only an existing observation."""
import asyncio
import copy
import threading
import unittest

import anyio

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.player_output import player_result
from tests.python.test_action_observations import Client as ActionClient
from tests.python.test_card_play import targets


READS = ('get_observation', 'inspect_targets', 'inspect_hand', 'inspect_ui', 'inspect_combatants')
ARGUMENTS = {'inspect_targets': {'card_id': 7}}
NATIVE = {'get_observation': 'get_state'}


class Client(ActionClient):
    def __init__(self):
        super().__init__()
        self.errors = {}

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation in self.errors:
            self.calls.append((operation, expected_state, arguments))
            error = self.errors[operation]
            if isinstance(error, Exception):
                raise error
            return copy.deepcopy(error)
        if operation == 'inspect_targets':
            self.calls.append((operation, expected_state, arguments))
            return {'ok': True, 'state': {**targets(), 'snapshot_id': self.token}}
        if operation == 'inspect_ui':
            self.calls.append((operation, expected_state, arguments))
            return {'ok': True, 'state': {'snapshot_id': self.token, 'scene': 'combat',
                    'screen': {'status': 'visible'}, 'hover_tips': []}}
        return super().call(operation, expected_state, arguments)


class InspectionErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_parameter_errors_explain_fields_and_preserve_permission(self):
        cases = [
            ('get_observation', {'unknown': True}, 'preset'),
            ('get_observation', {'preset': 'bad'}, 'preset'),
            ('inspect_targets', {'card_id': True}, 'card_id'),
            ('inspect_targets', {'card_id': 7, 'potion_slot': 0}, 'exactly one'),
            ('inspect_targets', {'potion_slot': -1}, 'potion_slot'),
            ('inspect_targets', {'card_id': 7, 'target_id': 2}, 'target_id'),
            ('inspect_targets', {'card_id': 7, 'preset': 'summary'}, 'preset'),
            ('inspect_hand', {'card_ids': [True]}, 'card_ids'),
            ('inspect_ui', {'sources': False}, 'sources'),
            ('inspect_combatants', {'enemy_id': 1}, 'preset'),
        ]
        for tool, arguments, expected in cases:
            with self.subTest(tool=tool, arguments=arguments):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                result = await getattr(tools, tool)(arguments)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertIn(expected, result['error']['message'])
                self.assertEqual(result['error']['recovery'], 'correct_request')
                self.assertEqual(len(client.calls), 1)
                self.assertEqual(tools.snapshot_id, 'state-1')
                self.assertNotIn('error', await tools.end_turn())

    async def test_definite_read_rejections_preserve_permission_and_reason(self):
        for tool in READS:
            for code in ('invalid_request', 'illegal_action', 'expired_request'):
                with self.subTest(tool=tool, code=code):
                    client = Client(); tools = GameTools(client)
                    await tools.get_observation()
                    native = NATIVE.get(tool, tool)
                    client.errors[native] = {'ok': False, 'error': {
                        'code': code, 'public_message': 'No supported visible hand card has that ID.'}}
                    result = await getattr(tools, tool)(ARGUMENTS.get(tool))
                    self.assertEqual(result['error']['code'], code)
                    self.assertEqual(tools.snapshot_id, 'state-1')
                    if code == 'illegal_action':
                        self.assertEqual(result['error']['message'], 'No supported visible hand card has that ID.')
                        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
                    self.assertNotIn('error', await tools.end_turn())
                    self.assertEqual([c[0] for c in client.calls], ['get_state', native, 'end_turn'])

    async def test_first_failed_read_does_not_create_permission(self):
        for tool in READS:
            with self.subTest(tool=tool):
                client = Client(); tools = GameTools(client)
                client.errors[NATIVE.get(tool, tool)] = {'ok': False, 'error': {'code': 'illegal_action'}}
                self.assertIn('error', await getattr(tools, tool)(ARGUMENTS.get(tool)))
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), 1)

    async def test_uncertain_or_malformed_reads_still_clear_permission(self):
        errors = [OSError('private connection detail'), TimeoutError('private timeout'),
                  {'ok': True, 'state': {'snapshot_id': 'untrusted'}},
                  {'ok': False, 'error': {'code': 'illegal_action', 'public_message': 7}},
                  {'ok': False, 'error': {'code': 'illegal_action', 'message': 7}},
                  *({'ok': False, 'error': {'code': code, 'message': 'private detail'}}
                    for code in ('game_error', 'timeout', 'transport_error', 'stale_state', 'unknown'))]
        for tool in READS:
            for error in errors:
                with self.subTest(tool=tool, error=error):
                    client = Client(); tools = GameTools(client)
                    await tools.get_observation()
                    client.errors[NATIVE.get(tool, tool)] = error
                    result = await getattr(tools, tool)(ARGUMENTS.get(tool))
                    self.assertIn('error', result)
                    self.assertNotIn('private', result['error']['message'])
                    self.assertIsNone(tools.snapshot_id)

    async def test_retained_read_permission_still_rejects_external_state_changes(self):
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        client.revision += 1
        client.errors['inspect_targets'] = {'ok': False, 'error': {'code': 'illegal_action'}}
        await tools.inspect_targets({'card_id': 7})
        self.assertEqual((await tools.end_turn())['error']['code'], 'stale_state')
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual(client.calls[-1], ('end_turn', 'state-1', None))

    async def test_unsubmitted_play_keeps_permission_for_end_turn(self):
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        client.errors['play_card'] = {'ok': False, 'error': {
            'code': 'illegal_action', 'public_message': 'Not enough Energy.', 'action_submitted': False}}
        result = await tools.play_card({'card_id': 7, 'target_id': 3})
        self.assertEqual(result['error']['message'], 'Not enough Energy.')
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertNotIn('action_submitted', result['error'])
        self.assertNotIn('snapshot_id', result)
        self.assertNotIn('error', await tools.end_turn())
        self.assertEqual([c[0] for c in client.calls], ['get_state', 'play_card', 'end_turn'])
        self.assertEqual(client.calls[-1][1], 'state-1')

    async def test_only_explicit_supported_rejections_restore_action_permission(self):
        cases = [
            ('play_card', {'card_id': 7}, {'code': 'illegal_action'}),
            ('play_card', {'card_id': 7}, {'code': 'illegal_action', 'action_submitted': 0}),
            ('play_card', {'card_id': 7}, {'code': 'illegal_action', 'action_submitted': True}),
            ('play_card', {'card_id': 7}, {'code': 'game_error', 'action_submitted': False}),
            ('play_card', {'card_id': 7}, {'code': 'stale_state', 'action_submitted': False}),
            ('end_turn', None, {'code': 'illegal_action'}),
            ('use_potion', {'potion_slot': 0}, {'code': 'illegal_action'}),
        ]
        for tool, args, error in cases:
            with self.subTest(tool=tool, error=error):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                client.errors[tool] = {'ok': False, 'error': error}
                self.assertIn('error', await getattr(tools, tool)(args))
                self.assertIsNone(tools.snapshot_id)

    async def test_native_unsubmitted_parameter_rejection_keeps_existing_permission(self):
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        client.errors['play_card'] = {'ok': False, 'error': {
            'code': 'invalid_request', 'public_message': 'Invalid target ID.', 'action_submitted': False}}
        result = await tools.play_card({'card_id': 7})
        self.assertEqual(result['error'], {'code': 'invalid_request', 'message': 'Invalid target ID.',
                                         'recovery': 'correct_request'})
        self.assertNotIn('error', await tools.end_turn())
        self.assertEqual(len(client.calls), 3)

    async def test_controller_conflicts_clear_permission_without_sending_a_read(self):
        class BusyController:
            def acquire(self): raise BlockingIOError('Controller already held')

        for tool in READS:
            with self.subTest(tool=tool):
                client = Client(); tools = GameTools(client)
                await tools.get_observation()
                tools.controller = BusyController()
                result = await getattr(tools, tool)(ARGUMENTS.get(tool))
                self.assertEqual(result['error']['code'], 'controller_busy')
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual(len(client.calls), 1)

    async def test_failed_inspection_never_authorizes_an_already_queued_first_action(self):
        started, release = threading.Event(), threading.Event()

        class BlockingClient(Client):
            def call(self, operation, expected_state=None, arguments=None, response_options=None):
                if operation == 'inspect_targets':
                    started.set()
                    if not release.wait(3): raise TimeoutError('Test did not release read')
                return super().call(operation, expected_state, arguments)

        client = BlockingClient(); tools = GameTools(client)
        client.errors['inspect_targets'] = {'ok': False, 'error': {'code': 'illegal_action'}}
        read = asyncio.create_task(tools.inspect_targets({'card_id': 7}))
        self.assertTrue(await asyncio.to_thread(started.wait, 2))
        action = asyncio.create_task(tools.end_turn())
        await asyncio.sleep(0)
        release.set()
        await read
        self.assertEqual((await action)['error']['code'], 'observation_required')
        self.assertEqual(len(client.calls), 1)

    async def test_cancelled_rejected_read_does_not_restore_permission(self):
        started, release = threading.Event(), threading.Event()

        class BlockingClient(Client):
            def call(self, operation, expected_state=None, arguments=None, response_options=None):
                if operation == 'inspect_targets':
                    started.set()
                    if not release.wait(3): raise TimeoutError('Test did not release read')
                return super().call(operation, expected_state, arguments)

        client = BlockingClient(); tools = GameTools(client)
        await tools.get_observation()
        client.errors['inspect_targets'] = {'ok': False, 'error': {'code': 'illegal_action'}}
        scopes = []

        async def read():
            with anyio.CancelScope() as scope:
                scopes.append(scope)
                await tools.inspect_targets({'card_id': 7})

        async with anyio.create_task_group() as group:
            group.start_soon(read)
            self.assertTrue(await anyio.to_thread.run_sync(started.wait, 2))
            scopes[0].cancel()
            release.set()
        self.assertIsNone(tools.snapshot_id)


class ErrorOutputTests(unittest.TestCase):
    def test_native_rejection_keeps_public_reason_but_filters_metadata(self):
        result = player_result({'ok': False, 'error': {'code': 'illegal_action',
            'public_message': 'Hand details are unavailable in the current screen.',
            'action_submitted': False, 'debug': 'hidden'}})
        self.assertEqual(result['error']['message'], 'Hand details are unavailable in the current screen.')
        self.assertEqual(set(result['error']), {'code', 'message', 'recovery'})

    def test_other_native_messages_never_expose_exception_details(self):
        for code in ('illegal_action', 'invalid_request', 'game_error', 'transport_error', 'timeout', 'unknown'):
            result = player_result({'ok': False, 'error': {'code': code, 'message': '/private/stack'}})
            self.assertNotIn('/private', result['error']['message'])

    def test_unknown_execution_outcomes_ignore_public_message_too(self):
        for code in ('game_error', 'timeout', 'transport_error', 'unknown', 'stale_state'):
            result = player_result({'ok': False, 'error': {
                'code': code, 'message': '/private/stack', 'public_message': '/private/exception'}})
            self.assertNotIn('/private', result['error']['message'])
