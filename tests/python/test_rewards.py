import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


def rewards(status='visible'):
    return {'status': status, 'title': 'Loot!' if status == 'visible' else None, 'items': [
        {'id': 12, 'type': 'gold', 'text': '17 Gold', 'enabled': True, 'linked_group': None},
        {'id': 14, 'type': 'card', 'text': 'Add a card to your deck.', 'enabled': True, 'linked_group': None},
    ] if status == 'visible' else None,
        'proceed': {'text': 'Skip', 'enabled': True, 'skips_remaining': True} if status == 'visible' else None}


def state(status='visible'):
    result = observation()
    result.update(snapshot_id='reward-1', scene='rewards', turn=None, player=None, enemies=None, buttons=None,
                  screen={'status': 'visible' if status == 'visible' else 'covered'}, rewards=rewards(status),
                  selection=None, available_actions=['claim_reward', 'proceed'] if status == 'visible' else [])
    return result


class RewardOutputTests(unittest.TestCase):
    def test_observation_keeps_visible_reward_rows_but_filters_hidden_fields(self):
        raw = state()
        raw['rewards']['items'][1].update(cards=[{'name': 'Secret candidate'}], backend_id=999)
        result = player_result({'ok': True, 'state': inspection_details('get_state', raw)})
        self.assertEqual(result['scene'], 'rewards')
        self.assertEqual(result['rewards'], rewards())
        self.assertNotIn('snapshot_id', result)
        self.assertNotIn('Secret candidate', str(result))

    def test_covered_and_empty_rewards_are_distinct(self):
        covered = inspection_details('get_state', state('covered'))
        self.assertEqual(covered['rewards'], {'status': 'covered', 'title': None, 'items': None, 'proceed': None})
        empty = state()
        empty['rewards']['items'] = []
        empty['rewards']['proceed'].update(text='Proceed', skips_remaining=False)
        self.assertEqual(inspection_details('get_state', empty)['rewards']['items'], [])

    def test_malformed_or_hidden_reward_contents_are_rejected(self):
        mutations = [lambda r: r.pop('rewards'), lambda r: r.update(rewards=None),
                     lambda r: r['rewards'].pop('items'),
                     lambda r: r['rewards'].update(status='unknown'),
                     lambda r: r['rewards']['items'].append(copy.deepcopy(r['rewards']['items'][0])),
                     lambda r: r['rewards']['items'][0].update(id=True),
                     lambda r: r['rewards']['items'][0].update(id=-1),
                     lambda r: r['rewards']['items'][0].update(type='made_up'),
                     lambda r: r['rewards']['items'][0].pop('text'),
                     lambda r: r['rewards']['proceed'].update(skips_remaining=1),
                     lambda r: r['rewards'].update(status='covered')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                raw = state()
                mutate(raw)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    inspection_details('get_state', raw)

    def test_inspection_returns_only_actual_hover_help_and_preserves_reward_ids(self):
        raw = state()
        raw['rewards']['items'][0]['hover_tips'] = []
        raw['rewards']['items'][1]['hover_tips'] = [{'title': 'Help', 'description': 'Visible tooltip', 'secret': 3}]
        raw['rewards']['items'][1]['cards'] = [{'name': 'Do not reveal'}]
        result = player_result({'ok': True, 'state': inspection_details('inspect_rewards', raw)})
        self.assertEqual(result['rewards']['items'][1]['hover_tips'], [{'title': 'Help', 'description': 'Visible tooltip'}])
        self.assertNotIn('cards', str(result))
        raw['rewards']['items'][1].pop('hover_tips')
        with self.assertRaises((ValueError, KeyError)):
            inspection_details('inspect_rewards', raw)

    def test_reward_actions_do_not_leak_through_incomplete_transition(self):
        for reason, complete, expected in [('action_completed', True, ['claim_reward', 'proceed']),
                                          ('timeout', False, []), ('interrupted', False, [])]:
            raw = state()
            raw['transition'] = {'stop_reason': reason, 'complete': complete, 'events': []}
            raw['reward_result'] = {'reward_id': 12, 'status': 'pending'}
            result = inspection_details('claim_reward', raw)
            self.assertEqual(result['available_actions'], expected)

    def test_failed_pickup_is_explicit_and_unknown_reward_outcomes_are_rejected(self):
        raw = state()
        raw.update(transition={'stop_reason': 'action_completed', 'complete': True, 'events': []},
                   reward_result={'reward_id': 12, 'status': 'not_claimed', 'secret': 'hidden'})
        result = inspection_details('claim_reward', raw)
        self.assertEqual(result['reward_result'], {'reward_id': 12, 'status': 'not_claimed'})
        raw['reward_result']['status'] = 'probably_claimed'
        with self.assertRaises(ValueError):
            inspection_details('claim_reward', raw)

    def test_catalog_exposes_separate_reward_actions_and_readonly_details(self):
        tools = {t.name: t for t in tool_definitions()}
        self.assertIn('claim_reward', tools)
        self.assertIn('proceed', tools)
        self.assertIn('inspect_rewards', tools)
        self.assertTrue(tools['inspect_rewards'].annotations.readOnlyHint)
        self.assertFalse(tools['claim_reward'].annotations.readOnlyHint)
        self.assertEqual(tools['claim_reward'].inputSchema['required'], ['reward_id'])


class RewardClient:
    def __init__(self):
        self.raw = state()
        self.calls = []

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'get_state':
            return {'ok': True, 'state': copy.deepcopy(self.raw)}
        if operation == 'inspect_rewards':
            details = copy.deepcopy(self.raw)
            for item in details['rewards']['items']:
                item['hover_tips'] = []
            return {'ok': True, 'state': details}
        if expected_state != self.raw['snapshot_id']:
            return {'ok': False, 'error': {'code': 'stale_state'}}
        self.raw['snapshot_id'] += 'x'
        if operation == 'claim_reward':
            self.raw['reward_result'] = {'reward_id': arguments['reward_id'], 'status': 'claimed'}
            self.raw['rewards']['items'] = [r for r in self.raw['rewards']['items'] if r['id'] != arguments['reward_id']]
        elif operation == 'proceed':
            self.raw.update(screen={'status': 'covered', 'view': 'map'}, rewards=rewards('covered'), available_actions=[])
        self.raw['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class RewardSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_claim_chain_preserves_ids_and_map_result_clears_permission(self):
        client = RewardClient()
        tools = GameTools(client)
        initial = await tools.get_observation()
        self.assertEqual(initial['available_actions'], ['claim_reward', 'proceed'])
        self.assertNotIn('error', await tools.inspect_rewards())
        result = await tools.claim_reward({'reward_id': 12})
        self.assertNotIn('rewards', result)
        self.assertEqual(result['reward_result'], {'reward_id': 12, 'status': 'claimed'})
        self.assertEqual(tools.snapshot_id, 'reward-1x')
        result = await tools.proceed()
        self.assertEqual(result['screen']['view'], 'map')
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual(client.calls, [('get_state', None, None), ('inspect_rewards', None, None),
                                       ('claim_reward', 'reward-1', {'reward_id': 12}), ('proceed', 'reward-1x', None)])

    async def test_illegal_arguments_preserve_permission_without_sending_action(self):
        cases = [('claim_reward', None), ('claim_reward', {'reward_id': True}),
                 ('claim_reward', {'reward_id': -1}), ('claim_reward', {'reward_id': 2**31}),
                 ('claim_reward', {'reward_id': 12, 'all': True}), ('proceed', {'skip': True})]
        for name, args in cases:
            with self.subTest(name=name, args=args):
                client = RewardClient()
                tools = GameTools(client)
                await tools.get_observation()
                result = await getattr(tools, name)(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(len(client.calls), 1)
                self.assertEqual(tools.snapshot_id, 'reward-1')

    async def test_no_observation_cannot_claim_or_proceed(self):
        tools = GameTools(RewardClient())
        self.assertEqual((await tools.claim_reward({'reward_id': 12}))['error']['code'], 'observation_required')
        self.assertEqual((await tools.proceed())['error']['code'], 'observation_required')


class RewardStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_routes_reward_arguments_and_preserves_invalid_proceed_permission(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER

        class RewardGame(FakeGame):
            def run(self):
                client = RewardClient()
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

        with RewardGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory),
                                                                         '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.call_tool('inspect_rewards', {})
                    claimed = await session.call_tool('claim_reward', {'reward_id': 12})
                    self.assertNotIn('rewards', claimed.structuredContent)
                    details = await session.call_tool('inspect_rewards', {})
                    self.assertEqual([r['id'] for r in details.structuredContent['rewards']['items']], [14])
                    self.assertEqual(json.loads(claimed.content[0].text), claimed.structuredContent)
                    bad = await session.call_tool('proceed', {'skip': True})
                    self.assertEqual(bad.structuredContent['error']['code'], 'invalid_request')
                    result = await session.call_tool('proceed', {})
                    self.assertEqual(result.structuredContent['screen']['view'], 'map')
            self.assertEqual([r['operation'] for r in game.operations],
                             ['inspect_rewards', 'claim_reward', 'inspect_rewards', 'proceed'])
