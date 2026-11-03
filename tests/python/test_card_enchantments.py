"""Keep visible enchantment metadata across basic/full/summary without exposing effects."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_hand_presets import HandClient


class EnchantmentClient(HandClient):
    def __init__(self):
        super().__init__()
        self.hand[0]['enchantment'] = {'name': 'Sharp', 'amount': 3, 'dimmed': False}
        self.hand[1]['enchantment'] = {'name': 'Swift', 'amount': 2, 'dimmed': True}
        self.hand[2]['enchantment'] = {'name': 'Clone', 'dimmed': False}

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        response = super().call(operation, expected_state, arguments)
        if operation == 'get_state' and response['ok']:
            response['state']['player']['hand'] = copy.deepcopy(self.hand)
        return response


class CardEnchantmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_affliction_coexists_with_enchantment_and_nulls_follow_preset(self):
        client = EnchantmentClient()
        client.hand[0]['affliction'] = {'name': 'Bound', 'amount': 19, 'description': 'Full help only.'}
        client.hand[1]['affliction'] = {'name': 'Smog'}
        client.hand[3].update(enchantment=None, affliction=None)
        tools = GameTools(client)
        for preset in ('full', 'default', 'summary'):
            for result in (await tools.get_observation({'preset': preset}),
                           await tools.inspect_hand({'preset': preset})):
                cards = result.get('hand', (result.get('player') or {}).get('hand'))
                self.assertEqual(cards[0]['affliction'], {'name': 'Bound'})
                self.assertEqual(cards[1]['affliction'], {'name': 'Smog'})
                self.assertEqual(cards[0]['enchantment'], {'name': 'Sharp', 'amount': 3, 'dimmed': False})
                for key in ('affliction', 'enchantment'):
                    if preset == 'full':
                        self.assertIn(key, cards[3])
                        self.assertIsNone(cards[3][key])
                    else:
                        self.assertNotIn(key, cards[3])

    async def test_invalid_affliction_is_rejected_before_filtering(self):
        for value in ([], 'Bound', {'name': 1}):
            client = EnchantmentClient()
            client.hand[0]['affliction'] = value
            tools = GameTools(client)
            result = await tools.inspect_hand({'preset': 'summary', 'card_ids': []})
            self.assertEqual(result['error']['code'], 'transport_error')
            self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_basic_full_and_summary_keep_the_same_visible_metadata(self):
        client = EnchantmentClient()
        tools = GameTools(client)
        basic = (await tools.get_observation())['player']['hand']
        full = (await tools.inspect_hand())['hand']
        summary = (await tools.inspect_hand({'preset': 'summary'}))['hand']
        expected = [{'name': 'Sharp', 'amount': 3, 'dimmed': False},
                    {'name': 'Swift', 'amount': 2, 'dimmed': True}, {'name': 'Clone', 'dimmed': False}]
        for cards in (basic, full, summary):
            self.assertEqual([card.get('enchantment') for card in cards[:3]], expected)
            self.assertNotIn('enchantment', cards[3])
        self.assertNotIn('description', basic[0])
        self.assertNotIn('description', summary[0])
        self.assertIn('description', full[0])

    async def test_unshown_count_is_not_defaulted_and_nested_effects_are_not_forwarded(self):
        client = EnchantmentClient()
        client.hand[2]['enchantment'].update(description='Not basic information.', hidden_amount=7, future='hidden')
        original = copy.deepcopy(client.hand)
        tools = GameTools(client)
        for result in ((await tools.get_observation())['player']['hand'],
                       (await tools.inspect_hand())['hand'],
                       (await tools.inspect_hand({'preset': 'summary'}))['hand']):
            self.assertEqual(result[2]['enchantment'], {'name': 'Clone', 'dimmed': False})
        self.assertEqual(client.hand, original)

    async def test_filtered_summary_keeps_enchantment_and_merged_error(self):
        result = await GameTools(EnchantmentClient()).inspect_hand({'preset': 'summary', 'card_ids': [9, 80]})
        self.assertEqual(result['hand'][0]['enchantment'], {'name': 'Sharp', 'amount': 3, 'dimmed': False})
        self.assertEqual(result['errors'], [{'code': 'cards_not_in_hand', 'card_ids': [80]}])

    async def test_bad_nested_values_fail_even_when_card_would_be_filtered_out(self):
        for field, value in [('name', 4), ('amount', True), ('amount', '3'), ('dimmed', 1), ('dimmed', 'yes')]:
            client = EnchantmentClient()
            client.hand[0]['enchantment'][field] = value
            tools = GameTools(client)
            with self.subTest(field=field, value=value):
                for result in (await tools.get_observation(), await tools.inspect_hand({'card_ids': [4]})):
                    self.assertEqual(result['error']['code'], 'transport_error')
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_absent_enchantment_is_compatible_with_previous_mod_output(self):
        tools = GameTools(HandClient())
        for result in (await tools.inspect_hand(), await tools.inspect_hand({'preset': 'summary'})):
            self.assertTrue(all('enchantment' not in card for card in result['hand']))


if __name__ == '__main__':
    unittest.main()
