"""Exercise screenshot filesystem refusals without borrowing or creating permission."""
import copy
import errno
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import anyio

from sts2_mcp.game_tools import GameTools
from tests.python.test_screenshots import CaptureClient, png_payload


class EvidencedCaptureClient(CaptureClient):
    def __init__(self):
        super().__init__()
        self.facts = {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}

    def call(self, operation, *args, **kwargs):
        reply = super().call(operation, *args, **kwargs)
        if operation == 'capture_screenshot' and self.facts is not None:
            reply['execution'] = copy.deepcopy(self.facts)
        if operation == 'end_turn':
            reply['state']['transition'] = {'stop_reason': 'player_ready', 'complete': True, 'events': []}
        return reply


class ScreenshotRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_keeps_permission_and_allows_direct_end_turn(self):
        with tempfile.TemporaryDirectory() as directory:
            client = EvidencedCaptureClient(); tools = GameTools(client, screenshot_directory=directory)
            await tools.get_observation(); await tools.capture_screenshot({'filename': 'same.png'})
            before = Path(directory, 'same.png').read_bytes()
            error = (await tools.capture_screenshot({'filename': 'same.png'}))['error']
            self.assertEqual(error['code'], 'file_exists')
            self.assertEqual(error['recovery'], 'change_filename')
            self.assertEqual(Path(directory, 'same.png').read_bytes(), before)
            self.assertEqual(tools.snapshot_id, 'fixture-1')
            self.assertNotIn('error', await tools.end_turn())
            self.assertEqual(client.calls, ['get_state', 'capture_screenshot', 'capture_screenshot', 'end_turn'])

    async def test_directory_and_unicode_filename_errors_are_specific_and_recoverable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); blocked = root / 'blocked'; blocked.write_text('not a directory')
            for destination, arguments, message, recovery in (
                    (blocked, {}, 'file', 'check_screenshot_directory'),
                    (root / 'valid', {'filename': '界' * 90 + '.png'}, 'long', 'change_filename')):
                with self.subTest(destination=destination):
                    client = EvidencedCaptureClient(); tools = GameTools(client, screenshot_directory=destination)
                    await tools.get_observation()
                    error = (await tools.capture_screenshot(arguments))['error']
                    self.assertEqual(error['code'], 'screenshot_save_failed')
                    self.assertIn(message, error['message'].lower())
                    self.assertEqual(error['recovery'], recovery)
                    self.assertEqual(tools.snapshot_id, 'fixture-1')
                    self.assertNotIn('error', await tools.end_turn())
            self.assertEqual(list(root.rglob('.capture-*')), [])

    async def test_known_os_refusals_preserve_permission_without_leaking_exception_text(self):
        for number, message in ((errno.EACCES, 'permission'), (errno.EROFS, 'read-only'), (errno.ENOSPC, 'space')):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as directory:
                client = EvidencedCaptureClient(); tools = GameTools(client, screenshot_directory=directory)
                await tools.get_observation()
                with mock.patch('sts2_mcp.screenshot_tool.os.link', side_effect=OSError(number, 'PRIVATE OS DETAIL')):
                    error = (await tools.capture_screenshot())['error']
                self.assertEqual(error['code'], 'screenshot_save_failed')
                self.assertIn(message, error['message'].lower())
                self.assertNotIn('PRIVATE', error['message'])
                self.assertEqual(tools.snapshot_id, 'fixture-1')

    async def test_overlong_configured_directory_points_to_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = GameTools(EvidencedCaptureClient(), screenshot_directory=directory)
            await tools.get_observation()
            with mock.patch.object(Path, 'mkdir', side_effect=OSError(errno.ENAMETOOLONG, 'PRIVATE')):
                error = (await tools.capture_screenshot({'filename': 'short.png'}))['error']
            self.assertEqual(error['code'], 'screenshot_save_failed')
            self.assertIn('long', error['message'].lower())
            self.assertEqual(error['recovery'], 'check_screenshot_directory')
            self.assertEqual(tools.snapshot_id, 'fixture-1')

    async def test_unknown_io_and_cleanup_failure_clear_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            tools = GameTools(EvidencedCaptureClient(), screenshot_directory=directory)
            await tools.get_observation()
            with mock.patch('sts2_mcp.screenshot_tool.os.link', side_effect=OSError(errno.EIO, 'PRIVATE')):
                error = (await tools.capture_screenshot())['error']
            self.assertEqual(error['code'], 'screenshot_save_failed')
            self.assertNotIn('PRIVATE', error['message'])
            self.assertEqual(error['outcome'], 'unknown')
            self.assertIsNone(tools.snapshot_id)
            await tools.get_observation()
            with mock.patch.object(Path, 'unlink', side_effect=PermissionError(errno.EACCES, 'PRIVATE')):
                error = (await tools.capture_screenshot({'filename': 'published.png'}))['error']
            self.assertEqual(error['code'], 'screenshot_save_failed')
            self.assertIn('temporary', error['message'].lower())
            self.assertIn('may', error['message'].lower())
            self.assertEqual(error['outcome'], 'unknown')
            self.assertTrue(Path(directory, 'published.png').is_file())
            self.assertIsNone(tools.snapshot_id)

    async def test_cold_changed_or_missing_evidence_cannot_restore_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            client = EvidencedCaptureClient(); tools = GameTools(client, screenshot_directory=directory)
            await tools.capture_screenshot({'filename': 'same.png'})
            await tools.capture_screenshot({'filename': 'same.png'})
            self.assertIsNone(tools.snapshot_id)
            await tools.get_observation(); client.token = 'changed'
            await tools.capture_screenshot({'filename': 'same.png'})
            self.assertIsNone(tools.snapshot_id)
            await tools.get_observation(); client.facts = None
            await tools.capture_screenshot({'filename': 'same.png'})
            self.assertIsNone(tools.snapshot_id)

    async def test_bad_pixels_native_failure_and_contradictory_facts_clear_permission(self):
        variants = [('bad_png', None), ('native_error', None)] + [
            (field, value) for field, value in (('ui_interaction_started', True),
                ('action_submission_observed', True), ('state_captured', False), ('state_captured', 'yes'))]
        for field, value in variants:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                client = EvidencedCaptureClient(); tools = GameTools(client, screenshot_directory=Path(directory) / 'images')
                await tools.get_observation()
                if field == 'bad_png': client.payload = {**png_payload(), 'png_base64': 'invalid'}
                elif field == 'native_error': client.error = 'screenshot_unavailable'
                else: client.facts[field] = value
                result = await tools.capture_screenshot()
                self.assertIn('error', result)
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual(list(Path(directory).iterdir()), [])
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_cancelled_local_refusal_cannot_restore_permission(self):
        started, released = threading.Event(), threading.Event()
        with tempfile.TemporaryDirectory() as directory:
            tools = GameTools(EvidencedCaptureClient(), screenshot_directory=directory)
            await tools.get_observation(); await tools.capture_screenshot({'filename': 'same.png'})
            save = tools.screenshots.save
            def delayed(state, arguments):
                started.set(); released.wait(3)
                return save(state, arguments)
            with mock.patch.object(tools.screenshots, 'save', side_effect=delayed):
                async with anyio.create_task_group() as group:
                    group.start_soon(tools.capture_screenshot, {'filename': 'same.png'})
                    await anyio.to_thread.run_sync(started.wait)
                    group.cancel_scope.cancel(); released.set()
            self.assertIsNone(tools.snapshot_id)

    async def test_disabled_direct_call_explains_configuration(self):
        client = EvidencedCaptureClient(); tools = GameTools(client)
        error = (await tools.capture_screenshot())['error']
        self.assertEqual(error['code'], 'invalid_request')
        self.assertIn('config', error['message'].lower())
        self.assertIn('restart', error['message'].lower())
        self.assertEqual(error['recovery'], 'check_configuration')
        self.assertEqual(client.calls, [])
