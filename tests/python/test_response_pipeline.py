"""MCP and file calls validate the same operation before projecting public data."""
import contextlib
import copy
import io
import json
import unittest
from unittest.mock import patch

from sts2_mcp import roundtrip_client
from tests.python.test_tool_contracts import DATA


MALFORMED = {
    'get_state': ('enemies', [None]), 'close_card_view': ('enemies', [None]),
    'close_map': ('enemies', [None]), 'set_selection_view': ('enemies', [None]),
    'set_divination_tool': ('enemies', [None]), 'inspect_hand': ('hand', [None]),
    'inspect_targets': ('targets', [None]), 'inspect_ui': ('hover_tips', [None]),
    'inspect_potions': ('potion_slots', [False]), 'inspect_relics': ('relics', [False]),
    'inspect_combatants': ('enemies', [None]), 'inspect_deck': ('deck', [False]),
    'inspect_pile': ('cards', [False]), 'inspect_map': ('nodes', [False]),
    'inspect_selection': ('selection', False), 'inspect_rewards': ('rewards', False),
    'inspect_rest_site': ('rest_site', False), 'inspect_treasure': ('treasure', False),
    'inspect_shop': ('shop', False), 'inspect_ancient': ('ancient', False),
    'inspect_event': ('event', False), 'inspect_run_result': ('run_result', False),
}


class FileValidationTests(unittest.TestCase):
    def test_each_file_operation_rejects_missing_required_gameplay_data(self):
        states = json.loads((DATA / 'states.json').read_text())
        for case in json.loads((DATA / 'cli_cases.json').read_text()):
            if '--preset' in case['argv']:
                continue
            operation = 'get_state' if case['tool'] == 'get_observation' else case['tool']
            key, value = MALFORMED.get(operation, ('transition', {'events': [None]}))
            raw = {'ok': True, 'state': copy.deepcopy(states[case['state']])}
            raw['state'].pop(key)
            output = io.StringIO()
            with self.subTest(operation=operation), patch('sys.argv', ['roundtrip_client.py', *case['argv']]), \
                    patch.object(roundtrip_client.Client, 'call', return_value=raw), contextlib.redirect_stdout(output):
                with self.assertRaises(SystemExit) as raised:
                    roundtrip_client.main()
                self.assertEqual(raised.exception.code, 1)
                self.assertEqual(json.loads(output.getvalue())['error']['code'], 'transport_error')

    def test_raw_file_output_does_not_apply_gameplay_validation(self):
        raw = {'ok': True, 'state': {'diagnostic': 'unchanged'}}
        output = io.StringIO()
        with patch('sys.argv', ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', 'get_state', '--raw']), \
                patch.object(roundtrip_client.Client, 'call', return_value=raw), contextlib.redirect_stdout(output):
            roundtrip_client.main()
        self.assertEqual(json.loads(output.getvalue()), raw)


class DecodeSuccessTests(unittest.TestCase):
    def test_each_operation_rejects_invalid_state_containers(self):
        from sts2_mcp.output.response_pipeline import decode_success
        cases = json.loads((DATA / 'cases.json').read_text())
        first = {case['tool']: case for case in cases if case['arguments'].get('preset') == 'full' and not case.get('error')}
        for case in first.values():
            operation = case['native_calls'][0]['operation']
            for value in (None, True, 7, 'state', []):
                with self.subTest(operation=operation, state=value), self.assertRaises(ValueError):
                    decode_success(operation, value, case['native_calls'][0]['arguments'])

    def test_each_operation_rejects_malformed_nested_values(self):
        from sts2_mcp.output.response_pipeline import decode_success
        states = json.loads((DATA / 'states.json').read_text())
        cases = json.loads((DATA / 'cases.json').read_text())
        for case in cases:
            if case['arguments'].get('preset') != 'full' or case.get('error') or 'unknown_field' in case['arguments']:
                continue
            request = case['native_calls'][0]
            operation = request['operation']
            key, value = MALFORMED.get(operation, ('transition', {'events': [None]}))
            raw = copy.deepcopy(states[case['state']])
            if operation == 'inspect_event' and (raw.get('divination') or {}).get('status') == 'visible':
                key, value = 'divination', False
            raw[key] = {**raw[key], **value} if key == 'transition' else value
            with self.subTest(operation=operation), self.assertRaises((ValueError, KeyError, TypeError)):
                decode_success(operation, raw, request['arguments'])

    def test_all_operation_readers_strip_unknown_nested_fields_and_preserve_inputs(self):
        from sts2_mcp.output.response_pipeline import decode_success
        states = json.loads((DATA / 'states.json').read_text())
        cases = json.loads((DATA / 'cases.json').read_text())

        def inject(value):
            if isinstance(value, dict):
                return {**{key: inject(item) for key, item in value.items()}, '__private': 'internal diagnostic'}
            if isinstance(value, list):
                return [inject(item) for item in value]
            return value

        for case in cases:
            if case['arguments'].get('preset') != 'full' or case.get('error') or 'unknown_field' in case['arguments']:
                continue
            request = case['native_calls'][0]
            raw = copy.deepcopy(states[case['state']])
            if raw.get('screen', {}).get('view') == 'map':
                raw['screen']['status'] = 'covered'
            if request['operation'] == 'discard_potion':
                raw['potion_discard'] = {'slot_index': 0, 'name': 'Block Potion', 'status': 'unknown'}
            decorated = inject(raw)
            original = copy.deepcopy(decorated)
            with self.subTest(operation=request['operation'], state=case['state']):
                expected = decode_success(request['operation'], raw, request['arguments'])
                self.assertEqual(decode_success(request['operation'], decorated, request['arguments']), expected)
                self.assertEqual(decorated, original)
                self.assertNotIn('__private', json.dumps(expected))
                self.assertNotIn('fixture-state', json.dumps(expected))


class LegacyFileOperationTests(unittest.TestCase):
    def test_file_only_test_start_and_close_deck_keep_complete_observations(self):
        states = json.loads((DATA / 'states.json').read_text())
        cases = json.loads((DATA / 'cli_cases.json').read_text())
        expected = json.loads((DATA / 'expected.json').read_text())
        base = next(case for case in cases if case['tool'] == 'get_observation')
        for operation in ('start_test_combat', 'close_deck'):
            output = io.StringIO()
            with self.subTest(operation=operation), \
                    patch('sys.argv', ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', operation]), \
                    patch.object(roundtrip_client.Client, 'call', return_value={'ok': True, 'state': states['observation']}), \
                    contextlib.redirect_stdout(output):
                roundtrip_client.main()
                self.assertEqual(json.loads(output.getvalue()), expected[base['expected_ref']])
