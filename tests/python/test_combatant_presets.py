"""Combatant object selection keeps canonical source addresses and UI boundaries."""
import copy
import json
import unittest

from sts2_mcp.output.combatant_presets import combatant_arguments, combatant_preset
from sts2_mcp.output.player_output import ENEMY_ATTACK_INTENT_NOTE


def payload():
    return {'scene': 'combat', 'screen': {'status': 'visible'},
        'player': {'powers': [{'name': 'Vulnerable', 'amount': 2}],
                   'orb_slots': [None, {'name': 'Lightning', 'passive': 3, 'evoke': None}, None],
                   'sovereign_blades': [{'id': 8, 'name': 'Sovereign Blade'}]},
        'enemies': [
            {'id': 10, 'name': 'A', 'powers': [{'name': 'Vulnerable', 'amount': 2}],
             'intents': [{'category': 'attack', 'value': '5'}]},
            {'id': 11, 'name': 'B', 'powers': [], 'intents': []},
            {'id': 12, 'name': 'C', 'powers': [{'name': 'Vulnerable', 'amount': 2}, {'name': 'Muted', 'amount': 1}],
             'intents': [{'category': 'buff', 'value': None}]}],
        'allies': [{'id': 4, 'name': 'Osty', 'powers': []}],
        'hover_tips': [
            {'title': 'Vulnerable', 'description': 'Receive more damage.',
             'sources': ['player.powers.0', 'enemies.0.powers.0', 'enemies.2.powers.0']},
            {'title': 'Aggressive', 'description': 'Attack for 5.', 'sources': ['enemies.0.intents.0']},
            {'title': 'Lightning', 'description': 'Passive and evoke.', 'sources': ['player.orb_slots.1']}],
        'notes': {'selection': 'Selection pending.', 'enemy_attack_intents': ENEMY_ATTACK_INTENT_NOTE,
            'hover_tips_unavailable': {'message': 'Hover help is currently unavailable for these displayed icons.',
                                     'sources': ['enemies.2.powers.1']}}}


