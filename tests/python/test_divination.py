import base64
import copy
import json
import sys
import struct
import unittest
import zlib

from sts2_mcp.output.game_output import observation_details
from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_server import tool_result
from sts2_mcp.output.player_output import player_result
from tests.python.test_events import state as event_state
from tests.python.test_screenshots import png_payload


def state():
    raw = event_state()
    raw.update(snapshot_id='sphere-1', screen={'status': 'visible', 'view': 'divination'},
               available_actions=['set_divination_tool', 'divine'], divination={
        'status': 'visible', 'phase': 'playing', 'remaining': 3, 'tool': 'big',
        'tools': [{'id': 'big', 'text': 'Big Divination', 'enabled': True},
                  {'id': 'small', 'text': 'Small Divination', 'enabled': True}],
        'instructions': {'title': 'How to divine', 'description': 'Uncover the future.'},
        'dialogue': None, 'grid': {'columns': 11, 'rows': 11, 'covered_rows': ['###########'] * 11,
                                  'image': {'width': 1, 'height': 1}, 'hidden_items': ['Secret']},
        'proceed': None, 'rng': 'Secret'}, divination_image=png_payload())
    raw['event'] = {'status': 'covered', **dict.fromkeys(('name', 'description', 'options', 'proceed'))}
    return raw


def replace_pixels(raw, compressed):
    image = raw['divination_image']
    data = base64.b64decode(image['png_base64'])
    chunk = struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', zlib.crc32(b'IDAT' + compressed))
    image['png_base64'] = base64.b64encode(data[:33] + chunk + data[-12:]).decode()


class DivinationOutputTests(unittest.TestCase):
    def test_visible_grid_survives_without_hidden_items_or_image_bytes(self):
        public = player_result({'ok': True, 'state': observation_details(state())})
        self.assertEqual(public['divination']['grid']['covered_rows'], ['###########'] * 11)
        self.assertNotIn('Secret', json.dumps(public))
        self.assertNotIn('divination_image', public)
        self.assertNotIn('manual input', json.dumps(public))

    def test_covered_grid_cannot_leak_pixels_or_state(self):
        raw = state(); raw['divination']['status'] = 'covered'
        with self.assertRaises(ValueError): observation_details(raw)
        raw['divination'] = {'status': 'covered', **dict.fromkeys(k for k in raw['divination'] if k not in {'status', 'rng'})}
        self.assertIsNone(observation_details(raw)['divination']['grid'])

    def test_missing_grid_rows_bad_cells_and_missing_divination_are_rejected(self):
        for mutate in (lambda r: r.pop('divination'), lambda r: r['divination']['grid'].update(covered_rows=['#'] * 11),
                       lambda r: r['divination']['grid'].update(covered_rows=['???????????'] * 11),
                       lambda r: r['divination'].update(remaining=True), lambda r: r['divination'].update(tool='unknown')):
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)): observation_details(raw)

    def test_visible_board_under_another_screen_is_rejected(self):
        raw = state(); raw['screen'] = {'status': 'covered', 'view': 'map'}
        with self.assertRaises(ValueError): observation_details(raw)

    def test_closing_map_can_return_to_the_supported_divination_board(self):
        from sts2_mcp.output.inspection_details import inspection_details
        closed = inspection_details('close_map', state())
        self.assertEqual(closed['divination']['phase'], 'playing')
        self.assertEqual(closed['screen'], {'status': 'visible', 'view': 'divination'})


