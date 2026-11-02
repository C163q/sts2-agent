"""Exercise selection summaries through validation, permissions and real MCP stdio."""
import copy
import json
import sys
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.player_output import player_result
from tests.python.test_action_observations import Client as ActionClient
from tests.python.test_hand_presets import hand
from tests.python.test_selection import selection


class SelectionClient(ActionClient):
    def __init__(self):
        super().__init__()
        self.choice = selection()
        self.choice['cards'] = hand()
        self.choice['cards'][0]['enchantment'] = {'name': 'Sharp', 'amount': 3, 'dimmed': False}
        self.error = None

    def call(self, operation, expected_state=None, arguments=None):
        if operation != 'inspect_selection':
            return super().call(operation, expected_state, arguments)
        self.calls.append((operation, expected_state, arguments))
        if self.error:
            return {'ok': False, 'error': {'code': self.error}}
        return {'ok': True, 'state': {'snapshot_id': self.token, 'scene': 'combat',
                                     'selection': copy.deepcopy(self.choice)}}


class SelectionPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_explicit_full_keep_existing_output_and_source(self):
        client = SelectionClient()
        original = copy.deepcopy(client.choice)
        expected = player_result({'ok': True, 'state': {'scene': 'combat', 'selection': original}},
                                 operation='inspect_selection')
        tools = GameTools(client)
        for args in (None, {}, {'preset': 'full'}):
            self.assertEqual(await tools.inspect_selection(args), expected)
        self.assertEqual(client.choice, original)
        self.assertEqual(client.calls, [('inspect_selection', None, None)] * 3)

    async def test_summary_preserves_selection_context_and_exact_hand_summary_cards(self):
        client = SelectionClient()
        client.choice['selected_ids'] = [9]
        result = await GameTools(client).inspect_selection({'preset': 'summary'})
        self.assertEqual(result['selection']['cards'], [
            {'id': 9, 'name': 'Defend+', 'type': 'Skill', 'energy_cost': '0', 'energy_cost_color': 'green',
             'unplayable_markers': [], 'outline': 'cyan',
             'enchantment': {'name': 'Sharp', 'amount': 3, 'dimmed': False}},
            {'id': 2, 'name': 'Defend', 'type': 'Skill', 'energy_cost': '1',
             'unplayable_markers': ['energy'], 'outline': 'none'},
            {'id': 4, 'name': 'Star Card', 'type': 'Attack', 'energy_cost': 'X', 'star_cost': '?',
             'star_cost_color': 'red', 'unplayable_markers': ['star'], 'outline': 'red'},
            {'id': 7, 'name': 'Unknown', 'type': None, 'energy_cost': None,
             'unplayable_markers': [], 'outline': 'none'},
        ])
        self.assertEqual({k: v for k, v in result['selection'].items() if k != 'cards'},
                         {k: v for k, v in client.choice.items() if k != 'cards'})
        self.assertEqual(result['scene'], 'combat')
        self.assertIn('selection', result['notes'])
        self.assertNotIn('hover_tips', result)
        self.assertIn('description', client.choice['cards'][0])

    async def test_every_preview_card_is_summarized_and_random_result_stays_unknown(self):
        for kind, field in [('hand_upgrade', 'upgrade_preview'), ('deck_upgrade', 'upgrade_previews'),
                            ('deck_enchant', 'enchant_previews'), ('deck_transform', 'transform_previews')]:
            for random in ([False, True] if kind == 'deck_transform' else [False]):
                with self.subTest(kind=kind, random=random):
                    client = SelectionClient()
                    before = copy.deepcopy(client.choice['cards'][0])
                    after = {**before, 'name': 'Defend++', 'description': 'Gain 11 Block.'}
                    pair = {'before': before, 'after': None if random else after}
                    client.choice.update(type=kind, selected_ids=[9])
                    if kind == 'deck_transform':
                        pair['random'] = random
                    if kind == 'deck_enchant':
                        client.choice['enchantment'] = {'title': 'Instinct', 'description': 'The visible operation.'}
                        before['enchantment'] = {'name': 'Clone', 'dimmed': False}
                    client.choice[field] = pair if kind == 'hand_upgrade' else [pair]
                    original = copy.deepcopy(client.choice)
                    result = await GameTools(client).inspect_selection({'preset': 'summary'})
                    preview = result['selection'][field]
                    preview = preview if kind == 'hand_upgrade' else preview[0]
                    for side in ('before', 'after'):
                        card = preview[side]
                        if card is None:
                            self.assertTrue(random)
                            continue
                        self.assertEqual(card['id'], 9)
                        self.assertNotIn('description', card)
                        self.assertNotIn('hover_tips', card)
                        self.assertNotIn('rarity', card)
                    if kind == 'deck_transform':
                        self.assertEqual(preview['random'], random)
                    if kind == 'deck_enchant':
                        self.assertEqual(result['selection']['enchantment'], original['enchantment'])
                        self.assertEqual(preview['before']['enchantment'], {'name': 'Clone', 'dimmed': False})
                    self.assertEqual(client.choice, original)

    async def test_bundle_cards_and_expanded_bundle_use_summaries(self):
        client = SelectionClient()
        cards = client.choice['cards']
        client.choice.update(type='bundle', cards=[], bundles=[{'id': 'bundle:0', 'cards': cards}])
        tools = GameTools(client)
        result = await tools.inspect_selection({'preset': 'summary'})
        self.assertEqual(result['selection']['bundles'][0]['id'], 'bundle:0')
        for card in result['selection']['bundles'][0]['cards']:
            self.assertNotIn('description', card)
            self.assertNotIn('hover_tips', card)
        self.assertNotIn('hover_tips', result)
        client.choice.update(cards=cards, bundles=[], selected_ids=[9, 2, 4, 7])
        expanded = await tools.inspect_selection({'preset': 'summary'})
        self.assertEqual(expanded['selection']['cards'], result['selection']['bundles'][0]['cards'])

    async def test_empty_result_page_is_a_valid_read_and_can_confirm_directly(self):
        client = SelectionClient()
        client.choice.update(type='view_cards', min_select=0, max_select=0, cards=[],
                             options=[{'id': 'confirm', 'text': 'Confirm', 'enabled': True}])
        tools = GameTools(client)
        self.assertEqual((await tools.inspect_selection({'preset': 'summary'}))['selection']['cards'], [])
        self.assertNotIn('error', await tools.selection_option({'option_id': 'confirm'}))
        self.assertEqual(client.calls, [('inspect_selection', None, None),
                                       ('selection_option', 'state-1', {'option_id': 'confirm'})])

    async def test_bad_arguments_do_not_read_or_clear_an_existing_permission(self):
        client = SelectionClient()
        tools = GameTools(client)
        await tools.get_observation()
        for args in ([], False, 0, '', {'preset': None}, {'preset': []}, {'preset': True},
                     {'preset': 'FULL'}, {'card_ids': None}, {'preset': 'summary', 'extra': 1}):
            with self.subTest(args=args):
                result = await tools.inspect_selection(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(tools.snapshot_id, 'state-1')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.select_card({'card_id': 9}))

    async def test_summary_cannot_hide_malformed_full_detail_and_clears_permission(self):
        for damage in ('description', 'tip', 'preview', 'bundle'):
            client = SelectionClient()
            tools = GameTools(client)
            await tools.get_observation()
            if damage == 'description':
                client.choice['cards'][0]['description'] = 3
            elif damage == 'tip':
                client.choice['cards'][0]['hover_tips'][0]['description'] = False
            elif damage == 'preview':
                card = client.choice['cards'][0]
                client.choice.update(type='hand_upgrade', selected_ids=[9],
                                     upgrade_preview={'before': card, 'after': {**card, 'id': 80}})
            else:
                client.choice.update(type='bundle', cards=[], bundles=[{'id': 'bundle:0', 'cards': [{'id': 9}]}])
            with self.subTest(damage=damage):
                result = await tools.inspect_selection({'preset': 'summary'})
                self.assertEqual(result['error']['code'], 'transport_error')
                self.assertEqual((await tools.select_card({'card_id': 9}))['error']['code'], 'observation_required')

    async def test_native_error_is_unchanged_and_summary_directly_authorizes_choice(self):
        client = SelectionClient()
        tools = GameTools(client)
        await tools.inspect_selection({'preset': 'summary'})
        self.assertNotIn('error', await tools.select_card({'card_id': 9}))
        self.assertEqual(client.calls[-1], ('select_card', 'state-1', {'card_id': 9}))
        client.error = 'illegal_action'
        self.assertEqual((await tools.inspect_selection({'preset': 'summary'}))['error']['code'], 'illegal_action')
        self.assertIsNone(tools.snapshot_id)


class SelectionPresetStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_schema_dispatch_and_matching_json_for_both_presets(self):
        from scripts._bootstrap import ROOT
        code = (f'import sys; sys.path.insert(0, {str(ROOT)!r}); import anyio; '
                'from tests.python.test_selection_presets import SelectionClient; from sts2_mcp.game_tools import GameTools; '
                'from sts2_mcp.mcp_server import run_stdio; anyio.run(run_stdio, GameTools(SelectionClient()))')
        params = StdioServerParameters(command=sys.executable, args=['-c', code])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = {t.name: t for t in (await session.list_tools()).tools}
                self.assertEqual(len(tools), 42)
                self.assertEqual(set(tools['inspect_selection'].inputSchema['properties']), {'preset', 'card_ids', 'view_upgrades'})
                self.assertFalse(tools['inspect_selection'].annotations.readOnlyHint)
                for args in ({}, {'preset': 'full'}, {'preset': 'summary'}):
                    result = await session.call_tool('inspect_selection', args)
                    self.assertFalse(result.isError, result)
                    self.assertEqual(result.structuredContent, json.loads(result.content[0].text))
                    card = result.structuredContent['selection']['cards'][0]
                    self.assertEqual('description' in card, args.get('preset') != 'summary')
                result = await session.call_tool('inspect_selection', {'preset': 'invalid'})
                self.assertTrue(result.isError, result)
                self.assertEqual(result.structuredContent['error']['code'], 'invalid_request')
                for preset in ('full', 'summary'):
                    result = await session.call_tool('inspect_selection', {'preset': preset, 'card_ids': [9, 80, 80]})
                    self.assertFalse(result.isError, result)
                    self.assertEqual(result.structuredContent, json.loads(result.content[0].text))
                    self.assertEqual([c['id'] for c in result.structuredContent['selection']['cards']], [9])
                    self.assertEqual(result.structuredContent['errors'], [
                        {'code': 'cards_not_in_selection', 'card_ids': [80]}])


if __name__ == '__main__':
    unittest.main()
