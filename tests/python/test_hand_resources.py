"""Hand filters retain visible HUD resources; incomplete counters stay unknown."""
import unittest
from sts2_mcp.game_tools import GameTools
from tests.python.test_hand_presets import HandClient


class HandResourceTests(unittest.IsolatedAsyncioTestCase):
    async def test_resources_are_independent_of_card_filter_and_stars_zero_is_visible(self):
        for card_ids in (None, [], [2147483647]):
            client = HandClient()
            client.extra.update(energy=3, max_energy=4, stars=0)
            tools = GameTools(client)
            for preset in ('full', 'default', 'summary'):
                arguments = {'preset': preset}
                if card_ids is not None: arguments['card_ids'] = card_ids
                result = await tools.inspect_hand(arguments)
                self.assertEqual(result['stars'], 0)
                self.assertEqual(result['energy'], '3/4' if preset == 'summary' else 3)
                if preset == 'summary': self.assertNotIn('max_energy', result)
                else: self.assertEqual(result['max_energy'], 4)
                if card_ids is not None: self.assertEqual(result['hand'], [])

    async def test_unreadable_resources_and_incomplete_energy_pair_are_not_filled(self):
        for energy, maximum in ((None, None), (3, None), (None, 4)):
            client = HandClient()
            client.extra.update(energy=energy, max_energy=maximum, stars=None)
            tools = GameTools(client)
            full = await tools.inspect_hand({'preset': 'full', 'card_ids': []})
            self.assertEqual({key: full[key] for key in ('energy', 'max_energy', 'stars')},
                             {'energy': energy, 'max_energy': maximum, 'stars': None})
            default = await tools.inspect_hand({'card_ids': []})
            self.assertEqual(default, {'hand': [], 'hover_tips': [],
                                      **({'energy': energy} if energy is not None else {}),
                                      **({'max_energy': maximum} if maximum is not None else {})})
            self.assertEqual(await tools.inspect_hand({'preset': 'summary', 'card_ids': []}), {'hand': []})

    async def test_bad_resources_fail_before_empty_filter_and_native_errors_stay_errors(self):
        for key, value in (('energy', True), ('max_energy', '4'), ('stars', 1.5)):
            client = HandClient()
            client.extra[key] = value
            result = await GameTools(client).inspect_hand({'preset': 'summary', 'card_ids': []})
            self.assertEqual(result['error']['code'], 'transport_error')
        client = HandClient()
        client.hand_error = 'illegal_action'
        result = await GameTools(client).inspect_hand({'preset': 'summary', 'card_ids': []})
        self.assertEqual(set(result), {'error'})


if __name__ == '__main__':
    unittest.main()
