import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


def state():
    raw = observation()
    raw.update(snapshot_id='treasure-1', scene='treasure', turn=None, player=None, enemies=None, buttons=None,
               selection=None, rewards=None, rest_site=None, available_actions=['loot_treasure'], treasure={
                   'status': 'visible', 'chest': 'closed', 'relic': None, 'proceed': None})
    return raw


class TreasureOutputTests(unittest.TestCase):
    def test_closed_chest_and_basic_observation_do_not_reveal_hover_or_generated_contents(self):
        raw = state()
        raw['treasure']['generated_relics'] = ['Secret']
        public = player_result({'ok': True, 'state': inspection_details('get_state', raw)})
        self.assertEqual(public['treasure'], {'status': 'visible', 'chest': 'closed', 'relic': None, 'proceed': None})
        raw['treasure'].update(chest='open', relic={'name': 'Anchor', 'enabled': True,
                                                   'description': 'Gain Block.', 'hover_tips': []})
        public = player_result({'ok': True, 'state': inspection_details('get_state', raw)})
        self.assertEqual(public['treasure']['relic'], {'name': 'Anchor', 'enabled': True})
        self.assertNotIn('snapshot_id', public)

    def test_inspection_includes_only_visible_relic_help(self):
        raw = state()
        raw['treasure'].update(chest='open', relic={'name': 'Anchor', 'enabled': True,
            'description': 'Gain 10 Block.', 'hover_tips': [{'title': 'Block', 'description': 'Prevents damage.', 'secret': 1}],
            'hidden': 'Secret'})
        result = player_result({'ok': True, 'state': inspection_details('inspect_treasure', raw)})
        self.assertEqual(result['treasure']['relic']['description'], 'Gain 10 Block.')
        self.assertEqual(result['treasure']['relic']['hover_tips'], [{'title': 'Block', 'description': 'Prevents damage.'}])
        self.assertNotIn('Secret', str(result))

    def test_hidden_or_inconsistent_treasure_is_rejected(self):
        for mutate in (lambda r: r.pop('treasure'), lambda r: r.update(treasure=None),
                       lambda r: r['treasure'].update(chest='unknown'),
                       lambda r: r['treasure'].update(status='covered'),
                       lambda r: r['treasure'].update(relic={'name': 'Anchor', 'enabled': True}),
                       lambda r: r['treasure'].update(chest='open', relic={'name': 'Anchor', 'enabled': 1})):
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)):
                inspection_details('get_state', raw)
        raw = state()
        raw['treasure'] = {'status': 'covered', 'chest': None, 'relic': None, 'proceed': None}
        raw['available_actions'] = []
        self.assertEqual(inspection_details('get_state', raw)['treasure'], raw['treasure'])
        with self.assertRaises(ValueError): inspection_details('inspect_treasure', raw)


class TreasureClient:
    def __init__(self): self.raw = state(); self.calls = []

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'loot_treasure':
            self.raw.update(snapshot_id='treasure-2', transition={'complete': True, 'stop_reason': 'action_completed', 'events': []})
            self.raw['treasure'].update(chest='open', proceed={'text': 'Proceed', 'enabled': True, 'skips_remaining': False})
            self.raw['available_actions'] = ['proceed']
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class TreasureSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_inspection_permission_and_default_compound_action_chain(self):
        client = TreasureClient(); tools = GameTools(client)
        await tools.inspect_treasure()
        result = await tools.loot_treasure()
        self.assertEqual(result['available_actions'], ['proceed'])
        self.assertEqual(tools.snapshot_id, 'treasure-2')
        await tools.proceed()
        self.assertEqual(client.calls[-1][1], 'treasure-2')

    async def test_invalid_arguments_consume_permission_without_game_call(self):
        for args in ({'open_only': 1}, {'open_only': None}, {'open_only': 'false'}, {'repeat': True}, [], False):
            client = TreasureClient(); tools = GameTools(client)
            await tools.get_observation()
            result = await tools.loot_treasure(args)
            self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(len(client.calls), 1)
        client = TreasureClient(); tools = GameTools(client)
        await tools.get_observation(); await tools.loot_treasure({'open_only': True})
        self.assertEqual(client.calls[-1][2], {'open_only': True})


class TreasureStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_routes_compound_action_and_open_only(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER

        class TreasureGame(FakeGame):
            def run(self):
                client = TreasureClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text()); self.operations.append(request)
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(response)); temporary.replace(target)
                        path.unlink()

        with TreasureGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory),
                                                                         '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.call_tool('get_observation', {})
                    bad = await session.call_tool('loot_treasure', {'open_only': 1})
                    self.assertEqual(bad.structuredContent['error']['code'], 'invalid_request')
                    await session.call_tool('get_observation', {})
                    result = await session.call_tool('loot_treasure', {'open_only': True})
                    self.assertNotIn('treasure', result.structuredContent)
                    self.assertEqual(result.structuredContent['transition']['stop_reason'], 'action_completed')
                    self.assertEqual(json.loads(result.content[0].text), result.structuredContent)
            self.assertEqual(game.operations[-1]['arguments'], {'open_only': True})
