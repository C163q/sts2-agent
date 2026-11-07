"""Pin card content boundaries and full browse validation before compact output."""
import copy
import json
import subprocess
import sys
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_mcp_server import FakeGame
from sts2_mcp.roundtrip_client import Client


class SharedCardFormatTests(unittest.IsolatedAsyncioTestCase):
    async def test_browse_default_is_complete_and_summary_uses_hand_fields(self):
        with FakeGame() as game:
            card = game.deck_payload['deck'][0]
            card.update(enchantment=None, affliction={'name': 'Bound'}, energy_cost_color='green')
            tools = GameTools(Client(game.directory))
            default = await tools.inspect_deck()
            self.assertEqual(default['deck'][0]['description'], 'Gain 8 Block.')
            self.assertNotIn('detail_level', default)
            full = await tools.inspect_deck({'preset': 'full'})
            self.assertIsNone(full['deck'][0]['enchantment'])
            summary = await tools.inspect_deck({'preset': 'summary'})
            self.assertEqual(summary['deck'][0], {'id': 'deck:0', 'name': 'Defend+', 'type': 'Skill',
                                                'energy_cost': '1', 'energy_cost_color': 'green',
                                                'affliction': {'name': 'Bound'}})
            self.assertNotIn('hover_tips', summary)
            self.assertEqual((await tools.inspect_deck({'detail_level': 'full'}))['error']['code'], 'invalid_request')

    async def test_compact_browse_does_not_hide_malformed_full_card(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            game.deck_payload['deck'][0]['hover_tips'] = [{'title': True, 'description': 'bad'}]
            self.assertEqual((await tools.inspect_deck({'preset': 'summary'}))['error']['code'], 'transport_error')


class CardModeTests(unittest.TestCase):
    def test_file_cli_projects_browse_presets_without_forwarding_them(self):
        from tests.python.test_mcp_server import SERVER
        with FakeGame() as game:
            command = [sys.executable, str(SERVER.with_name('roundtrip_client.py')),
                       '--ipc-dir', str(game.directory), 'inspect_deck']
            for preset in ('full', 'default', 'summary'):
                response = subprocess.run([*command, '--preset', preset], capture_output=True, text=True, timeout=8)
                self.assertEqual(response.returncode, 0, response.stderr)
                result = json.loads(response.stdout)
                self.assertEqual('description' in result['deck'][0], preset != 'summary')
                self.assertNotIn('detail_level', result)
                self.assertNotIn('preset', game.operations[-1].get('arguments', {}))
            count = len(game.operations)
            rejected = subprocess.run([*command, '--detail-level', 'full'], capture_output=True, text=True, timeout=8)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(len(game.operations), count)

    def test_expanded_candidate_and_comparison_help_survives_all_output_stages(self):
        from sts2_mcp.output.game_output import observation_details
        from sts2_mcp.output.inspection_details import inspection_details
        from sts2_mcp.output.player_output import player_result
        from sts2_mcp.output.presets import apply_preset
        from tests.python.test_selection import state
        data = state()
        before = {**data['selection']['cards'][0], 'enchantment': None,
                  'hover_tips': [{'title': 'Block', 'description': 'Before help.'}]}
        after = {**before, 'name': 'Defend+', 'description': 'Gain 8 Block.',
                 'enchantment': {'name': 'Sharp', 'amount': 2, 'dimmed': False},
                 'hover_tips': [{'title': 'Block', 'description': 'After help.'}]}
        data['selection'].update(type='hand_upgrade', selected_ids=[5], cards=[before],
                                 upgrade_preview={'before': before, 'after': after})
        for detailed, reader in ((False, observation_details), (True, lambda value: inspection_details('inspect_selection', value))):
            result = player_result({'ok': True, 'state': reader(data)}, operation='inspect_selection')
            pair = result['selection']['upgrade_preview']
            if detailed:
                self.assertEqual(pair['before']['hover_tips'], [{'title': 'Block', 'description': 'Before help.'}])
                self.assertEqual(pair['after']['hover_tips'], [{'title': 'Block', 'description': 'After help.'}])
            else:
                self.assertNotIn('hover_tips', pair['before'])
                self.assertNotIn('description', pair['after'])
            self.assertIsNone(apply_preset(result, 'default')['selection']['upgrade_preview']['before']['enchantment'])

    def test_result_observation_keeps_card_faces_and_general_tip_titles(self):
        from sts2_mcp.output.game_output import observation_details
        from tests.python.test_run_ending import state
        data = state('summary')
        data['run_result']['cards'] = [{'id': 'card:0', 'name': 'Defend', 'description': 'Gain 5 Block.',
                                        'enchantment': None, 'affliction': None,
                                        'hover_tips': [{'title': 'Block', 'description': 'Card help.'}]}]
        data['run_result']['hover_tips'] = [{'source': 'secret', 'title': 'General', 'description': 'Dedicated only.'}]
        result = observation_details(data)['run_result']
        self.assertNotIn('hover_tips', result['cards'][0])
        self.assertNotIn('description', result['cards'][0])
        self.assertEqual(result['hover_tips'], [{'source': 'secret', 'title': 'General'}])

    def test_fixed_face_boundary_and_comparison_null_context(self):
        from sts2_mcp.output.card_format import format_card
        card = {'id': 3, 'name': 'Defend', 'type': 'Skill', 'energy_cost': '1', 'star_cost': None,
                'enchantment': None, 'affliction': None, 'description': 'Gain 5 Block.',
                'hover_tips': [{'title': 'Block', 'description': 'Prevents damage.'}],
                'unplayable_markers': [], 'outline': 'none', 'private': 1}
        before = copy.deepcopy(card)
        for mode in ('face_full', 'face_default', 'summary'):
            result = format_card(card, mode)
            self.assertNotIn('description', result)
            self.assertNotIn('hover_tips', result)
            self.assertNotIn('private', result)
        self.assertIsNone(format_card(card, 'full')['enchantment'])
        self.assertNotIn('enchantment', format_card(card, 'default'))
        self.assertIsNone(format_card(card, 'default', path=('selection', 'upgrade_preview', 'before'))['enchantment'])
        self.assertEqual(format_card(card, 'full')['hover_tips'], [{'title': 'Block', 'description': 'Prevents damage.'}])
        self.assertEqual(card, before)


if __name__ == '__main__':
    unittest.main()
