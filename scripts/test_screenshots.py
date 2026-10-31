import base64
import copy
import json
import struct
import tempfile
import unittest
import zlib
import sys
import subprocess
from pathlib import Path

import anyio

from game_tools import GameTools
from mcp_catalog import tool_definitions
from test_card_play import combat


def png_payload():
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b'\0\xff\0\0\xff')) + chunk(b'IEND', b''))
    return {'snapshot_id': 'fixture-1', 'width': 1, 'height': 1,
            'png_base64': base64.b64encode(png).decode(), 'private': 'never expose'}


class ScreenshotConfigTests(unittest.TestCase):
    def test_default_missing_is_disabled_and_explicit_missing_fails(self):
        from mcp_config import load_config
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'missing.json'
            self.assertIsNone(load_config(default_path=missing).screenshot_directory)
            with self.assertRaises(ValueError):
                load_config(missing)

    def test_config_is_strict_and_resolves_directory_beside_file(self):
        from mcp_config import load_config
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': 'captures'}}))
            settings = load_config(path)
            self.assertEqual(settings.screenshot_directory, path.parent / 'captures')
            path.write_text('{"screenshots":{"enabled":false}}')
            self.assertIsNone(load_config(path).screenshot_directory)
            self.assertEqual(settings.screenshot_directory, path.parent / 'captures')
            for value in [[], {'screenshot': {}}, {'screenshots': []}, {'screenshots': {'enabled': 1}},
                          {'screenshots': {'enabled': True}}, {'screenshots': {'enabled': True, 'directory': ''}},
                          {'screenshots': {'enabled': True, 'directory': None}},
                          {'screenshots': {'enabled': False, 'typo': True}}]:
                path.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaises(ValueError):
                    load_config(path)
            path.write_text('{"screenshots":{"enabled":true,"enabled":false}}')
            with self.assertRaises(ValueError):
                load_config(path)

    def test_optional_tool_has_file_write_annotations_and_small_schema(self):
        defaults = {tool.name for tool in tool_definitions()}
        enabled = {tool.name: tool for tool in tool_definitions(screenshots_enabled=True)}
        self.assertEqual(set(enabled) - defaults, {'capture_screenshot'})
        tool = enabled['capture_screenshot']
        self.assertFalse(tool.annotations.readOnlyHint)
        self.assertFalse(tool.annotations.destructiveHint)
        self.assertFalse(tool.annotations.idempotentHint)
        self.assertEqual(set(tool.inputSchema['properties']), {'filename'})
        self.assertFalse(tool.inputSchema['additionalProperties'])


class ScreenshotStoreTests(unittest.TestCase):
    def test_save_png_and_reject_overwrite_including_symlink(self):
        from screenshot_tool import ScreenshotStore, ScreenshotError
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = ScreenshotStore(root / 'nested')
            result = store.save(png_payload(), {'filename': '01-选择.png'})
            self.assertEqual(result, {'path': str(root / 'nested/01-选择.png'), 'width': 1, 'height': 1})
            self.assertEqual(Path(result['path']).read_bytes(), base64.b64decode(png_payload()['png_base64']))
            with self.assertRaises(ScreenshotError) as raised:
                store.save(png_payload(), {'filename': '01-选择.png'})
            self.assertEqual(raised.exception.code, 'file_exists')
            victim = root / 'victim'; victim.write_text('unchanged')
            (root / 'nested/link.png').symlink_to(victim)
            with self.assertRaises(ScreenshotError):
                store.save(png_payload(), {'filename': 'link.png'})
            self.assertEqual(victim.read_text(), 'unchanged')
            automatic = store.save(png_payload(), {})
            self.assertTrue(Path(automatic['path']).name.endswith('.png'))

    def test_invalid_arguments_never_escape_directory(self):
        from screenshot_tool import screenshot_arguments
        for value in [False, [], {'path': '/tmp/test.png'}, {'filename': None}, {'filename': 1},
                      {'filename': '../escape.png'}, {'filename': '/tmp/escape.png'},
                      {'filename': r'a\escape.png'}, {'filename': 'bad\0.png'},
                      {'filename': 'bad.jpg'}, {'filename': 'x' * 129 + '.png'}]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                screenshot_arguments(value)

    def test_malformed_or_mismatched_png_is_rejected_before_writing(self):
        from screenshot_tool import ScreenshotStore
        mutations = [lambda d: d.update(width=True), lambda d: d.update(height=2),
                     lambda d: d.update(png_base64='invalid'), lambda d: d.update(width=999999),
                     lambda d: d.pop('png_base64'),
                     lambda d: d.update(png_base64=base64.b64encode(base64.b64decode(d['png_base64'])[:-1]).decode())]
        with tempfile.TemporaryDirectory() as directory:
            for mutate in mutations:
                payload = png_payload(); mutate(payload)
                with self.subTest(payload=payload), self.assertRaises((ValueError, KeyError)):
                    ScreenshotStore(Path(directory)).save(payload, {})
            self.assertEqual(list(Path(directory).iterdir()), [])


class CaptureClient:
    def __init__(self):
        self.calls = []
        self.token = 'fixture-1'
        self.error = None
        self.payload = None

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append(operation)
        if operation == 'capture_screenshot':
            if self.error:
                return {'ok': False, 'error': {'code': self.error}}
            state = self.payload or png_payload()
        else:
            state = combat()
        state = copy.deepcopy(state)
        state['snapshot_id'] = self.token
        return {'ok': True, 'state': state}


class ScreenshotSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_permission_preserved_only_for_unchanged_capture_and_never_created(self):
        with tempfile.TemporaryDirectory() as directory:
            client = CaptureClient()
            tools = GameTools(client, screenshot_directory=Path(directory))
            result = await tools.capture_screenshot()
            self.assertNotIn('png_base64', result)
            self.assertNotIn('snapshot_id', result)
            self.assertNotIn('private', result)
            self.assertIsNone(tools.snapshot_id)
            await tools.get_observation()
            await tools.capture_screenshot()
            self.assertEqual(tools.snapshot_id, 'fixture-1')
            client.token = 'fixture-2'
            await tools.capture_screenshot()
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_disabled_bad_filename_unavailable_and_save_failure_clear_permission(self):
        client = CaptureClient()
        disabled = GameTools(client)
        self.assertEqual((await disabled.capture_screenshot())['error']['code'], 'invalid_request')
        self.assertEqual(client.calls, [])
        with tempfile.TemporaryDirectory() as directory:
            tools = GameTools(client, screenshot_directory=Path(directory))
            await tools.get_observation()
            self.assertEqual((await tools.capture_screenshot({'filename': '../bad.png'}))['error']['code'], 'invalid_request')
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(client.calls, ['get_state'])
            client.error = 'screenshot_unavailable'
            await tools.get_observation()
            error = (await tools.capture_screenshot())['error']
            self.assertEqual(error['code'], 'screenshot_unavailable')
            self.assertNotIn('outcome', error)
            self.assertIsNone(tools.snapshot_id)
            client.error = None
            result = await tools.capture_screenshot({'filename': 'same.png'})
            self.assertIn('path', result)
            await tools.get_observation()
            self.assertEqual((await tools.capture_screenshot({'filename': 'same.png'}))['error']['code'], 'file_exists')
            self.assertIsNone(tools.snapshot_id)
            blocked = Path(directory) / 'file'; blocked.write_text('block')
            broken = GameTools(client, screenshot_directory=blocked)
            self.assertEqual((await broken.capture_screenshot())['error']['code'], 'screenshot_save_failed')

    async def test_cancelled_capture_does_not_restore_permission(self):
        import threading
        started, released = threading.Event(), threading.Event()
        class SlowClient(CaptureClient):
            def call(self, operation, *args, **kwargs):
                if operation == 'capture_screenshot':
                    started.set(); released.wait(3)
                return super().call(operation, *args, **kwargs)
        with tempfile.TemporaryDirectory() as directory:
            tools = GameTools(SlowClient(), screenshot_directory=Path(directory))
            await tools.get_observation()
            async with anyio.create_task_group() as group:
                group.start_soon(tools.capture_screenshot)
                await anyio.to_thread.run_sync(started.wait)
                group.cancel_scope.cancel()
                released.set()
            self.assertIsNone(tools.snapshot_id)


class ScreenshotStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_configuration_controls_registration_and_stays_fixed_until_restart(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from test_mcp_server import FakeGame, SERVER
        with FakeGame() as game:
            game.screenshot_payload = png_payload()
            config = game.directory / 'config.json'
            for enabled in (False, True):
                config.write_text(json.dumps({'screenshots': {'enabled': enabled, 'directory': 'captures'}}))
                parameters = StdioServerParameters(command=sys.executable, cwd='/tmp', args=[str(SERVER),
                    '--ipc-dir', str(game.directory), '--config', str(config)])
                async with stdio_client(parameters) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        listed = {tool.name for tool in (await session.list_tools()).tools}
                        self.assertEqual('capture_screenshot' in listed, enabled)
                        self.assertEqual(len(listed), 43 if enabled else 42)
                        config.write_text(json.dumps({'screenshots': {'enabled': not enabled, 'directory': 'elsewhere'}}))
                        self.assertEqual(listed, {tool.name for tool in (await session.list_tools()).tools})
                        if not enabled:
                            result = await session.call_tool('capture_screenshot', {})
                            self.assertTrue(result.isError)
                            self.assertEqual(result.structuredContent['error']['code'], 'invalid_request')
                            self.assertEqual(game.operations, [])
                            continue
                        first = await session.call_tool('capture_screenshot', {'filename': '01.png'})
                        self.assertFalse(first.isError)
                        self.assertEqual(json.loads(first.content[0].text), first.structuredContent)
                        self.assertEqual(first.structuredContent['path'], str(game.directory / 'captures/01.png'))
                        self.assertEqual((await session.call_tool('end_turn', {})).structuredContent['error']['code'], 'observation_required')
                        await session.call_tool('get_observation', {})
                        result = await session.call_tool('capture_screenshot', {'filename': '02.png'})
                        self.assertFalse(result.isError)
                        action = await session.call_tool('end_turn', {})
                        self.assertFalse(action.isError)
                        self.assertEqual(action.structuredContent['turn'], 2)
                        request = next(item for item in game.operations if item['operation'] == 'capture_screenshot')
                        self.assertNotIn('arguments', request)


class ScreenshotStartupTests(unittest.TestCase):
    def test_invalid_or_missing_explicit_config_fails_before_opening_ipc(self):
        from test_mcp_server import SERVER
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / 'bad.json'
            for content in (None, '{broken', '{"screenshots":{"enabled":"yes"}}'):
                if content is not None:
                    config.write_text(content)
                result = subprocess.run([sys.executable, str(SERVER), '--ipc-dir', str(root / 'ipc'),
                                         '--config', str(config)], capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, '')
                self.assertIn('error:', result.stderr)
                self.assertFalse((root / 'ipc').exists())
