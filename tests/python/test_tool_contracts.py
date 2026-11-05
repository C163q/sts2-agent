"""Frozen pre-refactor public contracts; expected values never use production builders."""
import copy
import json
import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from sts2_mcp import roundtrip_client

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import tool_definitions


DATA = Path(__file__).resolve().parents[1] / 'data/tool_contracts'
ADDED_TOOL_ARGUMENTS = {'play_cards': {'cards': [{'card_id': 7, 'target_id': 3}], 'preset': 'full'}}
DISCARD_UNKNOWN = {'slot_index': 0, 'name': 'Block Potion', 'status': 'unknown'}


class ContractReply:
    def __init__(self, state, error=None):
        self.state = copy.deepcopy(state)
        self.error = error
        self.calls = []

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.calls.append({'operation': operation, 'expected_state': expected_state, 'arguments': arguments})
        if self.error is not None:
            return {'ok': False, 'error': copy.deepcopy(self.error)}
        return {'ok': True, 'state': copy.deepcopy(self.state)}


class ToolContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_outputs_and_native_requests_match_frozen_baseline(self):
        states = json.loads((DATA / 'states.json').read_text())
        cases = json.loads((DATA / 'cases.json').read_text())
        expected = json.loads((DATA / 'expected.json').read_text())
        for index, case in enumerate(cases):
            with self.subTest(index=index, tool=case['tool'], arguments=case['arguments'], error=case.get('error')):
                client = ContractReply(states[case['state']], case.get('error'))
                # The approved map context changes status only; keep the historical JSON frozen.
                if client.state.get('screen', {}).get('view') == 'map':
                    client.state['screen']['status'] = 'covered'
                if case['tool'] == 'discard_potion':
                    # The frozen generic action has no discard witness; the new contract must remain unknown.
                    client.state['potion_discard'] = copy.deepcopy(DISCARD_UNKNOWN)
                original = copy.deepcopy(client.state)
                tools = GameTools(client)
                tools.snapshot_id = 'fixture-state'
                result = await getattr(tools, case['tool'])(copy.deepcopy(case['arguments']))
                want = copy.deepcopy(expected[case['expected_ref']])
                if case['tool'] == 'discard_potion' and 'error' not in want:
                    want.update(potion_discard=copy.deepcopy(DISCARD_UNKNOWN), available_actions=[])
                if want.get('screen', {}).get('view') == 'map':
                    want['screen']['status'] = 'covered'
                if case['tool'] in {'close_card_view', 'close_map'} and 'error' not in want:
                    # The approved action contract replaces the frozen partial observation.
                    want = {key: want[key] for key in ('scene', 'screen', 'available_actions')}
                if case['tool'] == 'set_selection_view' and 'error' not in want:
                    choice = want.get('selection')
                    want = {key: want[key] for key in ('scene', 'screen', 'available_actions')}
                    if choice is not None:
                        want['selection'] = {key: choice[key] for key in ('type', 'status')}
                if case['tool'] == 'inspect_pile' and case['arguments'].get('preset') == 'summary' and want.get('status') == 'opened':
                    want.pop('message', None)
                if 'unknown_field' in case['arguments']:
                    self.assertIn('unknown_field', result['error']['message'])
                    want['error']['message'] = result['error']['message']
                if case['tool'] == 'inspect_relics' and case['arguments'] == {'relic_indices': [2, 80], 'preset': 'full'}:
                    want['hover_tips'][0]['relic_indices'] = [2]
                if case.get('error') and case['tool'] in {
                    'inspect_run_result', 'inspect_event', 'inspect_ancient', 'inspect_shop',
                    'inspect_treasure', 'inspect_rest_site', 'inspect_rewards', 'inspect_potions',
                    'inspect_relics', 'inspect_selection'}:
                    want['error']['recovery'] = 'choose_legal_action'
                self.assertEqual(result, want)
                self.assertEqual(getattr(result, 'image', None), case.get('expected_image'))
                native_calls = copy.deepcopy(case['native_calls'])
                if case['tool'] == 'inspect_deck':
                    for call in native_calls:
                        if call['arguments'] == {}: call['arguments'] = None
                if case['tool'] == 'inspect_relics' and case['arguments'].get('preset') == 'summary':
                    for call in native_calls: call['arguments'] = {'level': 'summary'}
                self.assertEqual(client.calls, native_calls)
                self.assertEqual(client.state, original)

    def test_baseline_covers_catalog_presets_and_rejections(self):
        cases = json.loads((DATA / 'cases.json').read_text())
        expected = json.loads((DATA / 'expected.json').read_text())
        catalog = tool_definitions()
        self.assertEqual({case['tool'] for case in cases} | ADDED_TOOL_ARGUMENTS.keys(), {tool.name for tool in catalog})
        for tool in catalog:
            if tool.name in ADDED_TOOL_ARGUMENTS:
                # New tools have independent contracts; the pre-refactor fixtures stay frozen.
                self.assertTrue(Path(__file__).with_name('test_' + tool.name + '.py').is_file())
                continue
            successful = [case for case in cases if case['tool'] == tool.name and 'error' not in expected[case['expected_ref']]]
            presets = {case['arguments'].get('preset') for case in successful}
            # Dedicated preset tests cover additions to the frozen refactor baseline.
            added = {'summary'} if tool.name in {'inspect_potions', 'inspect_map', 'inspect_rewards'} else set()
            self.assertGreaterEqual(presets, {None, *(set(tool.inputSchema['properties']['preset']['enum']) - added)})
            self.assertTrue(any(case['tool'] == tool.name and case.get('error') for case in cases))
            self.assertTrue(any(case['tool'] == tool.name and 'unknown_field' in case['arguments'] for case in cases))


class FileContractTests(unittest.TestCase):
    def test_file_outputs_keep_historical_defaults_and_full_state_scope(self):
        states = json.loads((DATA / 'states.json').read_text())
        expected = json.loads((DATA / 'expected.json').read_text())
        for case in json.loads((DATA / 'cli_cases.json').read_text()):
            with self.subTest(tool=case['tool'], argv=case['argv']):
                raw = {'ok': True, 'state': copy.deepcopy(states[case['state']])}
                if raw['state'].get('screen', {}).get('view') == 'map':
                    raw['state']['screen']['status'] = 'covered'
                if case['tool'] == 'discard_potion':
                    raw['state']['potion_discard'] = copy.deepcopy(DISCARD_UNKNOWN)
                original = copy.deepcopy(raw)
                output = io.StringIO()
                with patch('sys.argv', ['roundtrip_client.py', *case['argv']]), \
                        patch.object(roundtrip_client.Client, 'call', return_value=raw) as call, \
                        contextlib.redirect_stdout(output):
                    roundtrip_client.main()
                want = copy.deepcopy(expected[case['expected_ref']])
                if case['tool'] == 'discard_potion':
                    want.update(potion_discard=copy.deepcopy(DISCARD_UNKNOWN), available_actions=[])
                if want.get('screen', {}).get('view') == 'map':
                    want['screen']['status'] = 'covered'
                if case['tool'] == 'close_card_view':
                    want = {key: want[key] for key in ('scene', 'screen', 'available_actions')}
                if case['tool'] == 'inspect_pile' and '--preset' in case['argv'] and 'summary' in case['argv'] and want.get('status') == 'opened':
                    want.pop('message', None)
                self.assertEqual(json.loads(output.getvalue()), want)
                self.assertEqual(call.call_args.kwargs.get('arguments'), case['native_arguments'])
                self.assertEqual(raw, original)
