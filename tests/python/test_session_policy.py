"""Permission matrices exercise every registered tool through its public handler."""
import asyncio
import json
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.tool_registry import TOOLS
from tests.python.test_tool_contracts import DATA, ContractReply


def requests():
    cases = json.loads((DATA / 'cases.json').read_text())
    return {case['tool']: case for case in cases if case['arguments'].get('preset') == 'full'
            and not case.get('error') and 'unknown_field' not in case['arguments']}


class SessionPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_proceed_preserves_only_proven_unsubmitted_rejections(self):
        for code, submitted, retained in [
                ('illegal_action', False, True), ('invalid_request', False, True),
                ('illegal_action', None, False), ('illegal_action', True, False),
                ('stale_state', False, False), ('timeout', False, False), ('game_error', False, False)]:
            with self.subTest(code=code, submitted=submitted):
                error = {'code': code, 'public_message': 'Close the map with close_map before proceeding.'}
                if submitted is not None:
                    error['action_submitted'] = submitted
                tools = GameTools(ContractReply({}, error)); tools.snapshot_id = 'existing'
                result = await tools.proceed({'preset': 'full'})
                self.assertEqual(tools.snapshot_id, 'existing' if retained else None)
                if retained:
                    self.assertEqual(result['error']['recovery'],
                                     'correct_request' if code == 'invalid_request' else 'choose_legal_action')
                    self.assertIn('close_map', result['error']['message'])
        client = ContractReply({}, {'code': 'illegal_action', 'action_submitted': False})
        tools = GameTools(client)
        self.assertEqual((await tools.proceed())['error']['code'], 'observation_required')
        self.assertEqual(client.calls, [])

    async def test_proceed_cannot_restore_permission_after_interaction_or_bad_response(self):
        class Interacted(ContractReply):
            def call(self, *args, **kwargs):
                result = super().call(*args, **kwargs)
                result['execution'] = {'ui_interaction_started': True,
                    'action_submission_observed': False, 'state_captured': True}
                return result

        for proof in (None, False):
            error = {'code': 'illegal_action'}
            if proof is not None: error['action_submitted'] = proof
            tools = GameTools(Interacted({}, error)); tools.snapshot_id = 'existing'
            result = await tools.proceed()
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(result['error']['code'], 'transport_error' if proof is False else 'illegal_action')
        tools = GameTools(ContractReply({})); tools.snapshot_id = 'existing'
        self.assertEqual((await tools.proceed())['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_selection_view_retains_only_explicit_unchanged_rejections(self):
        for code, unchanged, retained in [
                ('illegal_action', True, True), ('invalid_request', True, True),
                ('illegal_action', None, False), ('illegal_action', False, False),
                ('stale_state', True, False), ('game_error', True, False)]:
            with self.subTest(code=code, unchanged=unchanged):
                error = {'code': code, 'public_message': 'No card selection is open.'}
                if unchanged is not None:
                    error['ui_unchanged'] = unchanged
                tools = GameTools(ContractReply({}, error)); tools.snapshot_id = 'existing'
                result = await tools.set_selection_view({'view': 'selection'})
                self.assertEqual(tools.snapshot_id, 'existing' if retained else None)
                self.assertEqual(result['error']['recovery'], 'correct_request' if code == 'invalid_request' else (
                    'choose_legal_action' if retained else 'get_observation'))
        tools = GameTools(ContractReply({}, {'code': 'illegal_action', 'ui_unchanged': True}))
        result = await tools.set_selection_view({'view': 'selection'})
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual(result['error']['recovery'], 'get_observation')

    async def test_selection_view_interaction_cannot_claim_unchanged(self):
        class Interacted(ContractReply):
            def call(self, *args, **kwargs):
                result = super().call(*args, **kwargs)
                result['execution'] = {'ui_interaction_started': True,
                    'action_submission_observed': False, 'state_captured': True}
                return result
        for unchanged in (None, True):
            error = {'code': 'illegal_action'}
            if unchanged is not None:
                error['ui_unchanged'] = unchanged
            tools = GameTools(Interacted({}, error)); tools.snapshot_id = 'existing'
            result = await tools.set_selection_view({'view': 'selection'})
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(result['error']['code'], 'illegal_action' if unchanged is None else 'transport_error')

    async def test_selection_option_recovers_only_explicit_unsubmitted_rejections(self):
        for code, submitted, retained in [
                ('illegal_action', False, True), ('invalid_request', False, True),
                ('illegal_action', True, False), ('illegal_action', None, False),
                ('stale_state', False, False), ('game_error', False, False)]:
            with self.subTest(code=code, submitted=submitted):
                error = {'code': code, 'public_message': 'No card selection is open.'}
                if submitted is not None:
                    error['action_submitted'] = submitted
                tools = GameTools(ContractReply({}, error)); tools.snapshot_id = 'existing'
                result = await tools.selection_option({'option_id': 'confirm'})
                self.assertEqual(tools.snapshot_id, 'existing' if retained else None)
                recovery = 'choose_legal_action' if retained and code == 'illegal_action' else (
                    'correct_request' if code == 'invalid_request' else 'get_observation')
                self.assertEqual(result['error']['recovery'], recovery)
        client = ContractReply({}, {'code': 'illegal_action', 'action_submitted': False})
        tools = GameTools(client)
        self.assertEqual((await tools.selection_option({'option_id': 'confirm'}))['error']['code'], 'observation_required')
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual(client.calls, [])

    async def test_selection_option_interaction_evidence_never_retains_permission(self):
        class Interacted(ContractReply):
            def call(self, *args, **kwargs):
                result = super().call(*args, **kwargs)
                result['execution'] = {'ui_interaction_started': True,
                    'action_submission_observed': False, 'state_captured': True}
                return result

        for submitted in (None, False):
            error = {'code': 'illegal_action'}
            if submitted is not None:
                error['action_submitted'] = submitted
            tools = GameTools(Interacted({}, error)); tools.snapshot_id = 'existing'
            result = await tools.selection_option({'option_id': 'confirm'})
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(result['error']['code'], 'illegal_action' if submitted is None else 'transport_error')
            self.assertEqual(result['error']['recovery'], 'get_observation' if submitted is None else 'check_connection')

    async def test_selection_preflight_retains_only_explicit_unsubmitted_permission(self):
        for code, submitted, retained in [('illegal_action', False, True), ('illegal_action', True, False),
                                           ('illegal_action', None, False), ('stale_state', False, False),
                                           ('game_error', False, False)]:
            with self.subTest(code=code, submitted=submitted):
                error = {'code': code, 'public_message': 'No card selection is open.'}
                if submitted is not None:
                    error['action_submitted'] = submitted
                tools = GameTools(ContractReply({}, error)); tools.snapshot_id = 'existing'
                result = await tools.select_card({'card_id': 5})
                self.assertEqual(tools.snapshot_id, 'existing' if retained else None)
                self.assertEqual(result['error']['recovery'], 'choose_legal_action' if retained else 'get_observation')

    async def test_local_rejections_preserve_existing_permission_for_every_tool(self):
        for name, spec in TOOLS.items():
            with self.subTest(tool=name):
                client = ContractReply({})
                tools = GameTools(client)
                tools.snapshot_id = 'existing'
                result = await getattr(tools, name)({'unknown_field': True})
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertIn('unknown_field', result['error']['message'])
                self.assertEqual(result['error']['recovery'], 'correct_request')
                self.assertEqual(client.calls, [])
                self.assertEqual(tools.snapshot_id, 'existing')

    async def test_all_pure_reads_preserve_existing_permission_on_definite_rejection(self):
        cases = requests()
        for name, spec in TOOLS.items():
            if spec.effect != 'read': continue
            for code in ('invalid_request', 'illegal_action', 'expired_request'):
                with self.subTest(tool=name, code=code):
                    client = ContractReply({}, {'code': code})
                    tools = GameTools(client); tools.snapshot_id = 'existing'
                    result = await getattr(tools, name)(cases[name]['arguments'])
                    self.assertEqual(tools.snapshot_id, 'existing')
                    self.assertEqual(result['error']['recovery'],
                                     'correct_request' if code == 'invalid_request' else 'choose_legal_action')
                    self.assertEqual(len(client.calls), 1)
                    self.assertIsNone(client.calls[0]['expected_state'])

    async def test_first_read_rejection_never_creates_permission(self):
        for name, spec in TOOLS.items():
            if spec.effect != 'read': continue
            with self.subTest(tool=name):
                client = ContractReply({}, {'code': 'illegal_action'})
                tools = GameTools(client)
                result = await getattr(tools, name)(requests()[name]['arguments'])
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual(result['error']['recovery'], 'get_observation')

    async def test_view_changes_never_infer_unchanged_ui_from_rejection_code(self):
        cases = requests()
        variants = [(name, case['arguments']) for name, case in cases.items() if TOOLS[name].effect == 'view']
        variants.append(('inspect_selection', {'view_upgrades': False}))
        for name, arguments in variants:
            with self.subTest(tool=name):
                client = ContractReply({}, {'code': 'illegal_action', 'action_submitted': False})
                tools = GameTools(client); tools.snapshot_id = 'existing'
                result = await getattr(tools, name)(arguments)
                self.assertEqual(result['error']['code'], 'illegal_action')
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual(result['error']['recovery'], 'get_observation')

    async def test_all_tools_clear_permission_on_uncertain_or_bad_native_response(self):
        cases = requests()
        for name, case in cases.items():
            for response in [None, {'code': 'stale_state'}, {'code': 'timeout'}, {'code': 'unknown'}]:
                with self.subTest(tool=name, response=response):
                    client = ContractReply({}, response)
                    tools = GameTools(client); tools.snapshot_id = 'existing'
                    result = await getattr(tools, name)(case['arguments'])
                    self.assertIn('error', result)
                    self.assertIsNone(tools.snapshot_id)

    async def test_action_media_failure_never_claims_unsubmitted_or_preserves_permission(self):
        for submitted in (None, True, False):
            error = {'code': 'screenshot_unavailable'}
            if submitted is not None: error['action_submitted'] = submitted
            client = ContractReply({}, error)
            tools = GameTools(client); tools.snapshot_id = 'existing'
            result = await tools.divine({'x': 1, 'y': 2})
            self.assertEqual(result['error']['outcome'], 'unknown')
            self.assertEqual(result['error']['recovery'], 'get_observation')
            self.assertNotIn('no action', result['error']['message'])
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(len(client.calls), 1)

    async def test_queued_action_cannot_borrow_a_new_generation_with_identical_token(self):
        case = requests()['get_observation']
        state = json.loads((DATA / 'states.json').read_text())[case['state']]
        state['snapshot_id'] = 'same-token'
        tools = GameTools(ContractReply(state)); tools.snapshot_id = 'same-token'
        async with tools.lock:
            read = asyncio.create_task(tools.get_observation())
            await asyncio.sleep(0)
            action = asyncio.create_task(tools.end_turn())
            await asyncio.sleep(0)
        self.assertNotIn('error', await read)
        result = await action
        self.assertEqual(result['error']['code'], 'observation_required')
        self.assertEqual([call['operation'] for call in tools.client.calls], ['get_state'])

    async def test_cancelled_queued_request_revokes_permission(self):
        tools = GameTools(ContractReply({})); tools.snapshot_id = 'existing'
        async with tools.lock:
            read = asyncio.create_task(tools.inspect_rewards())
            await asyncio.sleep(0)
            read.cancel()
            with self.assertRaises(asyncio.CancelledError): await read
        self.assertIsNone(tools.snapshot_id)

    async def test_controller_rejection_clears_all_gameplay_permissions_without_io(self):
        class Busy:
            def acquire(self): raise BlockingIOError('private lock info')
        for name, case in requests().items():
            with self.subTest(tool=name):
                client = ContractReply({})
                tools = GameTools(client, controller=Busy()); tools.snapshot_id = 'existing'
                result = await getattr(tools, name)(case['arguments'])
                self.assertEqual(result['error']['code'], 'controller_busy')
                self.assertNotIn('private', result['error']['message'])
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual(client.calls, [])

    async def test_cancelling_queued_read_prevents_inflight_read_regrant(self):
        import threading
        started, release = threading.Event(), threading.Event()
        case = requests()['get_observation']
        state = json.loads((DATA / 'states.json').read_text())[case['state']]
        class Blocking(ContractReply):
            def call(self, *args, **kwargs):
                started.set()
                if not release.wait(3): raise TimeoutError('Test did not release request')
                return super().call(*args, **kwargs)
        tools = GameTools(Blocking(state)); tools.snapshot_id = 'existing'
        read = asyncio.create_task(tools.get_observation())
        try:
            self.assertTrue(await asyncio.to_thread(started.wait, 2))
            queued = asyncio.create_task(tools.inspect_rewards())
            await asyncio.sleep(0)
            queued.cancel()
            with self.assertRaises(asyncio.CancelledError): await queued
        finally:
            release.set()
            await read
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual([call['operation'] for call in tools.client.calls], ['get_state'])


class FileMediaErrorTests(unittest.TestCase):
    def test_nonraw_file_action_media_error_reports_unknown_outcome(self):
        import contextlib
        import io
        from unittest.mock import patch
        from sts2_mcp import roundtrip_client
        output = io.StringIO()
        raw = {'ok': False, 'error': {'code': 'screenshot_unavailable',
                                    'action_submitted': True, 'message': '/private/diagnostic'}}
        with patch('sys.argv', ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', 'divine', '--x', '1', '--y', '2']), \
                patch.object(roundtrip_client.Client, 'call', return_value=raw), contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit): roundtrip_client.main()
        error = json.loads(output.getvalue())['error']
        self.assertEqual(error['outcome'], 'unknown')
        self.assertEqual(error['recovery'], 'get_state')
        self.assertNotIn('private', error['message'])
        self.assertNotIn('action_submitted', error)

    def test_file_upgrade_view_media_error_uses_dynamic_effect_without_claiming_natural_trigger(self):
        import contextlib
        import io
        from unittest.mock import patch
        from sts2_mcp import roundtrip_client
        for flags, unknown in [([], False), (['--view-upgrades'], True), (['--no-view-upgrades'], True)]:
            with self.subTest(flags=flags):
                output = io.StringIO()
                raw = {'ok': False, 'error': {'code': 'screenshot_unavailable'}}
                with patch('sys.argv', ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', 'inspect_selection', *flags]), \
                        patch.object(roundtrip_client.Client, 'call', return_value=raw), contextlib.redirect_stdout(output):
                    with self.assertRaises(SystemExit): roundtrip_client.main()
                error = json.loads(output.getvalue())['error']
                self.assertEqual(error.get('outcome'), 'unknown' if unknown else None)
                self.assertEqual(error['recovery'], 'get_state' if unknown else 'check_game_window')
