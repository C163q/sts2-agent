"""Potion summaries, canonical slot filters and validated recovery."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_server import tool_result
from tests.python.test_action_observations import Client as ActionClient


class PotionClient(ActionClient):
    def __init__(self):
        super().__init__()
        block = {'title': 'Block', 'description': 'Prevents damage.'}
        self.slots = [
            {'name': 'Block Potion', 'description': 'Gain 12 Block.', 'hover_tips': [block]},
            None,
            {'name': 'Block Potion', 'description': 'Gain 12 Block.', 'hover_tips': [block]},
        ]
        self.sources = []
        self.damage = lambda state: None
        self.error = None

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation != 'inspect_potions':
            return super().call(operation, expected_state, arguments, response_options)
        self.calls.append((operation, expected_state, arguments))
        if self.error:
            return {'ok': False, 'error': self.error}
        summary = (arguments or {}).get('level') == 'summary'
        slots = copy.deepcopy(self.slots)
        if summary:
            for slot in slots:
                if slot is not None: slot.update(description=None, hover_tips=[])
        state = {'schema_version': 37, 'snapshot_id': self.token, 'scene': 'combat',
                 'screen': {'status': 'visible'}, 'potion_slots': slots,
                 'slot_tip': None if summary else {'title': 'Potion Slot', 'description': 'Use potions.'},
                 'unavailable_hover_sources': [] if summary else list(self.sources)}
        self.damage(state)
        return {'ok': True, 'state': state}


class PotionPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_and_default_keep_context_null_slots_and_shared_original_indices(self):
        client = PotionClient(); tools = GameTools(client)
        result = await tools.inspect_potions({'preset': 'full'})
        self.assertEqual(result['scene'], 'combat')
        self.assertEqual(result['screen'], {'status': 'visible'})
        self.assertEqual(result['potion_slots'][1], None)
        self.assertEqual(result['hover_tips'][0]['slot_indices'], [0, 2])
        self.assertEqual(await tools.inspect_potions(), result)
        self.assertEqual(client.calls, [('inspect_potions', None, None)] * 2)

    async def test_summary_matches_basic_static_fields_without_hover(self):
        client = PotionClient()
        client.slots[0].update(bouncing=True, usable_here=False, hidden='private')
        result = await GameTools(client).inspect_potions({'preset': 'summary'})
        self.assertEqual(result, {'scene': 'combat', 'screen': {'status': 'visible'}, 'potion_slots': [
            {'name': 'Block Potion', 'bouncing': True, 'usable_here': False}, None, {'name': 'Block Potion'}]})
        self.assertEqual(client.calls, [('inspect_potions', None, {'level': 'summary'})])

    async def test_full_keeps_same_static_flags(self):
        client = PotionClient(); client.slots[0].update(bouncing=True, usable_here=False)
        result = await GameTools(client).inspect_potions({'preset': 'full'})
        self.assertTrue(result['potion_slots'][0]['bouncing'])
        self.assertFalse(result['potion_slots'][0]['usable_here'])

    async def test_omitted_and_null_are_all_empty_list_is_none(self):
        for preset in ('full', 'default', 'summary'):
            tools = GameTools(PotionClient())
            original = await tools.inspect_potions({'preset': preset})
            self.assertEqual(await tools.inspect_potions({'preset': preset, 'slot_indices': None}), original)
            result = await tools.inspect_potions({'preset': preset, 'slot_indices': []})
            self.assertEqual(result['slot_indices'], [])
            self.assertEqual(result['potion_slots'], [])
            self.assertEqual(result.get('hover_tips'), None if preset == 'summary' else [])
            self.assertEqual('slot_tip' in result, preset != 'summary')

    async def test_empty_slot_drops_unrelated_block_tips(self):
        result = await GameTools(PotionClient()).inspect_potions({'slot_indices': [1]})
        self.assertEqual(result['slot_indices'], [1])
        self.assertEqual(result['potion_slots'], [None])
        self.assertEqual(result['hover_tips'], [])

    async def test_filter_deduplicates_preserves_native_order_and_original_tip_links(self):
        client = PotionClient(); original = copy.deepcopy(client.slots)
        result = await GameTools(client).inspect_potions({'slot_indices': [2, 1, 2]})
        self.assertEqual(result['slot_indices'], [1, 2])
        self.assertEqual(result['potion_slots'][0], None)
        self.assertEqual(result['hover_tips'][0]['slot_indices'], [2])
        self.assertEqual(client.slots, original)
        both = await GameTools(client).inspect_potions({'slot_indices': [2, 0]})
        self.assertEqual(both['hover_tips'][0]['slot_indices'], [0, 2])

    async def test_missing_indices_grouped_without_hiding_valid_results(self):
        for preset in ('default', 'full', 'summary'):
            result = await GameTools(PotionClient()).inspect_potions({'preset': preset, 'slot_indices': [90, 2, 70, 90]})
            self.assertEqual(result['slot_indices'], [2])
            self.assertEqual(result['errors'], [{'code': 'potion_slot_indices_out_of_range', 'slot_indices': [90, 70]}])
            self.assertFalse(tool_result(result).isError)

    async def test_unhoverable_slots_keep_identity_and_filter_notes_by_original_position(self):
        client = PotionClient(); client.slots[2].update(description=None, hover_tips=[])
        client.sources = ['potion_slots.2']
        tools = GameTools(client)
        full = await tools.inspect_potions({'preset': 'full', 'slot_indices': [2]})
        self.assertIsNone(full['potion_slots'][0]['description'])
        self.assertEqual(full['notes']['hover_tips_unavailable']['sources'], ['potion_slots.2'])
        compact = await tools.inspect_potions({'slot_indices': [2]})
        self.assertNotIn('description', compact['potion_slots'][0])
        for ids in ([], [0], [1]):
            self.assertNotIn('notes', await tools.inspect_potions({'slot_indices': ids}))
        self.assertNotIn('notes', await tools.inspect_potions({'preset': 'summary'}))

    async def test_bad_nested_values_cannot_hide_behind_summary_or_empty_filter(self):
        for change in (
            lambda s: s['potion_slots'][2].update(description=123),
            lambda s: s['potion_slots'][2].update(bouncing=1),
            lambda s: s['potion_slots'][2].update(usable_here='false'),
            lambda s: s.update(unavailable_hover_sources=['potion_slots.1']),
            lambda s: s['potion_slots'][2]['hover_tips'].append({'title': 'Bad', 'description': False}),
        ):
            for preset in ('full', 'summary'):
                client = PotionClient(); client.damage = change
                tools = GameTools(client); await tools.get_observation()
                result = await tools.inspect_potions({'preset': preset, 'slot_indices': []})
                self.assertEqual(result['error']['code'], 'transport_error')
                self.assertIsNone(tools.snapshot_id)

    async def test_missing_or_false_unavailable_evidence_is_invalid(self):
        for sources in ([], ['potion_slots.1'], ['potion_slots.2', 'potion_slots.2']):
            client = PotionClient(); client.slots[2].update(description=None, hover_tips=[])
            client.sources = sources
            result = await GameTools(client).inspect_potions({'preset': 'full'})
            self.assertEqual(result['error']['code'], 'transport_error')

    async def test_local_invalid_arguments_keep_permission_without_transport(self):
        client = PotionClient(); tools = GameTools(client); await tools.get_observation()
        for args in ({'slot_indices': [-1]}, {'slot_indices': [True]}, {'slot_indices': [1.0]},
                     {'slot_indices': [2147483648]}, {'slot_indices': '1'}, {'slot_index': 0}, {'preset': None}):
            result = await tools.inspect_potions(args)
            self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertEqual(tools.snapshot_id, 'state-1')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('error', await tools.end_turn())

    async def test_rejected_read_retains_old_permission_with_specific_safe_message(self):
        client = PotionClient(); tools = GameTools(client); await tools.get_observation()
        client.error = {'code': 'illegal_action', 'public_message': 'The potion bar is not exposed.'}
        result = await tools.inspect_potions({'preset': 'summary'})
        self.assertEqual(result['error']['message'], 'The potion bar is not exposed.')
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertNotIn('error', await tools.end_turn())

    async def test_empty_and_partial_success_can_authorize_action(self):
        for ids in ([], [1], [50, 2]):
            tools = GameTools(PotionClient())
            self.assertNotIn('error', await tools.inspect_potions({'preset': 'summary', 'slot_indices': ids}))
            self.assertNotIn('error', await tools.end_turn())


class PotionFileTests(unittest.TestCase):
    def run_cli(self, options, client=None):
        import contextlib
        import io
        import json
        from unittest.mock import patch
        from sts2_mcp import roundtrip_client
        client = client or PotionClient()
        output = io.StringIO()
        with patch.object(roundtrip_client, 'Client', return_value=client), \
                patch('sys.argv', ['roundtrip_client', '--ipc-dir', '/tmp/unused-potions', 'inspect_potions', *options]), \
                contextlib.redirect_stdout(output):
            roundtrip_client.main()
        return json.loads(output.getvalue()), client

    def test_cli_summary_and_empty_selection_use_same_projection(self):
        result, client = self.run_cli(['--preset', 'summary', '--slot-indices', '2'])
        self.assertEqual(result['slot_indices'], [2])
        self.assertEqual(result['potion_slots'], [{'name': 'Block Potion'}])
        self.assertNotIn('hover_tips', result)
        self.assertEqual(client.calls[0][2], {'level': 'summary'})
        empty, _ = self.run_cli(['--slot-indices'])
        self.assertEqual(empty['potion_slots'], [])
        self.assertEqual(empty['slot_indices'], [])

    def test_cli_legacy_default_keeps_full_null_fields(self):
        client = PotionClient(); client.slots[2].update(description=None, hover_tips=[])
        client.sources = ['potion_slots.2']
        full, _ = self.run_cli([], client)
        self.assertIsNone(full['potion_slots'][2]['description'])
        compact, _ = self.run_cli(['--preset', 'default'], client)
        self.assertNotIn('description', compact['potion_slots'][2])

    def test_raw_preserves_native_protocol_and_summary_level(self):
        result, client = self.run_cli(['--raw', '--preset', 'summary'])
        self.assertTrue(result['ok'])
        self.assertEqual(result['state']['snapshot_id'], 'state-1')
        self.assertIsNone(result['state']['slot_tip'])
        self.assertEqual(client.calls[0][2], {'level': 'summary'})
