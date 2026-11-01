import copy
import unittest

from game_tools import GameTools
from inspection_details import inspection_details
from player_output import player_result
from test_output_boundaries import observation


def state():
    raw = observation()
    raw.update(snapshot_id='rest-1', scene='rest_site', turn=None, player=None, enemies=None, buttons=None,
               selection=None, rewards=None, available_actions=['choose_rest_option'], rest_site={
                   'status': 'visible', 'prompt': 'What would you like to do?', 'description': None,
                   'options': [{'id': 'HEAL', 'text': 'Rest', 'enabled': True},
                               {'id': 'SMITH', 'text': 'Smith', 'enabled': False}], 'proceed': None})
    return raw


class RestSiteOutputTests(unittest.TestCase):
    def test_observation_keeps_options_without_hover_or_future_contents(self):
        raw = state()
        raw['rest_site']['options'][0].update(description='Heal 24 HP.', future_reward='Secret relic')
        public = player_result({'ok': True, 'state': inspection_details('get_state', raw)})
        self.assertEqual(public['rest_site']['options'], [
            {'id': 'HEAL', 'text': 'Rest', 'enabled': True}, {'id': 'SMITH', 'text': 'Smith', 'enabled': False}])
        self.assertNotIn('snapshot_id', public)
        self.assertNotIn('Secret relic', str(public))

    def test_inspection_returns_dynamic_disabled_descriptions(self):
        raw = state()
        for item, text in zip(raw['rest_site']['options'], ('Heal 24 HP.', 'No cards can be upgraded.')):
            item.update(description=text, future_reward='Secret')
        result = player_result({'ok': True, 'state': inspection_details('inspect_rest_site', raw)})
        self.assertEqual(result['rest_site']['options'][1]['description'], 'No cards can be upgraded.')
        self.assertFalse(result['rest_site']['options'][1]['enabled'])
        self.assertNotIn('Secret', str(result))

    def test_covered_missing_duplicate_and_malformed_states_are_rejected(self):
        variants = []
        for mutate in (lambda r: r.pop('rest_site'), lambda r: r.update(rest_site=None),
                       lambda r: r['rest_site'].update(status='covered'),
                       lambda r: r['rest_site']['options'].append(copy.deepcopy(r['rest_site']['options'][0])),
                       lambda r: r['rest_site']['options'][0].update(id=''),
                       lambda r: r['rest_site']['options'][0].update(enabled=1)):
            raw = state(); mutate(raw); variants.append(raw)
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)):
                inspection_details('get_state', raw)
        raw = state()
        raw['rest_site'] = {'status': 'covered', 'prompt': None, 'description': None, 'options': None, 'proceed': None}
        raw['available_actions'] = []
        self.assertIsNone(inspection_details('get_state', raw)['rest_site']['options'])
        with self.assertRaises(ValueError):
            inspection_details('inspect_rest_site', raw)

    def test_deck_upgrade_previews_preserve_original_ids_and_reject_hidden_clones(self):
        from test_selection import selection
        raw = state()
        raw['selection'] = selection()
        before = {'id': 5, 'name': 'Defend', 'description': 'Gain 5 Block.'}
        after = {'id': 5, 'name': 'Defend+', 'description': 'Gain 8 Block.', 'private': 'secret'}
        raw['selection'].update(type='deck_upgrade', selected_ids=[5], upgrade_previews=[{'before': before, 'after': after}])
        result = inspection_details('get_state', raw)['selection']
        self.assertEqual(result['upgrade_previews'][0]['after'],
                         {'id': 5, 'name': 'Defend+', 'description': 'Gain 8 Block.'})
        raw['selection']['upgrade_previews'][0]['after']['id'] = 100
        with self.assertRaises(ValueError): inspection_details('get_state', raw)
        raw['selection']['upgrade_previews'][0]['after']['id'] = 5
        raw['selection']['status'] = 'covered'
        with self.assertRaises(ValueError): inspection_details('get_state', raw)


class RestClient:
    def __init__(self):
        self.raw = state()
        self.calls = []

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'inspect_rest_site':
            result = copy.deepcopy(self.raw)
            for item in result['rest_site']['options']: item['description'] = 'Native help.'
            return {'ok': True, 'state': result}
        if operation == 'choose_rest_option':
            if expected_state != self.raw['snapshot_id']: return {'ok': False, 'error': {'code': 'stale_state'}}
            self.raw.update(snapshot_id='rest-2', available_actions=['proceed'],
                            transition={'complete': True, 'stop_reason': 'action_completed', 'events': []})
            self.raw['rest_site'].update(options=[], proceed={'text': 'Proceed', 'enabled': True})
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class RestSiteSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_inspection_and_action_result_support_continuation(self):
        tools = GameTools(RestClient())
        await tools.inspect_rest_site()
        result = await tools.choose_rest_option({'option_id': 'HEAL'})
        self.assertEqual(result['available_actions'], ['proceed'])
        self.assertEqual(tools.snapshot_id, 'rest-2')

    async def test_invalid_arguments_consume_permission_and_do_not_click(self):
        for args in (None, {}, {'option_id': 0}, {'option_id': ''}, {'option_id': 'x' * 129},
                     {'option_id': 'HEAL', 'repeat': True}):
            with self.subTest(args=args):
                client = RestClient(); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.choose_rest_option(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual(len(client.calls), 1)


class RestSiteStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_routes_option_and_invalid_request_clears_permission(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from test_mcp_server import FakeGame, SERVER

        class RestGame(FakeGame):
            def run(self):
                client = RestClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text())
                        self.operations.append(request)
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp')
                        temporary.write_text(json.dumps(response))
                        temporary.replace(target)
                        path.unlink()

        with RestGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory),
                                                                         '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.call_tool('inspect_rest_site', {})
                    bad = await session.call_tool('choose_rest_option', {'option_id': 'HEAL', 'repeat': True})
                    self.assertEqual(bad.structuredContent['error']['code'], 'invalid_request')
                    missing = await session.call_tool('choose_rest_option', {'option_id': 'HEAL'})
                    self.assertEqual(missing.structuredContent['error']['code'], 'observation_required')
                    await session.call_tool('get_observation', {})
                    selected = await session.call_tool('choose_rest_option', {'option_id': 'HEAL'})
                    self.assertNotIn('rest_site', selected.structuredContent)
                    self.assertEqual(selected.structuredContent['transition']['stop_reason'], 'action_completed')
                    self.assertEqual(json.loads(selected.content[0].text), selected.structuredContent)
            self.assertEqual([r['operation'] for r in game.operations],
                             ['inspect_rest_site', 'get_state', 'choose_rest_option'])
