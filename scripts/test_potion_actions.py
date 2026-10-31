import asyncio
import copy
import threading
import unittest

from game_tools import GameTools
from inspection_details import inspection_details
from mcp_catalog import tool_definitions
from player_output import player_result
from test_card_play import combat


def potion_targets():
    return {'snapshot_id': 'fixture-1', 'potion': {'slot_index': 0, 'name': 'Fruit Juice'},
            'usable': True, 'discardable': True, 'target_type': 'any_player', 'requires_target': False,
            'targets': [{'id': 'self', 'kind': 'player', 'name': 'The Ironclad'}], 'reason': None}


class PotionBoundaryTests(unittest.TestCase):
    def test_shared_query_and_two_action_schemas(self):
        tools = {tool.name: tool for tool in tool_definitions()}
        self.assertIn('use_potion', tools)
        self.assertIn('discard_potion', tools)
        self.assertEqual(len(tools), 31)
        self.assertTrue(tools['inspect_targets'].annotations.readOnlyHint)
        for name in ('use_potion', 'discard_potion'):
            self.assertFalse(tools[name].annotations.idempotentHint)
            self.assertEqual(tools[name].inputSchema['required'], ['potion_slot'])
            self.assertFalse(tools[name].inputSchema['additionalProperties'])
        self.assertEqual(len(tools['inspect_targets'].inputSchema['oneOf']), 2)

    def test_potion_query_filters_nested_fields(self):
        raw = potion_targets()
        raw['future_cards'] = ['secret']
        raw['potion']['description'] = 'unrequested'
        raw['targets'][0]['net_id'] = 'secret'
        result = player_result({'ok': True, 'state': inspection_details('inspect_targets', raw, {'potion_slot': 0})})
        self.assertEqual(result, {k: v for k, v in potion_targets().items() if k != 'snapshot_id'})

    def test_automatic_unusable_potion_can_still_be_discarded(self):
        raw = potion_targets()
        raw.update(usable=False, reason='This potion is used automatically.', target_type='self')
        result = inspection_details('inspect_targets', raw, {'potion_slot': 0})
        self.assertFalse(result['usable'])
        self.assertTrue(result['discardable'])

    def test_target_ids_and_merchant_shape(self):
        raw = potion_targets()
        raw.update(target_type='any_enemy', requires_target=True,
                   targets=[{'id': 2, 'kind': 'enemy', 'name': 'Slime'}])
        self.assertEqual(inspection_details('inspect_targets', raw, {'potion_slot': 0})['targets'][0]['id'], 2)
        raw.update(target_type='targeted_no_creature',
                   targets=[{'id': 'merchant', 'kind': 'merchant', 'name': 'Merchant'}])
        self.assertEqual(inspection_details('inspect_targets', raw, {'potion_slot': 0})['targets'][0]['id'], 'merchant')

    def test_invalid_query_results_are_rejected(self):
        mutations = [lambda d: d.pop('discardable'), lambda d: d.update(usable=1),
                     lambda d: d.update(reason='Blocked'), lambda d: d.update(usable=False),
                     lambda d: d['potion'].update(slot_index=1), lambda d: d['potion'].update(slot_index=True),
                     lambda d: d.update(target_type='unknown'), lambda d: d.update(requires_target=True),
                     lambda d: d['targets'][0].update(id=True), lambda d: d['targets'][0].update(id='hidden'),
                     lambda d: d['targets'][0].update(id=-1), lambda d: d['targets'][0].update(id=2**32),
                     lambda d: d['targets'].append(copy.deepcopy(d['targets'][0])),
                     lambda d: d['targets'][0].update(kind='enemy'), lambda d: d.update(discardable=False)]
        for mutate in mutations:
            raw = potion_targets()
            mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details('inspect_targets', raw, {'potion_slot': 0})

    def test_completed_noncombat_action_preserves_available_action_list(self):
        raw = combat()
        raw.update(scene='loading_or_noncombat', player=None, enemies=None, turn=None, buttons=None,
                   top_bar={'hp': 80, 'max_hp': 85, 'potion_slots': [None]},
                   available_actions=['use_potion', 'discard_potion'])
        raw['transition'] = {'stop_reason': 'action_completed', 'complete': True, 'events': [
            {'sequence': 1, 'type': 'potion_used', 'potion': {'slot_index': 0, 'name': 'Fruit Juice'}}]}
        result = inspection_details('use_potion', raw)
        self.assertEqual(result['top_bar']['max_hp'], 85)
        self.assertEqual(result['available_actions'], ['use_potion', 'discard_potion'])
        self.assertEqual(result['transition']['events'][0]['potion']['name'], 'Fruit Juice')

    def test_potion_source_and_discard_event_filter_internal_fields(self):
        raw = combat()
        raw['transition'] = {'stop_reason': 'player_ready', 'complete': True, 'events': [
            {'sequence': 1, 'type': 'potion_discarded',
             'potion': {'slot_index': 1, 'name': 'Fire Potion', 'model_id': 'secret'}},
            {'sequence': 2, 'type': 'damage', 'target': {'id': 2, 'kind': 'enemy', 'name': 'Slime'},
             'hp_loss': 20, 'blocked': 0, 'source': {'kind': 'potion', 'name': 'Fire Potion'}}]}
        result = inspection_details('discard_potion', raw)
        self.assertNotIn('model_id', result['transition']['events'][0]['potion'])
        raw['transition']['events'][0]['potion']['slot_index'] = -1
        with self.assertRaises(ValueError):
            inspection_details('discard_potion', raw)


