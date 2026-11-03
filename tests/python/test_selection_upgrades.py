"""Cover selection upgrade controls through real validation and MCP projections."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.game_output import selection_details
from tests.python.test_selection_presets import SelectionClient


class UpgradeClient(SelectionClient):
    def __init__(self, supported=True):
        super().__init__()
        self.original = copy.deepcopy(self.choice['cards'][1])
        self.original['description'] = 'Gain 5 Block.'
        self.choice.update(type='deck_upgrade' if supported else 'reward',
                           cards=[copy.deepcopy(self.original)], can_view_upgrades=supported,
                           view_upgrades=False)
        if supported:
            self.choice['upgrade_previews'] = []

    def call(self, operation, expected_state=None, arguments=None):
        if operation != 'inspect_selection' or self.error:
            return super().call(operation, expected_state, arguments)
        self.calls.append((operation, expected_state, arguments))
        assert arguments is None or set(arguments) == {'view_upgrades'}, arguments
        warnings = []
        if arguments is not None:
            if self.choice['can_view_upgrades']:
                self.choice['view_upgrades'] = arguments['view_upgrades']
            else:
                warnings = [{'code': 'upgrade_view_unavailable'}]
        card = copy.deepcopy(self.original)
        if self.choice['view_upgrades']:
            card.update(name='Defend+', description='Gain 8 Block.')
        self.choice['cards'] = [card]
        result = {'snapshot_id': 'after-view', 'scene': 'rest_site', 'screen': {'status': 'visible'},
                  'selection': copy.deepcopy(self.choice)}
        if warnings:
            result['errors'] = warnings
        return {'ok': True, 'state': result}


class SelectionUpgradeTests(unittest.IsolatedAsyncioTestCase):
    async def test_upgrade_request_forwards_only_native_option_and_keeps_summary_identity(self):
        client = UpgradeClient()
        tools = GameTools(client)
        result = await tools.inspect_selection({'view_upgrades': True, 'preset': 'summary', 'card_ids': [2]})
        self.assertNotIn('error', result)
        self.assertTrue(result['selection']['can_view_upgrades'])
        self.assertTrue(result['selection']['view_upgrades'])
        self.assertEqual(result['selection']['cards'][0]['id'], 2)
        self.assertEqual(result['selection']['cards'][0]['name'], 'Defend+')
        self.assertNotIn('description', result['selection']['cards'][0])
        self.assertEqual(client.calls, [('inspect_selection', None, {'view_upgrades': True})])
        self.assertEqual(tools.snapshot_id, 'after-view')
        kept = await tools.inspect_selection()
        self.assertTrue(kept['selection']['view_upgrades'])
        self.assertEqual(kept['selection']['cards'][0]['description'], 'Gain 8 Block.')
        normal = await tools.inspect_selection({'view_upgrades': False})
        self.assertFalse(normal['selection']['view_upgrades'])
        self.assertEqual(normal['selection']['cards'][0]['description'], 'Gain 5 Block.')

    async def test_unavailable_upgrade_view_keeps_cards_and_merges_missing_ids(self):
        client = UpgradeClient(supported=False)
        tools = GameTools(client)
        for preset in ('full', 'summary'):
            result = await tools.inspect_selection({'view_upgrades': True, 'preset': preset, 'card_ids': [2, 999]})
            self.assertNotIn('error', result)
            self.assertEqual(result['errors'], [{'code': 'upgrade_view_unavailable'},
                                               {'code': 'cards_not_in_selection', 'card_ids': [999]}])
            self.assertEqual(result['selection']['cards'][0]['name'], 'Defend')
            self.assertFalse(result['selection']['view_upgrades'])
            self.assertEqual(tools.snapshot_id, 'after-view')
        empty = await tools.inspect_selection({'view_upgrades': True, 'card_ids': []})
        self.assertEqual(empty['selection']['cards'], [])
        self.assertEqual(empty['errors'], [{'code': 'upgrade_view_unavailable'}])

    async def test_invalid_upgrade_flag_does_not_request_game_or_clear_permission(self):
        client = UpgradeClient()
        tools = GameTools(client)
        await tools.get_observation()
        calls = len(client.calls)
        for flag in (None, 0, 1, 'true', [], {}):
            with self.subTest(flag=flag):
                result = await tools.inspect_selection({'view_upgrades': flag})
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(tools.snapshot_id, 'state-1')
                self.assertEqual(len(client.calls), calls)

    async def test_native_failure_is_not_replaced_by_upgrade_warning(self):
        client = UpgradeClient()
        client.error = 'illegal_action'
        result = await GameTools(client).inspect_selection({'view_upgrades': True})
        self.assertEqual(result['error']['code'], 'illegal_action')
        self.assertNotIn('errors', result)

    def test_hidden_selection_does_not_disclose_upgrade_setting(self):
        choice = UpgradeClient().choice
        choice.update(status='covered', prompt=None, min_select=None, max_select=None,
                      selected_ids=None, cards=None, options=[], can_view_battlefield=False,
                      can_view_upgrades=False, view_upgrades=None)
        result = selection_details(choice)
        self.assertIsNone(result['view_upgrades'])
        choice['view_upgrades'] = True
        with self.assertRaises(ValueError): selection_details(choice)


if __name__ == '__main__':
    unittest.main()
