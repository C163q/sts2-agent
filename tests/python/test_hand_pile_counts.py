"""Visible pile counts survive hand filtering and use the existing null rules."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools


class HandReply:
    def __init__(self):
        self.state = {'snapshot_id': 'hand-state', 'scene': 'combat', 'screen': {'status': 'visible'},
            'hand': [], 'energy': 3, 'max_energy': 3, 'stars': None,
            'draw_count': 7, 'discard_count': 0, 'exhaust_count': None}
    def call(self, operation, expected_state=None, **kwargs):
        if operation != 'inspect_hand': raise AssertionError(operation)
        return {'ok': True, 'state': copy.deepcopy(self.state)}


class HandPileCountTests(unittest.IsolatedAsyncioTestCase):
    async def test_counts_keep_zero_and_follow_null_rules_independently_of_card_filter(self):
        for preset in ('full', 'default', 'summary'):
            for ids in (None, [], [99]):
                with self.subTest(preset=preset, ids=ids):
                    client = HandReply()
                    original = copy.deepcopy(client.state)
                    result = await GameTools(client).inspect_hand({'preset': preset, 'card_ids': ids})
                    expected = {'draw_count': 7, 'discard_count': 0}
                    if preset == 'full': expected['exhaust_count'] = None
                    self.assertEqual({k: v for k, v in result.items() if k.endswith('_count')}, expected)
                    self.assertEqual(result['hand'], [])
                    if preset == 'summary': self.assertEqual(result['energy'], '3/3')
                    if ids: self.assertEqual(result['errors'], [{'code': 'cards_not_in_hand', 'card_ids': [99]}])
                    self.assertEqual(client.state, original)

    async def test_empty_filter_cannot_hide_malformed_count(self):
        for name in ('draw_count', 'discard_count', 'exhaust_count'):
            for bad in (False, '0', [], 1.5):
                with self.subTest(name=name, bad=bad):
                    client = HandReply()
                    client.state[name] = bad
                    tools = GameTools(client)
                    tools.snapshot_id = 'old'
                    result = await tools.inspect_hand({'preset': 'summary', 'card_ids': []})
                    self.assertEqual(result['error']['code'], 'transport_error')
                    self.assertIsNone(tools.snapshot_id)

    async def test_old_reply_without_new_counts_remains_accepted(self):
        client = HandReply()
        for name in ('draw_count', 'discard_count', 'exhaust_count'): client.state.pop(name)
        result = await GameTools(client).inspect_hand({'preset': 'full'})
        self.assertNotIn('error', result)
        self.assertFalse(any(key.endswith('_count') for key in result))
