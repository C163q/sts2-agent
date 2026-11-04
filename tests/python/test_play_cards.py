"""Batch input contracts, control receipts and permission recovery."""
import copy
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.action_output import action_result
from sts2_mcp.request_arguments import normalize_request
from sts2_mcp.tool_registry import TOOLS
from tests.python.test_action_observations import Client
from tests.python.test_output_boundaries import observation
from tests.python.test_selection import selection


def batch(status='played', reason=None):
    return {'batch_id': 'test-batch', 'results': [
        {'index': 0, 'card_id': 7, 'target_id': 3, 'status': status, 'reason': reason}]}


def state(receipt=None):
    return {**observation(), 'card_plays': receipt if receipt is not None else batch(),
            'transition': {'stop_reason': 'player_ready', 'complete': True, 'events': []}}


class BatchContractTests(unittest.TestCase):
    def test_unknown_choice_keeps_results_but_not_game_actions(self):
        from sts2_mcp.game_session import can_continue
        raw = state(batch('unknown', 'The result could not be confirmed.'))
        raw.update(selection=selection(), available_actions=['select_card', 'selection_option', 'inspect_selection'])
        raw['transition']['stop_reason'] = 'choice_required'
        self.assertFalse(can_continue(raw))
        for operation in ('play_cards', 'select_card'):
            arguments = {'cards': [{'card_id': 7, 'target_id': 3}]} if operation == 'play_cards' else None
            result = inspection_details(operation, raw, arguments)
            self.assertEqual(result['card_plays'], raw['card_plays'])
            self.assertEqual(result['available_actions'], ['inspect_selection'])

    def test_file_cli_sends_validated_array_and_projects_default(self):
        from sts2_mcp import roundtrip_client
        raw = {'ok': True, 'state': {**state(), 'snapshot_id': 'fixture-state'}}
        output = io.StringIO()
        argv = ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', 'play_cards',
                '--cards', '[{"card_id":7,"target_id":3}]', '--expected-state', 'before']
        with patch('sys.argv', argv), patch.object(roundtrip_client.Client, 'call', return_value=raw) as call, \
                contextlib.redirect_stdout(output):
            roundtrip_client.main()
        self.assertEqual(call.call_args.kwargs['arguments'], {'cards': [{'card_id': 7, 'target_id': 3}]})
        self.assertNotIn('reason', json.loads(output.getvalue())['card_plays']['results'][0])

    def test_file_cli_rejects_bad_batch_locally(self):
        from sts2_mcp import roundtrip_client
        for value in ('[]', '[{"card_id":7},{"card_id":7}]'):
            output = io.StringIO()
            argv = ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', 'play_cards', '--cards', value]
            with patch('sys.argv', argv), patch.object(roundtrip_client.Client, 'call') as call, \
                    contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
                roundtrip_client.main()
            call.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())['error']['code'], 'invalid_request')

    def test_catalog_and_native_arguments_keep_order_and_separate_preset(self):
        definitions = {t.name: t for t in tool_definitions()}
        self.assertIn('play_cards', definitions)
        schema = definitions['play_cards'].inputSchema
        self.assertEqual(schema['required'], ['cards'])
        self.assertEqual(schema['properties']['cards']['minItems'], 1)
        self.assertFalse(schema['additionalProperties'])
        original = {'cards': [{'card_id': 7, 'target_id': 3}, {'card_id': 9}], 'preset': 'full'}
        args = copy.deepcopy(original)
        request = normalize_request(TOOLS['play_cards'], args)
        self.assertEqual(request.native_arguments, {'cards': original['cards']})
        self.assertEqual(request.preset, 'full')
        self.assertEqual(args, original)

    def test_invalid_arrays_ids_targets_and_fields_are_rejected_before_io(self):
        invalid = [{}, {'cards': None}, {'cards': []}, {'cards': {}}, {'cards': [None]},
            {'cards': [{}]}, {'cards': [{'card_id': True}]}, {'cards': [{'card_id': -1}]},
            {'cards': [{'card_id': 2147483648}]}, {'cards': [{'card_id': 'deck:1'}]},
            {'cards': [{'card_id': 7}, {'card_id': 7, 'target_id': 3}]},
            {'cards': [{'card_id': 7, 'target_id': None}]},
            {'cards': [{'card_id': 7, 'target_id': False}]},
            {'cards': [{'card_id': 7, 'target_id': 4294967296}]},
            {'cards': [{'card_id': 7, 'position': 'top'}]},
            {'cards': [{'card_id': 7}], 'stop_on_error': True}]
        for args in invalid:
            with self.subTest(args=args), self.assertRaises(ValueError):
                normalize_request(TOOLS['play_cards'], args)

    def test_nested_errors_identify_input_item_and_field(self):
        with self.assertRaisesRegex(ValueError, r'cards\[1\]\.target_id'):
            normalize_request(TOOLS['play_cards'], {'cards': [{'card_id': 7}, {'card_id': 8, 'target_id': None}]})

    def test_full_receipt_and_continuation_are_validated_and_projected(self):
        raw = state({**batch(), 'private': 'hidden'})
        raw['card_plays']['results'][0]['model_id'] = 'hidden'
        for operation in ('play_cards', 'select_card', 'selection_option', 'end_turn'):
            arguments = {'cards': [{'card_id': 7, 'target_id': 3}]} if operation == 'play_cards' else None
            payload = inspection_details(operation, raw, arguments)
            self.assertEqual(action_result(payload)['card_plays'], batch())
        raw = state()
        del raw['card_plays']
        with self.assertRaises((ValueError, KeyError)):
            inspection_details('play_cards', raw, {'cards': [{'card_id': 7, 'target_id': 3}]})

    def test_compatibility_projection_keeps_only_valid_batch_fields(self):
        from sts2_mcp.output.player_output import player_result
        raw = state({**batch(), 'raw_action_id': 'private'})
        self.assertEqual(player_result({'ok': True, 'state': raw})['card_plays'], batch())

    def test_inconsistent_or_malformed_receipts_cannot_authorize_actions(self):
        mutations = [lambda d: d.update(batch_id=''), lambda d: d.update(results=[]),
            lambda d: d['results'][0].update(index=True), lambda d: d['results'][0].update(index=1),
            lambda d: d['results'][0].update(card_id=-1), lambda d: d['results'][0].update(card_id=8),
            lambda d: d['results'][0].update(target_id=4), lambda d: d['results'][0].update(status='Finished'),
            lambda d: d['results'][0].update(status='not_submitted'),
            lambda d: d['results'][0].update(status='unknown'),
            lambda d: d['results'][0].pop('reason'),
            lambda d: d['results'].append(copy.deepcopy(d['results'][0]))]
        for mutate in mutations:
            data = batch(); mutate(data)
            with self.subTest(data=data), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details('play_cards', state(data), {'cards': [{'card_id': 7, 'target_id': 3}]})

    def test_ready_boundary_cannot_hide_pending_results(self):
        for status, reason in [('queued', None), ('resolving', None)]:
            with self.subTest(status=status), self.assertRaises(ValueError):
                inspection_details('play_cards', state(batch(status, reason)),
                    {'cards': [{'card_id': 7, 'target_id': 3}]})

    def test_ready_unknown_keeps_data_without_misreporting_transport_failure(self):
        raw = state(batch('unknown', 'The finished action was not visible.'))
        raw['available_actions'] = ['play_card', 'play_cards', 'inspect_hand']
        result = inspection_details('play_cards', raw, {'cards': [{'card_id': 7, 'target_id': 3}]})
        self.assertEqual(result['card_plays'], raw['card_plays'])
        self.assertEqual(result['available_actions'], ['inspect_hand'])


class BatchSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_choice_never_refreshes_first_or_continuation_permission(self):
        for continuation in (False, True):
            client = Client(); client.reason = 'choice_required'
            tools = GameTools(client); await tools.get_observation()
            if continuation:
                client.mutate_reply = lambda s: s.update(card_plays=batch('resolving'))
                result = await tools.play_cards({'cards': [{'card_id': 7, 'target_id': 3}]})
                self.assertNotIn('error', result)
                self.assertIsNotNone(tools.snapshot_id)
            client.mutate_reply = lambda s: s.update(card_plays=batch('unknown', 'Unconfirmed card result.'))
            result = await (tools.select_card({'card_id': 0}) if continuation else
                tools.play_cards({'cards': [{'card_id': 7, 'target_id': 3}]}))
            self.assertNotIn('error', result)
            self.assertEqual(result['card_plays']['results'][0]['status'], 'unknown')
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual((await tools.selection_option({'option_id': 'confirm'}))['error']['code'], 'observation_required')

        client = Client(); client.mutate_reply = lambda s: s.update(card_plays=batch('unknown', 'Finished but unobserved.'))
        tools = GameTools(client); await tools.get_observation()
        result = await tools.play_cards({'cards': [{'card_id': 7, 'target_id': 3}]})
        self.assertNotIn('error', result)
        self.assertEqual(result['card_plays']['results'][0]['status'], 'unknown')
        self.assertIsNone(tools.snapshot_id)

    async def test_omitted_preset_uses_default(self):
        client = Client(); client.mutate_reply = lambda s: s.update(card_plays=batch())
        tools = GameTools(client); await tools.get_observation()
        result = await tools.play_cards({'cards': [{'card_id': 7, 'target_id': 3}]})
        self.assertEqual(result['card_plays']['results'][0],
            {'index': 0, 'card_id': 7, 'target_id': 3, 'status': 'played'})

    async def test_default_compacts_and_full_keeps_ordinary_nulls(self):
        for preset in ('default', 'full'):
            client = Client(); client.mutate_reply = lambda s: s.update(card_plays=batch())
            tools = GameTools(client); await tools.get_observation()
            result = await tools.play_cards({'cards': [{'card_id': 7, 'target_id': 3}], 'preset': preset})
            self.assertNotIn('error', result)
            row = result['card_plays']['results'][0]
            self.assertEqual('reason' in row, preset == 'full')
            self.assertEqual(client.calls[-1][2], {'cards': [{'card_id': 7, 'target_id': 3}]})
            self.assertNotIn('error', await tools.end_turn())

    async def test_bad_input_preserves_permission_and_never_sends(self):
        client = Client(); tools = GameTools(client); await tools.get_observation()
        count, token = len(client.calls), tools.snapshot_id
        result = await tools.play_cards({'cards': [{'card_id': 7}, {'card_id': 7}]})
        self.assertEqual(result['error']['code'], 'invalid_request')
        self.assertEqual(len(client.calls), count)
        self.assertEqual(tools.snapshot_id, token)

    async def test_missing_or_mismatched_response_loses_permission_before_default(self):
        for receipt in (None, {**batch(), 'results': [{**batch()['results'][0], 'card_id': 8}]}):
            client = Client()
            if receipt is not None: client.mutate_reply = lambda s: s.update(card_plays=receipt)
            tools = GameTools(client); await tools.get_observation()
            result = await tools.play_cards({'cards': [{'card_id': 7, 'target_id': 3}]})
            self.assertEqual(result['error']['code'], 'transport_error')
            self.assertIsNone(tools.snapshot_id)

    async def test_explicit_preflight_only_preserves_existing_permission(self):
        class Rejected(Client):
            def call(self, operation, expected_state=None, **kwargs):
                if operation == 'play_cards':
                    return {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False,
                        'public_message': 'Close the map before playing cards.'}}
                return super().call(operation, expected_state, **kwargs)
        tools = GameTools(Rejected()); await tools.get_observation()
        result = await tools.play_cards({'cards': [{'card_id': 7}]})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertNotIn('error', await tools.end_turn())
