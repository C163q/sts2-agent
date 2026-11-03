"""UI discovery summaries and exact source filtering preserve context and validation."""
import copy
import unittest
from sts2_mcp.output.ui_presets import ui_arguments, ui_preset
from sts2_mcp.output.inspection_details import ui_details


class UiPresetTests(unittest.TestCase):
    def setUp(self):
        self.data = {'scene': 'event', 'screen': {'status': 'visible'}, 'hover_tips': [
            {'title': 'HP', 'description': 'If you run out of HP, you die.',
             'sources': ['top_bar.hp', 'top_bar.max_hp']},
            {'title': 'Energy', 'description': 'Energy help.', 'sources': ['player.energy', 'player.max_energy']}],
            'notes': {'selection': 'Selection pending.'}}

    def test_noncombat_context_is_accepted_without_becoming_combat(self):
        self.assertEqual(ui_details(self.data), {k: v for k, v in self.data.items() if k != 'notes'})

    def test_summary_only_removes_description_and_does_not_mutate_input(self):
        original = copy.deepcopy(self.data)
        result = ui_preset(self.data, 'summary', None)
        self.assertEqual(result['hover_tips'], [{k: v for k, v in t.items() if k != 'description'} for t in self.data['hover_tips']])
        self.assertEqual(result['screen'], self.data['screen'])
        self.assertEqual(result['notes'], self.data['notes'])
        self.assertEqual(self.data, original)

    def test_exact_filter_preserves_tip_order_and_only_matching_sources(self):
        result = ui_preset(self.data, 'full', ['player.energy', 'top_bar.hp', 'player.energy'])
        self.assertEqual([t['title'] for t in result['hover_tips']], ['HP', 'Energy'])
        self.assertEqual([t['sources'] for t in result['hover_tips']], [['top_bar.hp'], ['player.energy']])
        self.assertIn('description', result['hover_tips'][0])

    def test_empty_filter_and_grouped_missing_sources(self):
        self.assertEqual(ui_preset(self.data, 'summary', [])['hover_tips'], [])
        result = ui_preset(self.data, 'summary', ['top_bar', 'top_bar.hp', 'missing'])
        self.assertEqual(result['hover_tips'], [{'title': 'HP', 'sources': ['top_bar.hp']}])
        self.assertEqual(result['errors'], [{'code': 'ui_sources_unavailable', 'sources': ['top_bar', 'missing']}])

    def test_arguments_and_duplicates(self):
        self.assertEqual(ui_arguments(None), {'preset': 'full', 'sources': None})
        self.assertEqual(ui_arguments({'preset': 'summary', 'sources': ['top_bar.hp', 'top_bar.hp']}),
                         {'preset': 'summary', 'sources': ['top_bar.hp']})
        for bad in [[], {'sources': 'top_bar.hp'}, {'sources': ['']},
                    {'sources': [1]}, {'extra': True}, {'preset': 'invalid'}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError): ui_arguments(bad)

    def test_errors_are_never_projected(self):
        error = {'error': {'code': 'illegal_action'}}
        self.assertIs(ui_preset(error, 'summary', []), error)


class UiToolBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_filtered_summary_refreshes_permission_and_groups_missing_paths(self):
        from tests.python.test_mcp_server import FakeGame
        from sts2_mcp.roundtrip_client import Client
        from sts2_mcp.game_tools import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            result = await tools.inspect_ui({'preset': 'summary', 'sources': ['player.energy', 'missing']})
            self.assertEqual(result['hover_tips'], [{'title': 'Energy', 'sources': ['player.energy']}])
            self.assertEqual(result['errors'], [{'code': 'ui_sources_unavailable', 'sources': ['missing']}])
            self.assertTrue((await tools.end_turn())['transition']['complete'])

    async def test_invalid_arguments_preserve_existing_permission_and_do_not_reach_ipc(self):
        from tests.python.test_mcp_server import FakeGame
        from sts2_mcp.roundtrip_client import Client
        from sts2_mcp.game_tools import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            self.assertEqual((await tools.inspect_ui({'sources': False}))['error']['code'], 'invalid_request')
            self.assertEqual([r['operation'] for r in game.operations], ['get_state'])
            self.assertTrue((await tools.end_turn())['transition']['complete'])

    async def test_empty_filter_does_not_hide_malformed_unselected_native_help(self):
        from tests.python.test_mcp_server import FakeGame
        from sts2_mcp.roundtrip_client import Client
        from sts2_mcp.game_tools import GameTools
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            game.ui_payload['hover_tips'][0]['description'] = 7
            result = await tools.inspect_ui({'preset': 'summary', 'sources': []})
            self.assertEqual(result['error']['code'], 'transport_error')
            self.assertIsNone(tools.snapshot_id)
