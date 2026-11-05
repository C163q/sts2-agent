"""Rest-site summaries share observation fields while validating complete native details."""
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_rest_site import state
from tests.python.test_tool_contracts import ContractReply


def details():
    raw = state()
    raw['rest_site']['description'] = 'Heal 24 HP.'
    for option, text in zip(raw['rest_site']['options'], ('Heal 24 HP.', 'No cards can be upgraded.')):
        option['description'] = text
    return raw


class RestSitePresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_and_observation_share_static_fields_without_any_description(self):
        expected = {'status': 'visible', 'prompt': 'What would you like to do?', 'options': [
            {'id': 'HEAL', 'text': 'Rest', 'enabled': True},
            {'id': 'SMITH', 'text': 'Smith', 'enabled': False}]}
        summary = await GameTools(ContractReply(details())).inspect_rest_site({'preset': 'summary'})
        self.assertNotIn('error', summary)
        self.assertEqual(summary['rest_site'], expected)
        for preset in ('full', 'default', 'summary'):
            observed = await GameTools(ContractReply(details())).get_observation({'preset': preset})
            self.assertNotIn('error', observed)
            want = {**expected, 'proceed': None} if preset == 'full' else expected
            self.assertEqual(observed['rest_site'], want)

    async def test_default_and_full_keep_current_and_option_help(self):
        for preset in ('default', 'full'):
            client = ContractReply(details()); tools = GameTools(client)
            value = await tools.inspect_rest_site({'preset': preset, 'option_ids': None})
            self.assertNotIn('error', value)
            self.assertEqual(value['rest_site']['description'], 'Heal 24 HP.')
            self.assertEqual(value['rest_site']['options'][1]['description'], 'No cards can be upgraded.')
            self.assertEqual('proceed' in value['rest_site'], preset == 'full')
            self.assertEqual(client.calls, [{'operation': 'inspect_rest_site', 'expected_state': None, 'arguments': None}])
            self.assertEqual(tools.snapshot_id, 'rest-1')

    async def test_filter_preserves_order_and_reports_missing_ids_together(self):
        for preset in ('full', 'default', 'summary'):
            for requested, want, missing in [(None, ['HEAL', 'SMITH'], []), ([], [], []),
                    (['SMITH'], ['SMITH'], []), (['SMITH', 'HEAL', 'SMITH'], ['HEAL', 'SMITH'], []),
                    (['X', 'SMITH', 'Y', 'X'], ['SMITH'], ['X', 'Y']), (['heal'], [], ['heal'])]:
                with self.subTest(preset=preset, requested=requested):
                    value = await GameTools(ContractReply(details())).inspect_rest_site({'preset': preset, 'option_ids': requested})
                    self.assertNotIn('error', value)
                    self.assertEqual([o['id'] for o in value['rest_site']['options']], want)
                    self.assertEqual(value['rest_site']['prompt'], 'What would you like to do?')
                    self.assertEqual(value.get('errors', []), [{'code': 'option_ids_not_found', 'option_ids': missing}] if missing else [])
                    self.assertTrue(all(('description' in o) == (preset != 'summary') for o in value['rest_site']['options']))

    async def test_filter_keeps_page_proceed_and_full_empty_state(self):
        raw = details(); raw['rest_site'].update(prompt=None, description=None, options=[],
            proceed={'text': 'Proceed', 'enabled': True})
        for preset in ('full', 'default', 'summary'):
            result = await GameTools(ContractReply(raw)).inspect_rest_site({'preset': preset, 'option_ids': []})
            self.assertNotIn('error', result)
            self.assertEqual(result['rest_site']['proceed'], {'text': 'Proceed', 'enabled': True})
            self.assertEqual(result['rest_site']['options'], [])
            self.assertEqual('prompt' in result['rest_site'], preset == 'full')

    async def test_unavailable_help_uses_ids_and_tracks_filter_and_summary(self):
        raw = details()
        raw['rest_site']['options'][1]['description'] = None
        raw['unavailable_hover_sources'] = ['rest_site.options.SMITH']
        for preset in ('full', 'default', 'summary'):
            for requested in (None, [], ['HEAL'], ['SMITH']):
                with self.subTest(preset=preset, requested=requested):
                    value = await GameTools(ContractReply(raw)).inspect_rest_site({'preset': preset, 'option_ids': requested})
                    self.assertNotIn('error', value)
                    notes = value.get('notes', {})
                    if preset != 'summary' and requested in (None, ['SMITH']):
                        self.assertEqual(notes['hover_tips_unavailable']['sources'], ['rest_site.options.SMITH'])
                    else: self.assertNotIn('hover_tips_unavailable', notes)
                    for option in value['rest_site']['options']:
                        if option['id'] == 'SMITH':
                            self.assertEqual('description' in option, preset == 'full')
                            if preset == 'full': self.assertIsNone(option['description'])

    async def test_context_mismatch_never_refreshes_permission_even_with_empty_filter(self):
        for screen in ({'status': 'covered'}, {'status': 'covered', 'view': 'map'},
                       {'status': 'covered', 'view': 'deck'}, {'status': 'hidden'},
                       {'status': 'visible', 'view': 'selection'}):
            for preset in ('full', 'default', 'summary'):
                with self.subTest(screen=screen, preset=preset):
                    raw = details(); raw['screen'] = screen
                    tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'old'
                    result = await tools.inspect_rest_site({'preset': preset, 'option_ids': []})
                    self.assertEqual(result['error']['code'], 'transport_error')
                    self.assertIsNone(tools.snapshot_id)

    async def test_filter_cannot_hide_invalid_full_rows_or_hover_evidence(self):
        mutations = [lambda r: r['rest_site']['options'][1].pop('description'),
            lambda r: r['rest_site']['options'][1].update(description=None),
            lambda r: r.update(unavailable_hover_sources=['rest_site.options.UNKNOWN']),
            lambda r: r.update(unavailable_hover_sources=['rest_site.options.HEAL', 'rest_site.options.HEAL'])]
        for mutate in mutations:
            for preset in ('full', 'summary'):
                raw = details(); mutate(raw)
                tools = GameTools(ContractReply(raw)); tools.snapshot_id = 'old'
                result = await tools.inspect_rest_site({'preset': preset, 'option_ids': []})
                self.assertEqual(result['error']['code'], 'transport_error')
                self.assertIsNone(tools.snapshot_id)

    async def test_invalid_filters_are_local_and_preserve_permission(self):
        for value in ('HEAL', [1], [True], [''], ['  '], ['X' * 129], {}):
            with self.subTest(value=value):
                client = ContractReply(details()); tools = GameTools(client); tools.snapshot_id = 'old'
                result = await tools.inspect_rest_site({'option_ids': value})
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertIn('option_ids', result['error']['message'])
                self.assertEqual(tools.snapshot_id, 'old')
                self.assertEqual(client.calls, [])

    async def test_pure_read_rejection_keeps_old_permission_but_does_not_create_one(self):
        for initial in (None, 'old'):
            tools = GameTools(ContractReply({}, {'code': 'illegal_action',
                'public_message': 'Close the map with close_map before inspecting rest options.'}))
            tools.snapshot_id = initial
            result = await tools.inspect_rest_site({'preset': 'summary', 'option_ids': []})
            self.assertEqual(result['error']['code'], 'illegal_action')
            self.assertEqual(tools.snapshot_id, initial)
            self.assertEqual(result['error']['recovery'], 'choose_legal_action' if initial else 'get_observation')
