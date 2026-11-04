"""Exercise relic presets and original-list indices through validated MCP output."""
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


class RelicClient(ActionClient):
    def __init__(self):
        super().__init__()
        block = {'title': 'Block', 'description': 'Prevents damage.'}
        self.relics = [
            {'name': 'Anchor', 'counter': None, 'melted': False, 'description': 'Start with 10 Block.', 'hover_tips': [block]},
            {'name': 'Pen Nib', 'counter': 0, 'melted': None, 'description': 'Every tenth attack.', 'hover_tips': []},
            {'name': 'Anchor', 'counter': None, 'melted': True, 'description': 'Melted.', 'hover_tips': [block]},
        ]
        self.error = None

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation != 'inspect_relics':
            return super().call(operation, expected_state, arguments)
        self.calls.append((operation, expected_state, arguments))
        if self.error:
            return {'ok': False, 'error': {'code': self.error}}
        return {'ok': True, 'state': {'snapshot_id': self.token, 'relics': copy.deepcopy(self.relics)}}


class RelicPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_full_preserve_existing_output(self):
        client = RelicClient()
        original = copy.deepcopy(client.relics)
        expected = player_result({'ok': True, 'state': {'relics': original}}, operation='inspect_relics')
        tools = GameTools(client)
        for args in ({'preset': 'full'},):
            self.assertEqual(await tools.inspect_relics(args), expected)
        self.assertEqual(client.relics, original)
        self.assertEqual(client.calls, [('inspect_relics', None, None)] * 1)

    async def test_summary_keeps_only_basic_fields_including_zero_unknown_and_melted(self):
        client = RelicClient()
        client.relics[0].update(hidden_counter=12, future='secret')
        self.assertEqual(await GameTools(client).inspect_relics({'preset': 'summary'}), {'relics': [
            {'name': 'Anchor', 'melted': False},
            {'name': 'Pen Nib', 'counter': 0},
            {'name': 'Anchor', 'melted': True},
        ]})

    async def test_filter_uses_original_positions_preserves_order_and_original_tip_links(self):
        client = RelicClient()
        original = copy.deepcopy(client.relics)
        result = await GameTools(client).inspect_relics({'relic_indices': [2, 1, 2]})
        self.assertEqual(result['relic_indices'], [1, 2])
        self.assertEqual([r['name'] for r in result['relics']], ['Pen Nib', 'Anchor'])
        self.assertEqual(result['hover_tips'], [
            {'title': 'Block', 'description': 'Prevents damage.', 'relic_indices': [2]}])
        self.assertEqual(client.relics, original)
        self.assertEqual(client.calls, [('inspect_relics', None, None)])

    async def test_shared_tip_keeps_all_matching_original_indices(self):
        result = await GameTools(RelicClient()).inspect_relics({'relic_indices': [2, 0]})
        self.assertEqual(result['relic_indices'], [0, 2])
        self.assertEqual(result['hover_tips'][0]['relic_indices'], [0, 2])

    async def test_missing_indices_are_grouped_once_alongside_valid_results(self):
        for preset in ('full', 'summary'):
            result = await GameTools(RelicClient()).inspect_relics({
                'preset': preset, 'relic_indices': [80, 2, 70, 80]})
            self.assertEqual(result['relic_indices'], [2])
            self.assertEqual(result['relics'][0]['name'], 'Anchor')
            self.assertTrue(result['relics'][0]['melted'])
            self.assertEqual(result['errors'], [{'code': 'relic_indices_out_of_range', 'relic_indices': [80, 70]}])
            self.assertFalse(tool_result(result).isError)
            self.assertEqual('description' in result['relics'][0], preset == 'full')

    async def test_empty_and_all_missing_filters_keep_expected_shape(self):
        for preset in ('full', 'summary'):
            for indices in ([], [2147483647, 2147483647]):
                result = await GameTools(RelicClient()).inspect_relics({'preset': preset, 'relic_indices': indices})
                self.assertEqual(result['relics'], [])
                self.assertEqual(result['relic_indices'], [])
                self.assertEqual(result.get('hover_tips'), [] if preset == 'full' else None)
                self.assertEqual(result.get('errors'), None if not indices else [
                    {'code': 'relic_indices_out_of_range', 'relic_indices': [2147483647]}])
        client = RelicClient()
        client.relics = []
        self.assertEqual(await GameTools(client).inspect_relics({'preset': 'summary'}), {'relics': []})

    async def test_old_output_without_melted_is_not_filled_from_assumptions(self):
        client = RelicClient()
        for relic in client.relics:
            del relic['melted']
        result = await GameTools(client).inspect_relics({'preset': 'summary'})
        self.assertEqual(result['relics'], [{'name': 'Anchor'}, {'name': 'Pen Nib', 'counter': 0}, {'name': 'Anchor'}])

    async def test_invalid_arguments_do_not_read_or_clear_existing_permission(self):
        client = RelicClient()
        tools = GameTools(client)
        await tools.get_observation()
        args = [[], False, 0, '', {'preset': None}, {'preset': 'FULL'}, {'preset': []},
                {'relic_ids': [0]}, {'extra': True}]
        args += [{'relic_indices': indices} for indices in
                 (False, '0', {}, [True], [1.0], ['0'], [-1], [2147483648])]
        for value in args:
            with self.subTest(args=value):
                self.assertEqual((await tools.inspect_relics(value))['error']['code'], 'invalid_request')
                self.assertEqual(tools.snapshot_id, 'state-1')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.end_turn())

    async def test_filtered_empty_and_partial_success_authorize_direct_actions(self):
        for indices in ([], [0], [80, 1]):
            client = RelicClient()
            tools = GameTools(client)
            self.assertNotIn('error', await tools.inspect_relics({'preset': 'summary', 'relic_indices': indices}))
            self.assertNotIn('error', await tools.end_turn())
            self.assertEqual(client.calls[-1], ('end_turn', 'state-1', None))

    async def test_summary_and_empty_filter_cannot_hide_invalid_full_details(self):
        for damage in ('description', 'tip', 'counter', 'melted'):
            client = RelicClient()
            if damage == 'description':
                client.relics[2]['description'] = 123
            elif damage == 'tip':
                client.relics[2]['hover_tips'][0]['description'] = False
            elif damage == 'counter':
                client.relics[2]['counter'] = True
            else:
                client.relics[2]['melted'] = 1
            tools = GameTools(client)
            await tools.get_observation()
            result = await tools.inspect_relics({'preset': 'summary', 'relic_indices': []})
            self.assertEqual(result['error']['code'], 'transport_error')
            self.assertIsNone(tools.snapshot_id)

    async def test_native_error_is_not_replaced_by_missing_indices(self):
        client = RelicClient()
        client.error = 'illegal_action'
        result = await GameTools(client).inspect_relics({'preset': 'summary', 'relic_indices': [0]})
        self.assertEqual(result['error']['code'], 'illegal_action')
        self.assertNotIn('errors', result)


class RelicPresetStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_dispatch_and_matching_json(self):
        from scripts._bootstrap import ROOT
        code = (f'import sys; sys.path.insert(0, {str(ROOT)!r}); import anyio; '
                'from tests.python.test_relic_presets import RelicClient; from sts2_mcp.game_tools import GameTools; '
                'from sts2_mcp.mcp_server import run_stdio; anyio.run(run_stdio, GameTools(RelicClient()))')
        params = StdioServerParameters(command=sys.executable, args=['-c', code])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name: t for t in (await session.list_tools()).tools}
                self.assertEqual(len(tools), 43)
                self.assertEqual(set(tools['inspect_relics'].inputSchema['properties']), {'preset', 'relic_indices'})
                self.assertTrue(tools['inspect_relics'].annotations.readOnlyHint)
                for preset in ('full', 'summary'):
                    result = await session.call_tool('inspect_relics', {'preset': preset, 'relic_indices': [2, 80]})
                    self.assertFalse(result.isError, result)
                    self.assertEqual(result.structuredContent, json.loads(result.content[0].text))
                    self.assertEqual(result.structuredContent['relic_indices'], [2])
                    self.assertEqual(result.structuredContent['errors'], [
                        {'code': 'relic_indices_out_of_range', 'relic_indices': [80]}])


if __name__ == '__main__':
    unittest.main()