class DivinationClient:
    def __init__(self): self.raw = state(); self.calls = []
    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'set_divination_tool': self.raw['divination']['tool'] = arguments['tool']
        if operation == 'divine': self.raw['divination']['remaining'] -= 1
        if operation in {'set_divination_tool', 'divine'}:
            self.raw['snapshot_id'] = 'sphere-' + str(len(self.calls))
            self.raw['transition'] = {'complete': True, 'stop_reason': 'action_completed', 'events': []}
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class DivinationSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_config_returns_image_and_reuses_successful_action_observation(self):
        client = DivinationClient(); tools = GameTools(client)
        observed = tool_result(await tools.get_observation())
        self.assertEqual([c.type for c in observed.content], ['text', 'image'])
        self.assertEqual(observed.content[1].mimeType, 'image/png')
        self.assertEqual(base64.b64decode(observed.content[1].data), base64.b64decode(png_payload()['png_base64']))
        self.assertEqual(json.loads(observed.content[0].text), observed.structuredContent)
        self.assertNotIn('png_base64', observed.content[0].text)
        changed = await tools.set_divination_tool({'tool': 'small'})
        self.assertNotIn('divination', changed)
        self.assertEqual((await tools.inspect_event())['divination']['tool'], 'small')
        result = await tools.divine({'x': 0, 'y': 10})
        self.assertNotIn('divination', result)
        self.assertEqual([c.type for c in tool_result(result).content], ['text'])
        self.assertEqual(client.calls[-1], ('divine', 'sphere-2', {'x': 0, 'y': 10}))
        self.assertEqual((await tools.inspect_event())['divination']['remaining'], 2)

    async def test_strict_arguments_and_inspection_supports_action(self):
        for operation, arguments in [('divine', {'x': True, 'y': 0}), ('divine', {'x': 0.0, 'y': 0}),
                ('divine', {'x': 11, 'y': 0}), ('divine', {'x': -1, 'y': 0}), ('divine', {'x': 0, 'y': '0'}),
                ('divine', {'x': 0, 'y': 0, 'extra': 1}), ('divine', {}),
                ('set_divination_tool', {'tool': 'none'}), ('set_divination_tool', {'tool': 'small', 'x': 0})]:
            client = DivinationClient(); tools = GameTools(client)
            self.assertEqual((await getattr(tools, operation)(arguments))['error']['code'], 'invalid_request')
            self.assertEqual(client.calls, [])
        tools = GameTools(DivinationClient())
        await tools.inspect_event()
        self.assertNotIn('error', await tools.divine({'x': 5, 'y': 5}))

    async def test_missing_invalid_or_mismatched_image_revokes_permission(self):
        for mutate in (lambda r: r.pop('divination_image'), lambda r: r['divination_image'].update(png_base64='invalid'),
                       lambda r: r['divination_image'].update(width=2), lambda r: replace_pixels(r, b'not a zlib stream'),
                       lambda r: replace_pixels(r, zlib.compress(b'\0' * 10000)),
                       lambda r: replace_pixels(r, zlib.compress(b'\0')),
                       lambda r: replace_pixels(r, zlib.compress(b'\5\xff\0\0\xff'))):
            client = DivinationClient(); tools = GameTools(client)
            await tools.get_observation(); mutate(client.raw)
            result = await tools.get_observation()
            self.assertIn('error', result)
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual((await tools.divine({'x': 5, 'y': 5}))['error']['code'], 'observation_required')

    async def test_covered_board_never_attaches_private_image(self):
        client = DivinationClient()
        client.raw['screen'] = {'status': 'covered', 'view': 'map'}
        client.raw['available_actions'] = []
        client.raw['divination'] = {'status': 'covered', **dict.fromkeys(k for k in client.raw['divination'] if k not in {'status', 'rng'})}
        result = tool_result(await GameTools(client).get_observation())
        self.assertEqual([c.type for c in result.content], ['text'])
        self.assertNotIn('png_base64', result.content[0].text)

    async def test_bad_required_image_rejects_inspection_but_does_not_affect_action_receipt(self):
        for operation in ('inspect_event', 'divine'):
            client = DivinationClient(); tools = GameTools(client)
            await tools.get_observation()
            client.raw['divination_image']['png_base64'] = 'broken'
            result = await tools.inspect_event() if operation == 'inspect_event' else await tools.divine({'x': 5, 'y': 5})
            if operation == 'inspect_event':
                self.assertIn('error', result)
                self.assertIsNone(tools.snapshot_id)
            else:
                self.assertNotIn('error', result)
                self.assertTrue(result['transition']['complete'])
                self.assertIsNotNone(tools.snapshot_id)
                self.assertNotIn('divination', result)

    async def test_stdio_delivers_native_image_content_without_screenshot_tool(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER
        class SphereGame(FakeGame):
            def run(self):
                client = DivinationClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text()); self.operations.append(request)
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(response)); temporary.replace(target)
                        path.unlink()
        with SphereGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory), '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self.assertNotIn('capture_screenshot', {t.name for t in (await session.list_tools()).tools})
                    response = await session.call_tool('get_observation', {})
                    self.assertEqual([c.type for c in response.content], ['text', 'image'])
                    response = await session.call_tool('divine', {'x': 3, 'y': 6})
                    self.assertNotIn('divination', response.structuredContent)
                    self.assertEqual([c.type for c in response.content], ['text'])
                    response = await session.call_tool('inspect_event', {})
                    self.assertEqual(response.structuredContent['divination']['remaining'], 2)
                    self.assertEqual([c.type for c in response.content], ['text', 'image'])
