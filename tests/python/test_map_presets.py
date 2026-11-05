import asyncio
import copy
import json
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.game_tools import GameTools
from sts2_mcp.roundtrip_client import Client
from tests.python.test_mcp_server import FakeGame, SERVER, map_payload


class MapPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_explicit_full_keep_the_existing_result(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            for arguments in (None, {}, {'preset': 'full'}, {'max_steps': 0}, {'preset': 'full', 'max_steps': 0}):
                self.assertEqual(await tools.inspect_map(arguments), map_payload())

    async def test_selectable_returns_only_native_candidates_including_unconnected_flight(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:1', 'map:1:2:5'])
            game.map_payload['nodes'][2].update(revealed_type='monster', marked=True)
            tools = GameTools(Client(game.directory))
            result = await tools.inspect_map({'preset': 'selectable'})
            self.assertEqual(result, {
                'scene': 'combat', 'screen': {'status': 'covered', 'view': 'map'}, 'act': 1,
                'current_node': 'map:1:1:2', 'can_travel': True,
                'selectable_nodes': ['map:1:2:1', 'map:1:2:5'], 'preset': 'selectable',
                'nodes': [
                    {'id': 'map:1:2:1', 'row': 2, 'column': 1, 'type': 'unknown', 'revealed_type': 'monster', 'marked': True},
                    {'id': 'map:1:2:5', 'row': 2, 'column': 5, 'type': 'rest_site'},
                ],
            })
            self.assertNotIn('next', result['nodes'][0])
            self.assertEqual(game.operations[0], {'id': game.operations[0]['id'], 'operation': 'inspect_map',
                                                  'response_options': {'include_divination_image': False}})

    async def test_selectable_without_travel_returns_no_nodes(self):
        with FakeGame() as game:
            result = await GameTools(Client(game.directory)).inspect_map({'preset': 'selectable'})
            self.assertFalse(result['can_travel'])
            self.assertEqual(result['nodes'], [])
            self.assertEqual(result['selectable_nodes'], [])
            self.assertNotIn('visited_path', result)

    async def test_one_step_keeps_current_and_connected_successors_and_clips_boundary_edges(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:1', 'map:1:2:5'])
            result = await GameTools(Client(game.directory)).inspect_map({'max_steps': 1})
            self.assertEqual(result['max_steps'], 1)
            self.assertEqual(result['nodes'], [
                {'id': 'map:1:1:2', 'row': 1, 'column': 2, 'type': 'monster', 'next': ['map:1:2:1']},
                {'id': 'map:1:2:1', 'row': 2, 'column': 1, 'type': 'unknown', 'next': []},
            ])
            self.assertEqual(result['selectable_nodes'], ['map:1:2:1', 'map:1:2:5'])
            self.assertEqual(result['visited_path'], ['map:1:0:3', 'map:1:1:2'])

    async def test_depth_reaches_both_bosses_one_edge_at_a_time_without_mutation(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            before = copy.deepcopy(game.map_payload)
            two = await tools.inspect_map({'max_steps': 2})
            self.assertEqual([n['id'] for n in two['nodes']], ['map:1:1:2', 'map:1:2:1', 'map:1:3:3'])
            self.assertEqual(two['nodes'][-1], {'id': 'map:1:3:3', 'row': 3, 'column': 3,
                                              'type': 'boss', 'name': 'Ceremonial Beast', 'next': []})
            three = await tools.inspect_map({'max_steps': 3})
            self.assertEqual([n['id'] for n in three['nodes']], ['map:1:1:2', 'map:1:2:1', 'map:1:3:3', 'map:1:4:3'])
            self.assertEqual(three['nodes'][-2]['next'], ['map:1:4:3'])
            self.assertEqual(three['nodes'][-1]['name'], 'The Kin')
            self.assertEqual(game.map_payload, before)

    async def test_branches_merge_without_duplicates_and_cycles_stop_at_visited_nodes(self):
        with FakeGame() as game:
            game.map_payload['nodes'][1]['next'] = ['map:1:2:1', 'map:1:2:5']
            game.map_payload['nodes'][4]['next'].append('map:1:1:2')
            result = await GameTools(Client(game.directory)).inspect_map({'max_steps': 2147483647})
            self.assertEqual([n['id'] for n in result['nodes']],
                             ['map:1:1:2', 'map:1:2:1', 'map:1:2:5', 'map:1:3:3', 'map:1:4:3'])
            self.assertEqual(result['nodes'][-2]['next'], ['map:1:4:3', 'map:1:1:2'])

    async def test_depth_counts_edges_instead_of_rows_or_only_the_exact_last_level(self):
        with FakeGame() as game:
            game.map_payload['nodes'][1]['next'].append('map:1:3:3')
            result = await GameTools(Client(game.directory)).inspect_map({'max_steps': 2})
            self.assertEqual([n['id'] for n in result['nodes']], ['map:1:1:2', 'map:1:2:1', 'map:1:3:3', 'map:1:4:3'])

    async def test_unentered_act_counts_lowest_row_as_first_step_even_without_choices(self):
        with FakeGame() as game:
            game.map_payload.update(current_node=None, visited_path=[])
            tools = GameTools(Client(game.directory))
            first = await tools.inspect_map({'max_steps': 1})
            self.assertNotIn('current_node', first)
            self.assertFalse(first['can_travel'])
            self.assertEqual(first['nodes'], [{'id': 'map:1:0:3', 'row': 0, 'column': 3,
                                               'type': 'ancient', 'name': 'Neow', 'next': []}])
            second = await tools.inspect_map({'max_steps': 2})
            self.assertEqual([n['id'] for n in second['nodes']], ['map:1:0:3', 'map:1:1:2'])

    async def test_selectable_overrides_depth_without_changing_candidate_details(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:5'])
            tools = GameTools(Client(game.directory))
            selected = await tools.inspect_map({'preset': 'selectable'})
            self.assertEqual(await tools.inspect_map({'preset': 'selectable', 'max_steps': 1}), selected)
            self.assertNotIn('max_steps', selected)
            self.assertEqual(selected['nodes'][0]['id'], 'map:1:2:5')

    async def test_unentered_act_includes_every_lowest_row_entry_without_assuming_ancients(self):
        with FakeGame() as game:
            game.map_payload.update(current_node=None, visited_path=[])
            game.map_payload['nodes'].insert(1, {'id': 'map:1:0:4', 'row': 0, 'column': 4,
                                                'type': 'monster', 'next': ['map:1:1:2']})
            result = await GameTools(Client(game.directory)).inspect_map({'max_steps': 1})
            self.assertEqual([n['id'] for n in result['nodes']], ['map:1:0:3', 'map:1:0:4'])
            self.assertEqual(result['nodes'][1]['type'], 'monster')
            self.assertTrue(all(n['next'] == [] for n in result['nodes']))

    async def test_queued_travel_cannot_borrow_a_future_selectable_inspection(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:5'])
            tools = GameTools(Client(game.directory))
            game.release_observation.clear()
            inspection = asyncio.create_task(tools.inspect_map({'preset': 'selectable'}))
            self.assertTrue(await asyncio.to_thread(game.observation_started.wait, 2))
            travel = asyncio.create_task(tools.travel_to_node({'node_id': 'map:1:2:5'}))
            await asyncio.sleep(0)
            game.release_observation.set()
            self.assertTrue((await inspection)['can_travel'])
            self.assertEqual((await travel)['error']['code'], 'observation_required')
            self.assertEqual([r['operation'] for r in game.operations], ['inspect_map'])

    async def test_invalid_options_and_close_options_preserve_existing_permission_before_ipc(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            for arguments in ({'preset': None}, {'preset': 'brief'}, {'preset': []}, {'max_steps': True},
                              {'max_steps': 1.0}, {'max_steps': -1}, {'max_steps': 2147483648},
                              {'max_steps': '1'}, {'max_steps': None}, {'preset': 'selectable', 'max_steps': -1},
                              {'filter_next': 1}, [], False):
                self.assertEqual((await tools.inspect_map(arguments))['error']['code'], 'invalid_request')
            for arguments in ({'preset': None}, {'preset': 'selectable'}, {'max_steps': 0}):
                self.assertEqual((await tools.close_map(arguments))['error']['code'], 'invalid_request')
            self.assertEqual([r['operation'] for r in game.operations], ['get_state'])
            self.assertNotIn('error', await tools.end_turn())

    async def test_bad_full_graph_is_rejected_even_when_corruption_would_be_filtered_out(self):
        for options in ({'preset': 'selectable'}, {'max_steps': 1}):
            with self.subTest(options=options), FakeGame() as game:
                tools = GameTools(Client(game.directory))
                await tools.get_observation()
                game.map_payload['nodes'][-1]['next'] = ['map:2:9:9']
                self.assertEqual((await tools.inspect_map(options))['error']['code'], 'transport_error')
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_selectable_and_filtered_reads_support_travel_with_the_full_native_token(self):
        for options in ({'preset': 'selectable'}, {'max_steps': 1}):
            with self.subTest(options=options), FakeGame() as game:
                game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:5'])
                tools = GameTools(Client(game.directory))
                await tools.inspect_map(options)
                self.assertNotIn('error', await tools.travel_to_node({'node_id': 'map:1:2:5'}))
                self.assertEqual(game.operations[-1]['expected_state'], 'state-1-ui-1')
                self.assertNotIn('arguments', game.operations[0])

    async def test_real_external_change_still_invalidates_permission_after_selectable_read(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:5'])
            tools = GameTools(Client(game.directory))
            await tools.inspect_map({'preset': 'selectable'})
            game.turn += 1
            self.assertEqual((await tools.travel_to_node({'node_id': 'map:1:2:5'}))['error']['code'], 'stale_state')

    async def test_native_error_is_returned_without_filtering_or_retry(self):
        with FakeGame() as game:
            game.map_error = True
            result = await GameTools(Client(game.directory)).inspect_map({'preset': 'selectable'})
            self.assertEqual(result['error']['code'], 'illegal_action')
            self.assertEqual(len(game.operations), 1)


class MapPresetStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovered_schema_accepts_parameters_and_returns_matching_text_and_json(self):
        with FakeGame() as game:
            game.map_payload.update(can_travel=True, selectable_nodes=['map:1:2:5'])
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name: t for t in (await session.list_tools()).tools}
                    self.assertEqual(set(tools['inspect_map'].inputSchema['properties']), {'preset', 'max_steps'})
                    for options, count in (({'preset': 'selectable', 'max_steps': 1}, 1), ({'max_steps': 1}, 2)):
                        result = await session.call_tool('inspect_map', options)
                        self.assertFalse(result.isError, result)
                        self.assertEqual(result.structuredContent, json.loads(result.content[0].text))
                        self.assertEqual(len(result.structuredContent['nodes']), count)
                    travel = await session.call_tool('travel_to_node', {'node_id': 'map:1:2:5'})
                    self.assertFalse(travel.isError, travel)


if __name__ == '__main__':
    unittest.main()
