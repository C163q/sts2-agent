"""Filter validated selection details while preserving native choice context."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_server import tool_result
from tests.python.test_selection_presets import SelectionClient


class SelectionFilterTests(unittest.IsolatedAsyncioTestCase):
    async def test_filter_keeps_native_order_and_only_matching_shared_tip_links(self):
        client = SelectionClient()
        original = copy.deepcopy(client.choice)
        result = await GameTools(client).inspect_selection({'card_ids': [4, 2, 2]})
        self.assertEqual([c['id'] for c in result['selection']['cards']], [2, 4])
        self.assertEqual(result['hover_tips'], [
            {'title': 'Block', 'description': 'Until next turn, prevents damage.', 'card_ids': [2]},
            {'title': 'Star', 'description': 'A visible resource.', 'card_ids': [4]},
        ])
        self.assertEqual(client.choice, original)
        self.assertEqual(client.calls, [('inspect_selection', None, None)])

    async def test_mixed_missing_ids_are_grouped_once_and_do_not_block_direct_action(self):
        for preset in ('full', 'summary'):
            with self.subTest(preset=preset):
                client = SelectionClient()
                tools = GameTools(client)
                result = await tools.inspect_selection({'preset': preset, 'card_ids': [80, 9, 70, 80]})
                self.assertEqual([c['id'] for c in result['selection']['cards']], [9])
                self.assertEqual(result['selection']['cards'][0]['enchantment']['name'], 'Sharp')
                self.assertEqual(result['errors'], [{'code': 'cards_not_in_selection', 'card_ids': [80, 70]}])
                self.assertFalse(tool_result(result).isError)
                self.assertEqual('description' in result['selection']['cards'][0], preset == 'full')
                self.assertNotIn('error', await tools.select_card({'card_id': 9}))
                self.assertEqual(client.calls[-1], ('select_card', 'state-1', {'card_id': 9}))

    async def test_empty_and_all_missing_filters_keep_complete_context(self):
        for preset in ('full', 'summary'):
            for ids in ([], [80, 80]):
                client = SelectionClient()
                client.choice['selected_ids'] = [9]
                result = await GameTools(client).inspect_selection({'preset': preset, 'card_ids': ids})
                self.assertEqual(result['selection'], {**client.choice, 'cards': []})
                self.assertEqual(result.get('errors'), None if not ids else [
                    {'code': 'cards_not_in_selection', 'card_ids': [80]}])
                self.assertEqual(result.get('hover_tips'), [] if preset == 'full' else None)

    async def test_bundle_filter_keeps_bundle_ids_and_filters_each_card_list(self):
        for preset in ('full', 'summary'):
            client = SelectionClient()
            cards = client.choice['cards']
            client.choice.update(type='bundle', cards=[], bundles=[
                {'id': 'bundle:0', 'cards': cards[:2]}, {'id': 'bundle:1', 'cards': cards[2:]}])
            tools = GameTools(client)
            result = await tools.inspect_selection({'preset': preset, 'card_ids': [4, 2, 80]})
            bundles = result['selection']['bundles']
            self.assertEqual([b['id'] for b in bundles], ['bundle:0', 'bundle:1'])
            self.assertEqual([[c['id'] for c in b['cards']] for b in bundles], [[2], [4]])
            self.assertEqual(result['errors'], [{'code': 'cards_not_in_selection', 'card_ids': [80]}])
            self.assertEqual('description' in bundles[0]['cards'][0], preset == 'full')
            empty = await tools.inspect_selection({'preset': preset, 'card_ids': []})
            self.assertEqual(empty['selection']['bundles'], [
                {'id': 'bundle:0', 'cards': []}, {'id': 'bundle:1', 'cards': []}])

    async def test_all_preview_types_filter_by_original_id_without_changing_comparisons(self):
        for kind, field in [('hand_upgrade', 'upgrade_preview'), ('deck_upgrade', 'upgrade_previews'),
                            ('deck_enchant', 'enchant_previews'), ('deck_transform', 'transform_previews')]:
            for preset in ('full', 'summary'):
                with self.subTest(kind=kind, preset=preset):
                    client = SelectionClient()
                    before = copy.deepcopy(client.choice['cards'][0])
                    pair = {'before': before, 'after': {**before, 'name': 'Defend++'}}
                    client.choice.update(type=kind, selected_ids=[9], cards=[])
                    if kind == 'deck_transform':
                        pair.update(after=None, random=True)
                    if kind == 'deck_enchant':
                        client.choice['enchantment'] = {'title': 'Instinct', 'description': 'The visible operation.'}
                    client.choice[field] = pair if kind == 'hand_upgrade' else [pair]
                    original = copy.deepcopy(client.choice)
                    tools = GameTools(client)
                    result = await tools.inspect_selection({'preset': preset, 'card_ids': [9, 80]})
                    self.assertEqual(result['errors'], [{'code': 'cards_not_in_selection', 'card_ids': [80]}])
                    preview = result['selection'][field]
                    preview = preview if kind == 'hand_upgrade' else preview[0]
                    self.assertEqual(preview['before']['id'], 9)
                    self.assertEqual('description' in preview['before'], preset == 'full')
                    if kind == 'deck_transform':
                        self.assertIsNone(preview['after'])
                        self.assertTrue(preview['random'])
                    else:
                        self.assertEqual(preview['after']['name'], 'Defend++')
                    empty = await tools.inspect_selection({'preset': preset, 'card_ids': []})
                    if preset == 'summary':
                        self.assertNotIn(field, empty['selection'])
                    else:
                        self.assertEqual(empty['selection'][field], None if kind == 'hand_upgrade' else [])
                    self.assertEqual(empty['selection']['selected_ids'], [9])
                    self.assertEqual(client.choice, original)

    async def test_result_page_filters_identity_without_making_cards_selectable(self):
        client = SelectionClient()
        client.choice.update(type='view_cards', min_select=0, max_select=0, selected_ids=[],
                             options=[{'id': 'confirm', 'text': 'Confirm', 'enabled': True}])
        tools = GameTools(client)
        result = await tools.inspect_selection({'card_ids': [9]})
        self.assertEqual([c['id'] for c in result['selection']['cards']], [9])
        self.assertEqual(result['selection']['min_select'], 0)
        self.assertEqual(result['selection']['max_select'], 0)
        self.assertNotIn('error', await tools.selection_option({'option_id': 'confirm'}))

    async def test_invalid_id_arguments_do_not_request_game_or_clear_permission(self):
        client = SelectionClient()
        tools = GameTools(client)
        await tools.get_observation()
        for ids in ( False, '9', {}, [True], [1.0], ['9'], [-1], [2147483648]):
            with self.subTest(ids=ids):
                result = await tools.inspect_selection({'card_ids': ids})
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(tools.snapshot_id, 'state-1')
        self.assertEqual(len(client.calls), 1)

    async def test_filter_cannot_hide_malformed_unmatched_card_or_preview(self):
        for damage in ('card', 'preview', 'bundle'):
            client = SelectionClient()
            if damage == 'card':
                client.choice['cards'][1]['description'] = 123
            elif damage == 'preview':
                card = client.choice['cards'][0]
                client.choice.update(type='hand_upgrade', selected_ids=[9],
                                     upgrade_preview={'before': card, 'after': {**card, 'id': 80}})
            else:
                client.choice.update(type='bundle', cards=[], bundles=[{'id': 'bundle:0', 'cards': [{'id': 9}]}])
            tools = GameTools(client)
            await tools.get_observation()
            result = await tools.inspect_selection({'preset': 'summary', 'card_ids': []})
            self.assertEqual(result['error']['code'], 'transport_error')
            self.assertIsNone(tools.snapshot_id)

    async def test_hidden_selection_error_is_not_converted_to_missing_ids(self):
        client = SelectionClient()
        client.error = 'illegal_action'
        result = await GameTools(client).inspect_selection({'card_ids': [9]})
        self.assertEqual(result['error']['code'], 'illegal_action')
        self.assertNotIn('errors', result)


if __name__ == '__main__':
    unittest.main()
