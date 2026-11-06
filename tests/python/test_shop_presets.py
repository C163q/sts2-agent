"""Public shop presets share static observations and validate before local filtering."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_shop import state
from tests.python.test_tool_contracts import ContractReply


def details():
    raw = state()
    raw['schema_version'] = 43
    raw['top_bar'].update(gold=100, deck_count=10, relic_count=1)
    raw['shop']['items'] += [
        {'id': 7, 'kind': 'relic', 'position': 'relic:0', 'price': 80, 'affordable': True, 'enabled': True,
         'name': 'Vajra', 'description': 'Gain 1 Strength.', 'hover_tips': [{'title': 'Strength', 'description': 'Attacks deal more damage.'}]},
        {'id': 8, 'kind': 'potion', 'position': 'potion:0', 'price': 20, 'affordable': True, 'enabled': True,
         'name': 'Block Potion', 'description': 'Gain 12 Block.', 'hover_tips': []},
        {'id': 9, 'kind': 'card_removal', 'position': 'card_removal:0', 'price': 75, 'affordable': True, 'enabled': True,
         'name': 'Card Removal Service', 'used': False, 'description': 'Remove a card.', 'hover_tips': []}]
    return raw


class ShopPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_shares_observation_shop_and_top_bar(self):
        tools = GameTools(ContractReply(details()))
        summary = await tools.inspect_shop({'preset': 'summary'})
        self.assertNotIn('error', summary)
        observed = await tools.get_observation({'preset': 'summary'})
        self.assertEqual(summary['shop'], observed['shop'])
        self.assertEqual(summary['top_bar'], observed['top_bar'])
        self.assertEqual(summary['shop']['items'][0]['card'], {'name': 'Strike+', 'type': 'Attack', 'energy_cost': '1', 'star_cost': '0'})
        for item in summary['shop']['items']:
            self.assertNotIn('description', item.get('card') or item)
            self.assertNotIn('hover_tips', item.get('card') or item)

    async def test_full_and_default_add_compact_top_bar_without_native_output_arguments(self):
        for preset in ('full', 'default'):
            client = ContractReply(details()); tools = GameTools(client)
            result = await tools.inspect_shop({'preset': preset, 'item_ids': None, 'kinds': None})
            self.assertNotIn('error', result)
            self.assertEqual(result['top_bar'], {'gold': 100, 'deck_count': 10, 'relic_count': 1,
                'potion_slots': [None, {'name': 'Block Potion'}]})
            self.assertEqual(result['shop']['items'][0]['card']['description'], 'Deal 9 damage.')
            self.assertEqual(client.calls, [{'operation': 'inspect_shop', 'expected_state': None, 'arguments': None}])

    async def test_filters_keep_native_order_and_missing_ids_use_complete_inventory(self):
        for preset in ('full', 'default', 'summary'):
            for ids, kinds, expected, missing in [
                (None, None, [0, 7, 8, 9], []), ([], None, [], []), (None, [], [], []),
                ([8, 7, 8], None, [7, 8], []), (None, ['potion', 'relic'], [7, 8], []),
                ([8, 7, 404, 405, 404], ['card'], [], [404, 405]),
                ([8, 7, 404], ['relic'], [7], [404]), ([9], ['card_removal'], [9], [])]:
                with self.subTest(preset=preset, ids=ids, kinds=kinds):
                    result = await GameTools(ContractReply(details())).inspect_shop({'preset': preset, 'item_ids': ids, 'kinds': kinds})
                    self.assertNotIn('error', result)
                    self.assertEqual([item['id'] for item in result['shop']['items']], expected)
                    self.assertEqual(result.get('errors', []), [{'code': 'item_ids_not_found', 'item_ids': missing}] if missing else [])
                    self.assertEqual(result['shop']['back'], {'enabled': True})
                    self.assertEqual(result['top_bar']['gold'], 100)

    async def test_local_parameter_errors_preserve_permission_and_send_nothing(self):
        for arguments in ({'kinds': ['cards']}, {'kinds': [0]}, {'kinds': 'card'}, {'item_ids': [True]},
                          {'item_ids': [-1]}, {'item_ids': [2147483648]}, {'item_ids': ['0']}, {'extra': 1}, {'preset': 'bad'}):
            with self.subTest(arguments=arguments):
                client = ContractReply(details()); tools = GameTools(client)
                await tools.get_observation()
                result = await tools.inspect_shop(arguments)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(tools.snapshot_id, 'shop-1')
                self.assertEqual(len(client.calls), 1)

    async def test_context_and_full_data_are_checked_even_with_empty_filters(self):
        changes = [lambda r: r.update(screen={'status': 'covered'}),
            lambda r: r.update(screen={'status': 'covered', 'view': 'map'}),
            lambda r: r.update(screen={'status': 'visible', 'view': 'deck'}),
            lambda r: r.update(screen={'status': 'hidden'}),
            lambda r: r.update(scene='event'), lambda r: r['shop']['items'][0].update(price=-1),
            lambda r: r['shop']['items'][1].update(description=None),
            lambda r: r.pop('top_bar'), lambda r: r['top_bar'].update(gold=-1),
            lambda r: r['top_bar'].update(potion_slots=[{}])]
        for preset in ('full', 'summary'):
            for mutate in changes:
                raw = details(); mutate(raw); tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'old'
                result = await tools.inspect_shop({'preset': preset, 'item_ids': [], 'kinds': []})
                self.assertEqual(result['error']['code'], 'transport_error', raw)
                self.assertIsNone(tools.snapshot_id)

    async def test_unavailable_hover_help_keeps_static_card_body_and_tracks_ids(self):
        raw = details()
        raw['shop']['items'][0]['card']['hover_tips'] = None
        raw['shop']['items'][1].update(description=None, hover_tips=[])
        raw['unavailable_hover_sources'] = ['shop.items.0', 'shop.items.7']
        for preset in ('full', 'default', 'summary'):
            for kinds in (None, ['card'], ['relic'], []):
                with self.subTest(preset=preset, kinds=kinds):
                    result = await GameTools(ContractReply(raw)).inspect_shop({'preset': preset, 'kinds': kinds})
                    self.assertNotIn('error', result)
                    sources = result.get('notes', {}).get('hover_tips_unavailable', {}).get('sources')
                    expected = None if preset == 'summary' or kinds == [] else (
                        ['shop.items.0', 'shop.items.7'] if kinds is None else ['shop.items.0'] if kinds == ['card'] else ['shop.items.7'])
                    self.assertEqual(sources, expected)
                    for item in result['shop']['items']:
                        if item['id'] == 0 and preset != 'summary':
                            self.assertEqual(item['card']['description'], 'Deal 9 damage.')
                            self.assertEqual('hover_tips' in item['card'], preset == 'full')
                        if item['id'] == 7: self.assertEqual('description' in item, preset == 'full')

    async def test_used_removal_and_partial_or_hidden_top_bar_preserve_meaning(self):
        raw = details(); raw['shop']['items'][-1].update(used=True, price=None, affordable=None, enabled=False)
        raw['shop']['items'][-1].pop('description'); raw['shop']['items'][-1].pop('hover_tips')
        for preset in ('full', 'default', 'summary'):
            for hidden in (False, True):
                data = copy.deepcopy(raw)
                if hidden: data['top_bar'] = None
                else: data['top_bar']['gold'] = None
                result = await GameTools(ContractReply(data)).inspect_shop({'preset': preset})
                self.assertNotIn('error', result)
                self.assertTrue(result['shop']['items'][-1]['used'])
                self.assertNotIn('description', result['shop']['items'][-1])
                if hidden: self.assertEqual('top_bar' in result, preset == 'full')
                else: self.assertEqual('gold' in result['top_bar'], preset == 'full')

    async def test_read_rejection_retains_existing_permission_without_creating_one(self):
        client = ContractReply(details(), {'code': 'illegal_action', 'public_message': 'Open the shop with open_shop.'})
        tools = GameTools(client)
        result = await tools.inspect_shop({'preset': 'summary', 'kinds': ['card']})
        self.assertEqual(result['error']['recovery'], 'get_observation')
        self.assertIsNone(tools.snapshot_id)
        tools.snapshot_id = 'old'
        result = await tools.inspect_shop({'preset': 'summary', 'item_ids': []})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertEqual(tools.snapshot_id, 'old')
