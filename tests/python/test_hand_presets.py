"""Exercise hand projections through validated game responses and real MCP stdio."""
import asyncio
import copy
import json
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_server import tool_result
from sts2_mcp.output.player_output import player_result
from tests.python.test_action_observations import Client as ActionClient
from tests.python.test_mcp_server import FakeGame, SERVER
from sts2_mcp.roundtrip_client import Client


def hand():
    block = {'title': 'Block', 'description': 'Until next turn, prevents damage.'}
    return [
        {'id': 9, 'name': 'Defend+', 'type': 'Skill', 'rarity': 'basic', 'visual_card_pool': 'ironclad',
         'energy_cost': '0', 'star_cost': None, 'energy_cost_color': 'green',
         'unplayable_markers': [], 'outline': 'cyan', 'description': 'Gain 8 Block.', 'hover_tips': [block]},
        {'id': 2, 'name': 'Defend', 'type': 'Skill', 'rarity': 'basic', 'visual_card_pool': 'ironclad',
         'energy_cost': '1', 'star_cost': None, 'unplayable_markers': ['energy'], 'outline': 'none',
         'description': 'Gain 5 Block.', 'hover_tips': [block]},
        {'id': 4, 'name': 'Star Card', 'type': 'Attack', 'rarity': 'rare', 'visual_card_pool': 'regent',
         'energy_cost': 'X', 'star_cost': '?', 'star_cost_color': 'red',
         'unplayable_markers': ['star'], 'outline': 'red', 'description': 'An effect.',
         'hover_tips': [{'title': 'Star', 'description': 'A visible resource.'}]},
        {'id': 7, 'name': 'Unknown', 'type': None, 'rarity': None, 'visual_card_pool': None,
         'energy_cost': None, 'star_cost': None, 'unplayable_markers': [], 'outline': 'none',
         'description': None, 'hover_tips': None},
    ]


class HandClient(ActionClient):
    def __init__(self):
        super().__init__()
        self.hand = hand()
        self.extra = {}
        self.hand_error = None

    def call(self, operation, expected_state=None, arguments=None):
        if operation != 'inspect_hand':
            return super().call(operation, expected_state, arguments)
        self.calls.append((operation, expected_state, arguments))
        if self.hand_error:
            return {'ok': False, 'error': {'code': self.hand_error}}
        return {'ok': True, 'state': {'snapshot_id': f'state-{self.revision}',
                                     'hand': copy.deepcopy(self.hand), **self.extra}}


class HandPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_full_is_compatible_and_does_not_modify_response(self):
        client = HandClient()
        original = copy.deepcopy(client.hand)
        tools = GameTools(client)
        expected = player_result({'ok': True, 'state': {'hand': original}}, operation='inspect_hand')
        for args in ({'preset': 'full'},):
            self.assertEqual(await tools.inspect_hand(args), expected)
        self.assertEqual(client.hand, original)
        self.assertTrue(all(c == ('inspect_hand', None, None) for c in client.calls))

    async def test_summary_retains_visible_costs_and_markers_without_effects_or_hidden_attributes(self):
        tools = GameTools(HandClient())
        result = await tools.inspect_hand({'preset': 'summary'})
        self.assertEqual(result, {'hand': [
            {'id': 9, 'name': 'Defend+', 'type': 'Skill', 'energy_cost': '0', 'energy_cost_color': 'green',
             'unplayable_markers': [], 'outline': 'cyan'},
            {'id': 2, 'name': 'Defend', 'type': 'Skill', 'energy_cost': '1',
             'unplayable_markers': ['energy'], 'outline': 'none'},
            {'id': 4, 'name': 'Star Card', 'type': 'Attack', 'energy_cost': 'X', 'star_cost': '?',
             'star_cost_color': 'red', 'unplayable_markers': ['star'], 'outline': 'red'},
            {'id': 7, 'name': 'Unknown', 'type': None, 'energy_cost': None,
             'unplayable_markers': [], 'outline': 'none'},
        ]})

    async def test_filter_preserves_hand_order_deduplicates_and_clips_shared_tip_links(self):
        client = HandClient()
        result = await GameTools(client).inspect_hand({'card_ids': [4, 2, 2]})
        self.assertEqual([c['id'] for c in result['hand']], [2, 4])
        self.assertEqual(result['hover_tips'], [
            {'title': 'Block', 'description': 'Until next turn, prevents damage.', 'card_ids': [2]},
            {'title': 'Star', 'description': 'A visible resource.', 'card_ids': [4]},
        ])
        self.assertEqual([c['id'] for c in client.hand], [9, 2, 4, 7])
        self.assertIn('card_values', result['notes'])

    async def test_mixed_and_all_missing_ids_report_once_in_request_order(self):
        for preset in ('full', 'summary'):
            with self.subTest(preset=preset):
                tools = GameTools(HandClient())
                result = await tools.inspect_hand({'preset': preset, 'card_ids': [80, 9, 70, 80]})
                self.assertEqual([c['id'] for c in result['hand']], [9])
                self.assertEqual(result['errors'], [{'code': 'cards_not_in_hand', 'card_ids': [80, 70]}])
                self.assertFalse(tool_result(result).isError)
                missing = await tools.inspect_hand({'preset': preset, 'card_ids': [80, 80]})
                self.assertEqual(missing['hand'], [])
                self.assertEqual(missing['errors'], [{'code': 'cards_not_in_hand', 'card_ids': [80]}])
                self.assertNotIn('notes', missing)
                self.assertFalse(tool_result(missing).isError)
                self.assertNotIn('error', await tools.end_turn())

    async def test_empty_filter_and_empty_hand_read_the_game_and_keep_no_unrelated_tips(self):
        for preset in ('full', 'summary'):
            client = HandClient()
            tools = GameTools(client)
            result = await tools.inspect_hand({'preset': preset, 'card_ids': []})
            self.assertEqual(result, {'hand': [], **({'hover_tips': []} if preset == 'full' else {})})
            self.assertEqual(client.calls, [('inspect_hand', None, None)])
            client.hand = []
            self.assertEqual(await tools.inspect_hand({'preset': preset}), result)

    async def test_summary_and_empty_filter_preserve_pending_selection_navigation_note(self):
        client = HandClient()
        client.extra['selection_view'] = 'battlefield'
        result = await GameTools(client).inspect_hand({'preset': 'summary', 'card_ids': []})
        self.assertEqual(set(result['notes']), {'selection'})
        self.assertEqual(result['hand'], [])

    async def test_bad_arguments_do_not_request_game_or_discard_previous_permission(self):
        client = HandClient()
        tools = GameTools(client)
        await tools.get_observation()
        for args in ([], False, 0, '', {'preset': None}, {'preset': []}, {'preset': 'FULL'},
                     {'filter': [9]}, {'card_ids': None}, {'card_ids': 9}, {'card_ids': '9'},
                     {'card_ids': [True]}, {'card_ids': [1.0]}, {'card_ids': [-1]},
                     {'card_ids': [2147483648]}, {'card_ids': ['9']}, {'extra': True}):
            with self.subTest(args=args):
                result = await tools.inspect_hand(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.end_turn())

    async def test_full_native_payload_is_validated_before_filtering_and_bad_data_clears_permission(self):
        for options in ({'preset': 'summary', 'card_ids': [9]}, {'card_ids': []}):
            client = HandClient()
            tools = GameTools(client)
            await tools.get_observation()
            client.hand[-1]['energy_cost'] = True
            self.assertEqual((await tools.inspect_hand(options))['error']['code'], 'transport_error')
            self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_successful_filtered_inspection_refreshes_native_token_and_external_changes_still_expire_it(self):
        client = HandClient()
        tools = GameTools(client)
        await tools.inspect_hand({'preset': 'summary', 'card_ids': [9, 80]})
        self.assertNotIn('error', await tools.end_turn())
        self.assertEqual(client.calls[-1], ('end_turn', 'state-1', None))
        await tools.inspect_hand({'card_ids': [9]})
        client.revision += 1
        self.assertEqual((await tools.end_turn())['error']['code'], 'stale_state')

    async def test_native_error_is_not_converted_into_missing_ids_or_retried(self):
        client = HandClient()
        client.hand_error = 'illegal_action'
        result = await GameTools(client).inspect_hand({'preset': 'summary', 'card_ids': [9]})
        self.assertEqual(result['error']['code'], 'illegal_action')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('errors', result)

    async def test_queued_action_cannot_borrow_a_future_summary_inspection(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            game.release_observation.clear()
            inspection = asyncio.create_task(tools.inspect_hand({'preset': 'summary'}))
            self.assertTrue(await asyncio.to_thread(game.observation_started.wait, 2))
            action = asyncio.create_task(tools.end_turn())
            await asyncio.sleep(0)
            game.release_observation.set()
            self.assertIn('hand', await inspection)
            self.assertEqual((await action)['error']['code'], 'observation_required')
            self.assertEqual([r['operation'] for r in game.operations], ['inspect_hand'])


class HandPresetStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_dispatch_and_partial_errors_keep_matching_text_and_structured_json(self):
        with FakeGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name: t for t in (await session.list_tools()).tools}
                    self.assertEqual(set(tools['inspect_hand'].inputSchema['properties']), {'preset', 'card_ids'})
                    for args in ({'preset': 'summary', 'card_ids': [2, 80]}, {'card_ids': [80]}, {'card_ids': []}):
                        result = await session.call_tool('inspect_hand', args)
                        self.assertFalse(result.isError, result)
                        self.assertEqual(result.structuredContent, json.loads(result.content[0].text))
                        if args.get('preset') == 'summary':
                            self.assertEqual([card['id'] for card in result.structuredContent['hand']], [2])
                            self.assertNotIn('description', result.structuredContent['hand'][0])
                            self.assertNotIn('hover_tips', result.structuredContent)
                        if args['card_ids']:
                            self.assertEqual(result.structuredContent['errors'], [{'code': 'cards_not_in_hand', 'card_ids': [80]}])
                    result = await session.call_tool('inspect_hand', {'card_ids': [True]})
                    self.assertTrue(result.isError, result)
                    self.assertEqual(result.structuredContent['error']['code'], 'invalid_request')
                    self.assertEqual([r['operation'] for r in game.operations], ['inspect_hand'] * 3)


if __name__ == '__main__':
    unittest.main()
