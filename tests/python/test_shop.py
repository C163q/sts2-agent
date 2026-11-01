import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


def state(opened=True):
    raw = observation()
    raw.update(snapshot_id='shop-1', scene='shop', turn=None, player=None, enemies=None, buttons=None,
               selection=None, rewards=None, rest_site=None, treasure=None, available_actions=['buy_item', 'close_shop'], shop={
                   'status': 'visible', 'view': 'inventory' if opened else 'merchant',
                   'items': [{'id': 0, 'kind': 'card', 'position': 'character_card:0', 'price': 50, 'affordable': True,
                              'enabled': True, 'on_sale': False, 'card': {'name': 'Strike+', 'type': 'Attack', 'rarity': 'basic',
                              'visual_card_pool': 'Ironclad', 'energy_cost': '1', 'star_cost': '0',
                              'description': 'Deal 9 damage.', 'hover_tips': []}, 'secret': 'hidden'}] if opened else None,
                   'open': None if opened else {'enabled': True}, 'back': {'enabled': True} if opened else None,
                   'proceed': None if opened else {'text': 'Proceed', 'enabled': True}})
    return raw


class ShopOutputTests(unittest.TestCase):
    def test_card_summary_hides_effect_but_inspection_returns_all_item_help(self):
        raw = state()
        basic = inspection_details('get_state', raw)
        self.assertNotIn('description', basic['shop']['items'][0]['card'])
        public = player_result({'ok': True, 'state': inspection_details('inspect_shop', raw)})
        self.assertEqual(public['shop']['items'][0]['card']['description'], 'Deal 9 damage.')
        self.assertNotIn('secret', str(public))
        self.assertNotIn('snapshot_id', public)
        for kind in ('relic', 'potion', 'card_removal'):
            item = {'id': 2, 'kind': kind, 'position': kind + ':0', 'price': 100, 'affordable': False,
                    'enabled': False, 'name': 'Visible', 'description': 'Help.', 'hover_tips': []}
            if kind == 'card_removal': item['used'] = False
            raw['shop']['items'] = [item]
            full = inspection_details('inspect_shop', raw)['shop']['items'][0]
            self.assertEqual(full['description'], 'Help.')
            self.assertNotIn('description', inspection_details('get_state', raw)['shop']['items'][0])

    def test_hidden_and_malformed_contents_are_rejected(self):
        for mutate in (lambda r: r.pop('shop'), lambda r: r.update(shop=None),
                       lambda r: r['shop'].update(status='covered'), lambda r: r['shop'].update(view='merchant'),
                       lambda r: r['shop']['items'][0].update(id=True), lambda r: r['shop']['items'][0].update(price=-1),
                       lambda r: r['shop']['items'].append(copy.deepcopy(r['shop']['items'][0])),
                       lambda r: r['shop']['items'][0].pop('card')):
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)):
                inspection_details('get_state', raw)
        raw = state(False)
        self.assertIsNone(inspection_details('get_state', raw)['shop']['items'])
        with self.assertRaises(ValueError): inspection_details('inspect_shop', raw)
        raw['shop'] = dict.fromkeys(('view', 'items', 'open', 'back', 'proceed')) | {'status': 'covered'}
        self.assertEqual(inspection_details('get_state', raw)['shop'], raw['shop'])

    def test_unreadable_price_stays_unknown_without_rejecting_visible_item(self):
        raw = state()
        raw['shop']['items'][0].update(price=None, affordable=None, enabled=False)
        item = inspection_details('get_state', raw)['shop']['items'][0]
        self.assertIsNone(item['price'])
        self.assertIsNone(item['affordable'])
        self.assertFalse(item['enabled'])
        raw['shop']['items'][0]['enabled'] = True
        with self.assertRaises(ValueError): inspection_details('get_state', raw)

    def test_used_removal_is_visible_without_hidden_price(self):
        raw = state()
        raw['shop']['items'] = [{'id': 14, 'kind': 'card_removal', 'position': 'card_removal:0', 'price': None,
            'affordable': None, 'enabled': False, 'name': 'Card Removal Service', 'used': True}]
        self.assertTrue(inspection_details('get_state', raw)['shop']['items'][0]['used'])
        raw['shop']['items'][0]['price'] = 100
        with self.assertRaises(ValueError): inspection_details('get_state', raw)

    def test_blocked_potion_reward_reports_consumed_without_obtaining(self):
        from tests.python.test_rewards import state as reward_state
        raw = reward_state()
        raw['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
        raw['reward_result'] = {'reward_id': 0, 'status': 'not_obtained'}
        result = player_result({'ok': True, 'state': inspection_details('claim_reward', raw)})
        self.assertEqual(result['reward_result'], {'reward_id': 0, 'status': 'not_obtained'})

    def test_potion_visual_cue_and_purchase_failure_are_preserved(self):
        raw = state()
        raw['top_bar']['potion_slots'] = [{'name': 'Foul Potion', 'usable_here': True, 'bouncing': True, 'hidden_effect': 'Secret'}]
        raw['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': []}
        raw['purchase_result'] = {'item_id': 0, 'status': 'failure_space'}
        public = player_result({'ok': True, 'state': inspection_details('buy_item', raw)})
        self.assertEqual(public['purchase_result'], {'item_id': 0, 'status': 'failure_space'})
        self.assertEqual(public['top_bar']['potion_slots'], [{'name': 'Foul Potion', 'usable_here': True, 'bouncing': True}])


class ShopClient:
    def __init__(self): self.raw = state(); self.calls = []

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation in {'buy_item', 'open_shop', 'close_shop'}:
            self.raw.update(snapshot_id='shop-2', transition={'complete': True, 'stop_reason': 'action_completed', 'events': []})
            if operation == 'buy_item':
                self.raw['shop']['items'][0].update(id=15, price=60, on_sale=False)
                self.raw['shop']['items'][0]['card']['name'] = 'New stock'
                self.raw['purchase_result'] = {'item_id': arguments['item_id'], 'status': 'success'}
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class ShopSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_inspection_preserves_permission_and_restock_action_can_chain(self):
        client = ShopClient(); tools = GameTools(client)
        await tools.inspect_shop()
        result = await tools.buy_item({'item_id': 0})
        self.assertNotIn('shop', result)
        self.assertEqual((await tools.inspect_shop())['shop']['items'][0]['id'], 15)
        self.assertEqual(tools.snapshot_id, 'shop-2')
        await tools.buy_item({'item_id': 15})
        self.assertEqual(client.calls[-1][1:], ('shop-2', {'item_id': 15}))

    async def test_bad_purchase_or_page_arguments_consume_permission(self):
        for args in (None, {}, {'item_id': -1}, {'item_id': True}, {'item_id': 1.0}, {'item_id': '0'},
                     {'item_id': 0, 'repeat': True}, [], False):
            tools = GameTools(ShopClient()); await tools.get_observation()
            self.assertEqual((await tools.buy_item(args))['error']['code'], 'invalid_request')
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(len(tools.client.calls), 1)
        for name in ('open_shop', 'close_shop'):
            tools = GameTools(ShopClient()); await tools.get_observation()
            self.assertEqual((await getattr(tools, name)({'ignored': True}))['error']['code'], 'invalid_request')
            self.assertIsNone(tools.snapshot_id)


class ShopStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_routes_item_purchase_and_explicit_page_actions(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER

        class ShopGame(FakeGame):
            def run(self):
                client = ShopClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text()); self.operations.append(request)
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(response)); temporary.replace(target)
                        path.unlink()

        with ShopGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory), '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.call_tool('get_observation', {})
                    for name, args in (('open_shop', {}), ('inspect_shop', {}), ('buy_item', {'item_id': 0}), ('close_shop', {})):
                        result = await session.call_tool(name, args)
                        self.assertNotIn('error', result.structuredContent)
                        self.assertEqual(json.loads(result.content[0].text), result.structuredContent)
            self.assertEqual([r['operation'] for r in game.operations], ['get_state', 'open_shop', 'inspect_shop', 'buy_item', 'close_shop'])
