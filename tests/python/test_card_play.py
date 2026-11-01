import copy
import asyncio
import threading
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.output.player_output import player_result
from tests.python.test_selection import state as selection_state


def combat():
    data = selection_state()
    data.update(selection=None, available_actions=['end_turn', 'play_card'], screen={'status': 'visible'})
    return data


def targets():
    return {'snapshot_id': 'fixture-1', 'card': {'id': 7, 'name': 'Strike'}, 'playable': True,
            'target_type': 'any_enemy', 'requires_target': True,
            'targets': [{'id': 3, 'kind': 'enemy', 'name': 'Slime'}], 'reason': None}


class CardPlayBoundaryTests(unittest.TestCase):
    def test_two_tools_and_strict_schemas(self):
        definitions = {tool.name: tool for tool in tool_definitions()}
        self.assertIn('play_card', definitions)
        self.assertIn('inspect_targets', definitions)
        self.assertEqual(len(definitions), 42)
        self.assertTrue(definitions['inspect_targets'].annotations.readOnlyHint)
        self.assertFalse(definitions['play_card'].annotations.idempotentHint)
        schema = definitions['play_card'].inputSchema
        self.assertEqual(schema['required'], ['card_id'])
        self.assertFalse(schema['additionalProperties'])
        self.assertIn('target_id', schema['properties'])

    def test_targets_filter_nested_internal_state(self):
        raw = targets()
        raw['rng_state'] = 'secret'
        raw['card']['description'] = 'unrequested'
        raw['targets'][0]['next_move'] = 'secret'
        result = player_result({'ok': True, 'state': inspection_details('inspect_targets', raw, {'card_id': 7})})
        self.assertEqual(result, {key: value for key, value in targets().items() if key != 'snapshot_id'})

    def test_targets_reject_malformed_and_inconsistent_payloads(self):
        mutations = [lambda d: d.pop('targets'), lambda d: d.update(playable=1),
                     lambda d: d.update(requires_target=False), lambda d: d.update(target_type='unknown'),
                     lambda d: d.update(targets=[]), lambda d: d['targets'][0].update(id=True),
                     lambda d: d['targets'][0].pop('name'), lambda d: d.update(reason='Blocked'),
                     lambda d: d['targets'].append(copy.deepcopy(d['targets'][0])),
                     lambda d: d['card'].update(id=8)]
        for mutate in mutations:
            raw = targets()
            mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details('inspect_targets', raw, {'card_id': 7})

    def test_untargeted_card_can_be_playable_with_empty_range(self):
        raw = targets()
        raw.update(target_type='all_enemies', requires_target=False, targets=[])
        result = inspection_details('inspect_targets', raw, {'card_id': 7})
        self.assertTrue(result['playable'])
        raw.update(playable=False, reason='Not enough Energy.')
        self.assertFalse(inspection_details('inspect_targets', raw, {'card_id': 7})['playable'])

    def test_canceled_action_returns_events_without_authorizing_more_play(self):
        raw = combat()
        raw['transition'] = {'stop_reason': 'action_canceled', 'complete': True, 'events': []}
        result = inspection_details('play_card', raw)
        self.assertEqual(result['transition']['stop_reason'], 'action_canceled')
        self.assertEqual(result['available_actions'], [])

    def test_choice_or_incomplete_transition_never_offers_play_card(self):
        for reason, complete in [('choice_required', True), ('timeout', False)]:
            raw = selection_state()
            raw['available_actions'].extend(['play_card', 'end_turn'])
            raw['transition'] = {'stop_reason': reason, 'complete': complete, 'events': []}
            result = inspection_details('play_card', raw)
            self.assertNotIn('play_card', result['available_actions'])
            self.assertNotIn('end_turn', result['available_actions'])


class Client:
    def __init__(self):
        self.calls = []
        self.malformed = False

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        raw = targets() if operation == 'inspect_targets' else combat()
        if self.malformed:
            raw.pop('targets', None)
        if operation == 'play_card':
            raw['transition'] = {'stop_reason': 'player_ready', 'complete': True, 'events': []}
        return {'ok': True, 'state': raw}


class CardPlayPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_query_is_serialized_after_an_inflight_observation(self):
        started, release = threading.Event(), threading.Event()

        class SlowClient(Client):
            def call(self, operation, expected_state=None, arguments=None):
                started.set()
                if not release.wait(3):
                    raise TimeoutError('Test observation was not released')
                return super().call(operation, expected_state, arguments)

        tools = GameTools(SlowClient())
        observation = asyncio.create_task(tools.get_observation())
        while not started.is_set():
            await asyncio.sleep(.001)
        invalid = asyncio.create_task(tools.inspect_targets({'card_id': True}))
        await asyncio.sleep(0)
        release.set()
        await observation
        self.assertEqual((await invalid)['error']['code'], 'invalid_request')
        self.assertIsNone(tools.snapshot_id)

    async def test_query_provides_state_for_subsequent_play(self):
        client = Client()
        tools = GameTools(client)
        self.assertTrue(hasattr(tools, 'inspect_targets'), 'Target query is missing')
        self.assertNotIn('error', await tools.inspect_targets({'card_id': 7}))
        self.assertEqual(tools.snapshot_id, 'fixture-1')
        await tools.inspect_targets({'card_id': 7})
        self.assertEqual(tools.snapshot_id, 'fixture-1')
        played = await tools.play_card({'card_id': 7, 'target_id': 3})
        self.assertNotIn('error', played)
        self.assertEqual(client.calls[-1], ('play_card', 'fixture-1', {'card_id': 7, 'target_id': 3}))
        self.assertEqual(tools.snapshot_id, 'fixture-1')
        self.assertNotIn('error', await tools.play_card({'card_id': 7, 'target_id': 3}))

    async def test_invalid_play_parameters_consume_permission_without_input(self):
        client = Client()
        tools = GameTools(client)
        self.assertTrue(hasattr(tools, 'play_card'), 'Play action is missing')
        for args in [None, {}, {'card_id': True}, {'card_id': -1}, {'card_id': 2**31},
                     {'card_id': 7, 'target_id': None}, {'card_id': 7, 'target_id': True},
                     {'card_id': 7, 'target_id': -1}, {'card_id': 7, 'target_id': 2**32},
                     {'card_id': 7, 'choose_cards': [1]}]:
            await tools.get_observation()
            result = await tools.play_card(args)
            self.assertEqual(result['error']['code'], 'invalid_request', args)
            self.assertIsNone(tools.snapshot_id)
        self.assertTrue(all(call[0] == 'get_state' for call in client.calls))

    async def test_query_rejects_extra_parameters_and_malformed_output(self):
        client = Client()
        tools = GameTools(client)
        self.assertTrue(hasattr(tools, 'inspect_targets'), 'Target query is missing')
        result = await tools.inspect_targets({'card_id': 7, 'target_id': 3})
        self.assertEqual(result['error']['code'], 'invalid_request')
        self.assertEqual(client.calls, [])
        await tools.get_observation()
        client.malformed = True
        result = await tools.inspect_targets({'card_id': 7})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)


if __name__ == '__main__':
    unittest.main()