class CombatantPresetTests(unittest.TestCase):
    def setUp(self): self.data = payload()

    def test_summary_keeps_static_objects_without_any_hover_metadata(self):
        result = combatant_preset(self.data, 'summary', None)
        self.assertNotIn('hover_tips', result)
        self.assertNotIn('hover_tips_unavailable', result['notes'])
        self.assertEqual(result['player'], self.data['player'])
        self.assertEqual(result['enemies'], self.data['enemies'])
        self.assertEqual(self.data, payload())

    def test_enemy_group_selects_data_not_just_help(self):
        result = combatant_preset(self.data, 'summary', ['enemies'])
        self.assertEqual(set(result), {'scene', 'screen', 'enemies', 'notes'})
        self.assertEqual(result['enemies'], self.data['enemies'])
        self.assertNotIn('source_indices', result)

    def test_empty_filter_retains_only_context_and_relevant_navigation(self):
        for preset in ('full', 'summary'):
            result = combatant_preset(self.data, preset, [])
            self.assertEqual(result, {'scene': 'combat', 'screen': {'status': 'visible'},
                                      'notes': {'selection': 'Selection pending.'}})

    def test_nested_union_preserves_identity_order_and_canonical_sources(self):
        result = combatant_preset(self.data, 'full',
            ['enemies.2.powers.0', 'enemies.0.intents', 'enemies.2.powers.0'])
        self.assertEqual(result['enemies'], [
            {'id': 10, 'name': 'A', 'intents': self.data['enemies'][0]['intents']},
            {'id': 12, 'name': 'C', 'powers': [self.data['enemies'][2]['powers'][0]]}])
        self.assertEqual(result['source_indices'], {'enemies': [0, 2], 'enemies.2.powers': [0]})
        self.assertEqual([t['sources'] for t in result['hover_tips']],
                         [['enemies.2.powers.0'], ['enemies.0.intents.0']])
        self.assertNotIn('hover_tips_unavailable', result['notes'])

    def test_real_empty_orb_is_selected_without_fabricating_other_empty_slots(self):
        result = combatant_preset(self.data, 'full', ['player.orb_slots.2'])
        self.assertEqual(result['player'], {'orb_slots': [None]})
        self.assertEqual(result['source_indices'], {'player.orb_slots': [2]})
        self.assertEqual(result['hover_tips'], [])
        self.assertNotIn('enemy_attack_intents', result['notes'])

    def test_empty_container_is_a_valid_selection(self):
        result = combatant_preset(self.data, 'full', ['enemies.1.powers'])
        self.assertEqual(result['enemies'], [{'id': 11, 'name': 'B', 'powers': []}])
        self.assertNotIn('errors', result)

    def test_missing_paths_are_grouped_and_do_not_drop_valid_objects(self):
        missing = ['enemies.20', 'player.powers.00', 'enemies.2.powers.0.name']
        result = combatant_preset(self.data, 'full', ['enemies.2', *missing, 'enemies.20'])
        self.assertEqual([e['id'] for e in result['enemies']], [12])
        self.assertEqual(result['errors'], [{'code': 'combatant_sources_unavailable', 'sources': missing}])
        self.assertEqual(result['hover_tips'][0]['sources'], ['enemies.2.powers.0'])

    def test_unavailable_hover_note_is_trimmed_with_selection(self):
        result = combatant_preset(self.data, 'full', ['enemies.2'])
        self.assertEqual(result['notes']['hover_tips_unavailable']['sources'], ['enemies.2.powers.1'])
        self.assertNotIn('hover_tips_unavailable', combatant_preset(self.data, 'summary', ['enemies.2'])['notes'])

    def test_no_filter_preserves_full_data(self):
        self.assertEqual(combatant_preset(self.data, 'full', None), self.data)

    def test_arguments_distinguish_omitted_null_and_empty(self):
        self.assertEqual(combatant_arguments(None), {'preset': 'full', 'sources': None})
        self.assertEqual(combatant_arguments({'sources': None}), {'preset': 'full', 'sources': None})
        self.assertEqual(combatant_arguments({'preset': 'summary', 'sources': []}), {'preset': 'summary', 'sources': []})
        self.assertEqual(combatant_arguments({'sources': ['enemies', 'enemies']}),
                         {'preset': 'full', 'sources': ['enemies']})
        for bad in (False, [], {'sources': False}, {'sources': [None]}, {'sources': ['']},
                    {'preset': None}, {'enemy_id': 10}):
            with self.subTest(bad=bad), self.assertRaises(ValueError): combatant_arguments(bad)

    def test_errors_are_not_replaced_by_an_empty_selection(self):
        error = {'error': {'code': 'transport_error'}}
        self.assertIs(combatant_preset(error, 'summary', []), error)

from sts2_mcp.game_tools import GameTools
from tests.python.test_action_observations import Client as ActionClient


class CombatantClient(ActionClient):
    def __init__(self):
        super().__init__()
        self.mutate = lambda state: None

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation != 'inspect_combatants': return super().call(operation, expected_state, arguments)
        self.calls.append((operation, expected_state, arguments))
        state = payload(); state.pop('notes')
        state['snapshot_id'] = self.token
        state['unavailable_hover_sources'] = ['enemies.2.powers.1']
        if arguments == {'level': 'summary'}:
            state['hover_tips'] = []
            state['unavailable_hover_sources'] = []
        self.mutate(state)
        return {'ok': True, 'state': state}


class CombatantToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_requests_static_level_and_can_authorize_an_action(self):
        client = CombatantClient(); tools = GameTools(client)
        result = await tools.inspect_combatants({'preset': 'summary', 'sources': ['enemies']})
        self.assertEqual(set(result), {'scene', 'screen', 'enemies', 'notes'})
        self.assertEqual(client.calls[-1], ('inspect_combatants', None, {'level': 'summary'}))
        self.assertNotIn('error', await tools.end_turn())

    async def test_full_requests_details_and_explains_unavailable_hover(self):
        client = CombatantClient(); tools = GameTools(client)
        result = await tools.inspect_combatants({'preset': 'full', 'sources': ['enemies.2']})
        self.assertEqual(client.calls[-1][2], {'level': 'full'})
        self.assertEqual(result['notes']['hover_tips_unavailable']['sources'], ['enemies.2.powers.1'])
        self.assertEqual(result['enemies'][0]['id'], 12)
        self.assertEqual(result['source_indices'], {'enemies': [2]})
        self.assertEqual(result['hover_tips'][0]['sources'], ['enemies.2.powers.0'])

    async def test_empty_filter_still_validates_the_whole_native_response(self):
        client = CombatantClient(); tools = GameTools(client)
        await tools.get_observation()
        client.mutate = lambda state: state['enemies'][0].update(powers=[{'name': 'Bad', 'amount': True}])
        result = await tools.inspect_combatants({'preset': 'summary', 'sources': []})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_bad_arguments_preserve_permission_without_a_native_query(self):
        client = CombatantClient(); tools = GameTools(client)
        await tools.get_observation()
        for args in ({'sources': False}, {'sources': [None]}, {'enemy_id': 10}):
            result = await tools.inspect_combatants(args)
            self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertIn('sources', result['error']['message'])
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.end_turn())

    async def test_bad_unavailable_hover_metadata_is_not_a_successful_empty_selection(self):
        for invalid in (['enemies.99.powers.0'], ['player.orb_slots.0'], ['enemies.2.powers.0'],
                        ['enemies.2.powers.1', 'enemies.2.powers.1'], [False], None):
            with self.subTest(invalid=invalid):
                client = CombatantClient(); tools = GameTools(client)
                await tools.get_observation()
                client.mutate = lambda state: state.update(unavailable_hover_sources=invalid)
                result = await tools.inspect_combatants({'preset': 'full', 'sources': []})
                self.assertEqual(result['error']['code'], 'transport_error')
                self.assertIsNone(tools.snapshot_id)