class Client:
    def __init__(self):
        self.calls = []
        self.malformed = False

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        raw = potion_targets() if operation == 'inspect_targets' else combat()
        if self.malformed:
            raw.pop('targets', None)
        if operation in {'use_potion', 'discard_potion'}:
            raw['transition'] = {'stop_reason': 'player_ready', 'complete': True, 'events': []}
        return {'ok': True, 'state': raw}


class PotionPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_query_permission_and_successful_action_replacement(self):
        tools = GameTools(Client())
        self.assertTrue(hasattr(tools, 'use_potion'))
        self.assertTrue(hasattr(tools, 'discard_potion'))
        self.assertNotIn('error', await tools.inspect_targets({'potion_slot': 0}))
        self.assertIsNone(tools.snapshot_id)
        for name in ('use_potion', 'discard_potion'):
            await tools.get_observation()
            await tools.inspect_targets({'potion_slot': 0})
            self.assertEqual(tools.snapshot_id, 'fixture-1')
            result = await getattr(tools, name)({'potion_slot': 0})
            self.assertNotIn('error', result)
            self.assertEqual(tools.client.calls[-1], (name, 'fixture-1', {'potion_slot': 0}))
            self.assertNotIn('error', await getattr(tools, name)({'potion_slot': 0}))

    async def test_invalid_arguments_never_reach_game_and_clear_permission(self):
        tools = GameTools(Client())
        self.assertTrue(hasattr(tools, 'use_potion'))
        for name in ('inspect_targets', 'use_potion', 'discard_potion'):
            invalid = [None, {}, {'potion_slot': True}, {'potion_slot': -1}, {'potion_slot': 2**31},
                       {'potion_slot': '0'}, {'potion_slot': 0, 'card_id': 1}, {'potion_slot': 0, 'extra': 1}]
            invalid += [{'potion_slot': 0, 'target_id': t} for t in (None, True, -1, 2**32, 1.0, 'self', 'enemy')]
            if name != 'use_potion':
                invalid += [{'potion_slot': 0, 'target_id': 1}, {'potion_slot': 0, 'target_id': 'merchant'}]
            for args in invalid:
                await tools.get_observation()
                before = len(tools.client.calls)
                result = await getattr(tools, name)(args)
                self.assertEqual(result['error']['code'], 'invalid_request', (name, args))
                self.assertEqual(len(tools.client.calls), before)
                self.assertIsNone(tools.snapshot_id)

    async def test_merchant_target_forwarded_and_corrupt_output_drops_permission(self):
        tools = GameTools(Client())
        self.assertTrue(hasattr(tools, 'use_potion'))
        await tools.get_observation()
        result = await tools.use_potion({'potion_slot': 0, 'target_id': 'merchant'})
        self.assertNotIn('error', result)
        self.assertEqual(tools.client.calls[-1][2]['target_id'], 'merchant')
        await tools.get_observation()
        tools.client.malformed = True
        result = await tools.inspect_targets({'potion_slot': 0})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)


if __name__ == '__main__':
    unittest.main()
