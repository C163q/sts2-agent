"""Ancient details validate the exposed UI before compacting or filtering."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_ancients import state
from tests.python.test_tool_contracts import ContractReply


def details():
    raw = state()
    raw['schema_version'] = 46
    raw['ancient'].update(description='An already displayed introduction.',
        options=[{'id': 4, 'title': 'First Gift', 'description': 'Transform 1 card.',
                  'enabled': True, 'lethal_warning': False,
                  'hover_tips': [{'title': 'Transform', 'description': 'Replace a card.'}]},
                 {'id': 9, 'title': 'Second Gift', 'description': 'Lose 9 Max HP.',
                  'enabled': True, 'lethal_warning': True, 'hover_tips': []}])
    return raw


class AncientInspectionPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_keeps_gift_effects_and_observation_uses_same_static_fields(self):
        expected = {'status': 'visible', 'name': 'Neow', 'description': 'An already displayed introduction.',
            'dialogue': [{'speaker': 'Neow', 'text': 'Awaken.'}], 'options': [
                {'id': 4, 'title': 'First Gift', 'description': 'Transform 1 card.', 'enabled': True},
                {'id': 9, 'title': 'Second Gift', 'description': 'Lose 9 Max HP.', 'enabled': True, 'lethal_warning': True}]}
        value = await GameTools(ContractReply(details())).inspect_ancient({'preset': 'summary'})
        self.assertNotIn('error', value)
        self.assertEqual(value['ancient'], expected)
        for preset in ('full', 'default', 'summary'):
            result = await GameTools(ContractReply(details())).get_observation({'preset': preset})
            self.assertNotIn('error', result)
            want = {**expected, 'epithet': None, 'continue': None, 'proceed': None} if preset == 'full' else expected
            self.assertEqual(result['ancient'], want)

    async def test_filter_keeps_native_ids_order_and_groups_missing_ids(self):
        for preset in ('full', 'default', 'summary'):
            for requested, expected, missing in [(None, [4, 9], []), ([], [], []), ([9], [9], []),
                    ([9, 4, 9], [4, 9], []), ([3, 9, 7, 3], [9], [3, 7])]:
                with self.subTest(preset=preset, requested=requested):
                    client = ContractReply(details()); tools = GameTools(client)
                    result = await tools.inspect_ancient({'preset': preset, 'option_ids': requested})
                    self.assertNotIn('error', result)
                    self.assertEqual([o['id'] for o in result['ancient']['options']], expected)
                    self.assertEqual(result.get('errors', []), [{'code': 'option_ids_not_found', 'option_ids': missing}] if missing else [])
                    self.assertEqual(result['ancient']['dialogue'], [{'speaker': 'Neow', 'text': 'Awaken.'}])
                    self.assertTrue(all(('hover_tips' in o) == (preset != 'summary') for o in result['ancient']['options']))
                    self.assertEqual(client.calls, [{'operation': 'inspect_ancient', 'expected_state': None, 'arguments': None}])
                    self.assertEqual(tools.snapshot_id, 'ancient-1')
                    if preset != 'summary' and requested is None:
                        self.assertIs(result['ancient']['options'][0]['lethal_warning'], False)
                    self.assertEqual('proceed' in result['ancient'], preset == 'full')

    async def test_empty_filter_keeps_continue_and_proceed(self):
        raw = details(); raw['ancient'].update(options=[],
            continue_ignored=None, proceed={'text': 'Proceed', 'enabled': True})
        raw['ancient']['continue'] = {'text': None, 'enabled': False}
        for preset in ('full', 'default', 'summary'):
            result = await GameTools(ContractReply(raw)).inspect_ancient({'preset': preset, 'option_ids': []})
            self.assertNotIn('error', result)
            self.assertEqual(result['ancient']['options'], [])
            self.assertEqual(result['ancient']['proceed'], {'text': 'Proceed', 'enabled': True})
            self.assertIs(result['ancient']['continue']['enabled'], False)

    async def test_unavailable_hover_note_follows_filter_and_summary(self):
        raw = details(); raw['unavailable_hover_sources'] = ['ancient.options.9']
        for preset in ('full', 'default', 'summary'):
            for selected in (None, [], [4], [9]):
                result = await GameTools(ContractReply(raw)).inspect_ancient({'preset': preset, 'option_ids': selected})
                self.assertNotIn('error', result)
                note = result.get('notes', {}).get('hover_tips_unavailable')
                if preset != 'summary' and selected in (None, [9]):
                    self.assertEqual(note['sources'], ['ancient.options.9'])
                else:
                    self.assertIsNone(note)
        self.assertEqual(raw['unavailable_hover_sources'], ['ancient.options.9'])

    async def test_bad_context_never_refreshes_permission_even_with_empty_filter(self):
        for screen in ({'status': 'covered'}, {'status': 'covered', 'view': 'map'},
                       {'status': 'covered', 'view': 'deck'}, {'status': 'visible', 'view': 'selection'},
                       {'status': 'hidden'}, {'status': 'not_ready'}):
            for tool in ('inspect_ancient', 'get_observation'):
                raw = details(); raw['screen'] = screen
                tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'old'
                result = await getattr(tools, tool)({'option_ids': []} if tool == 'inspect_ancient' else {})
                self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                self.assertIsNone(tools.snapshot_id)

    async def test_bad_rows_and_hover_evidence_cannot_be_hidden_by_filter(self):
        mutations = [lambda r: r['ancient']['options'][1].pop('lethal_warning'),
            lambda r: r['ancient']['options'][1].update(lethal_warning=None),
            lambda r: r['ancient']['options'][1].update(id=2147483648),
            lambda r: r['ancient']['options'][1].pop('hover_tips'),
            lambda r: r.update(unavailable_hover_sources=['ancient.options.123']),
            lambda r: r.update(unavailable_hover_sources=['ancient.options.9', 'ancient.options.9']),
            lambda r: r.update(unavailable_hover_sources=['ancient.options.4']),
            lambda r: r.update(unavailable_hover_sources='ancient.options.9')]
        for mutate in mutations:
            for preset in ('full', 'summary'):
                raw = details(); mutate(raw)
                tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'old'
                result = await tools.inspect_ancient({'preset': preset, 'option_ids': []})
                self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                self.assertIsNone(tools.snapshot_id)

    async def test_old_schema_does_not_invent_absent_death_warning(self):
        raw = details(); raw['schema_version'] = 45
        for option in raw['ancient']['options']: option.pop('lethal_warning')
        for preset in ('full', 'default', 'summary'):
            result = await GameTools(ContractReply(raw)).inspect_ancient({'preset': preset})
            self.assertNotIn('error', result)
            self.assertTrue(all('lethal_warning' not in o for o in result['ancient']['options']))

    async def test_invalid_filter_is_local_and_keeps_existing_permission(self):
        for value in (True, '4', [True], [-1], [2147483648], ['4'], [None], {}):
            client = ContractReply(details()); tools = GameTools(client); tools.snapshot_id = 'old'
            result = await tools.inspect_ancient({'option_ids': value})
            self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertIn('option_ids', result['error']['message'])
            self.assertEqual(client.calls, [])
            self.assertEqual(tools.snapshot_id, 'old')

    async def test_read_rejection_keeps_old_permission_without_granting_new_one(self):
        for initial in (None, 'old'):
            tools = GameTools(ContractReply({}, {'code': 'illegal_action',
                'public_message': 'Close the map with close_map before inspecting the ancient.'}))
            tools.snapshot_id = initial
            result = await tools.inspect_ancient({'preset': 'summary', 'option_ids': []})
            self.assertEqual(result['error']['code'], 'illegal_action')
            self.assertIn('close_map', result['error']['message'])
            self.assertEqual(tools.snapshot_id, initial)
            self.assertEqual(result['error']['recovery'], 'choose_legal_action' if initial else 'get_observation')