class CombatantFileClientTests(unittest.TestCase):
    def test_file_client_uses_the_same_summary_and_selection_contract(self):
        import contextlib
        import io
        from unittest.mock import patch
        from sts2_mcp import roundtrip_client
        for sources in (['enemies'], []):
            with self.subTest(sources=sources):
                client = CombatantClient(); output = io.StringIO()
                argv = ['roundtrip_client', '--ipc-dir', '/tmp/unused-combatants',
                        'inspect_combatants', '--preset', 'summary', '--sources', *sources]
                with patch.object(roundtrip_client, 'Client', return_value=client), \
                     patch('sys.argv', argv), contextlib.redirect_stdout(output):
                    roundtrip_client.main()
                result = json.loads(output.getvalue())
                self.assertEqual(client.calls[0][2], {'level': 'summary'})
                self.assertNotIn('hover_tips', result)
                self.assertNotIn('snapshot_id', result)
                self.assertEqual('enemies' in result, bool(sources))
                if not sources: self.assertEqual(set(result), {'scene', 'screen'})

    def test_file_default_reads_full_level_then_omits_null_fields(self):
        import contextlib
        import io
        from unittest.mock import patch
        from sts2_mcp import roundtrip_client
        client = CombatantClient(); output = io.StringIO()
        argv = ['roundtrip_client', '--ipc-dir', '/tmp/unused-combatants',
                'inspect_combatants', '--preset', 'default']
        with patch.object(roundtrip_client, 'Client', return_value=client), \
             patch('sys.argv', argv), contextlib.redirect_stdout(output):
            roundtrip_client.main()
        result = json.loads(output.getvalue())
        self.assertEqual(client.calls[0][2], {'level': 'full'})
        self.assertIn('hover_tips', result)
        self.assertIn('hover_tips_unavailable', result['notes'])
        self.assertNotIn('evoke', result['player']['orb_slots'][1])
        self.assertIsNone(result['player']['orb_slots'][0])

    def test_file_client_rejects_unrelated_arguments_before_native_io(self):
        import contextlib
        import io
        from unittest.mock import patch
        from sts2_mcp import roundtrip_client
        client = CombatantClient(); output = io.StringIO()
        argv = ['roundtrip_client', '--ipc-dir', '/tmp/unused-combatants',
                'inspect_combatants', '--card-id', '1']
        with patch.object(roundtrip_client, 'Client', return_value=client), \
             patch('sys.argv', argv), contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            roundtrip_client.main()
        result = json.loads(output.getvalue())
        self.assertEqual(result['error']['code'], 'invalid_request')
        self.assertIn('--preset', result['error']['message'])
        self.assertEqual(client.calls, [])

    def test_other_observations_do_not_adopt_inspector_only_hover_metadata(self):
        from sts2_mcp.output.player_output import player_result
        from tests.python.test_output_boundaries import observation
        state = observation()
        state['unavailable_hover_sources'] = ['private.unrecognized.path']
        result = player_result({'ok': True, 'state': state}, operation='get_state')
        self.assertNotIn('unavailable_hover_sources', result)
        self.assertNotIn('hover_tips_unavailable', result.get('notes', {}))
