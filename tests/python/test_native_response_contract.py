"""Protocol options, context and execution facts stay outside public gameplay data."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from sts2_mcp.game_tools import GameTools
from sts2_mcp.roundtrip_client import Client
from sts2_mcp.output.response_pipeline import decode_success
from tests.python.test_tool_contracts import DATA


class TransportOptionsTests(unittest.TestCase):
    def test_response_options_are_request_metadata_and_legacy_calls_omit_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'responses').mkdir()
            client = Client(root, timeout=1)
            for number, options in [(1, None), (2, {'include_divination_image': False})]:
                request_id = f'{number:032x}'
                (root/'responses'/f'{request_id}.json').write_text(json.dumps({'id': request_id, 'ok': True, 'state': {}}))
                client.call('get_state', request_id=request_id, response_options=options)
                request = json.loads((root/'requests'/f'{request_id}.json').read_text())
                self.assertNotIn('arguments', request)
                if options is None: self.assertNotIn('response_options', request)
                else: self.assertEqual(request['response_options'], options)

    def test_new_schema_details_require_and_preserve_same_snapshot_context(self):
        states = json.loads((DATA/'states.json').read_text())
        cases = [('inspect_hand', 'hand', None), ('inspect_targets', 'targets', {'card_id': 7}),
                 ('inspect_potions', 'potions', None), ('inspect_relics', 'relics', None)]
        for operation, key, arguments in cases:
            raw = {**states[key], 'schema_version': 35, 'scene': 'event',
                   'screen': {'status': 'covered', 'view': 'map'}}
            with self.subTest(operation=operation):
                result = decode_success(operation, raw, arguments)
                self.assertEqual(result['scene'], 'event')
                self.assertEqual(result['screen'], {'status': 'covered', 'view': 'map'})
                self.assertNotIn('schema_version', result)
                for missing in ('scene', 'screen'):
                    bad = dict(raw); bad.pop(missing)
                    with self.assertRaises((ValueError, KeyError)): decode_success(operation, bad, arguments)


class MediaClient:
    def __init__(self, state):
        self.state = copy.deepcopy(state)
        self.options = []
        self.error = None
        self.execution = None

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.options.append(response_options)
        if self.error:
            result = {'ok': False, 'error': copy.deepcopy(self.error)}
        else:
            state = copy.deepcopy(self.state)
            if response_options and not response_options['include_divination_image']:
                state.pop('divination_image', None)
            result = {'ok': True, 'state': state}
        if self.execution is not None: result['execution'] = self.execution
        return result


class NativeMediaTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_outputs_with_boards_require_native_media(self):
        states = json.loads((DATA/'states.json').read_text())
        for tool, arguments, required in [
            ('get_observation', {}, True), ('get_observation', {'preset': 'full'}, True),
            ('get_observation', {'preset': 'summary'}, True), ('get_observation', {'preset': 'actions_only'}, False),
            ('get_observation', {'preset': 'top_bar'}, False), ('inspect_event', {}, True),
            ('close_map', {}, False), ('close_card_view', {}, False),
            ('divine', {'x': 1, 'y': 2}, False), ('set_divination_tool', {'tool': 'small'}, False)]:
            with self.subTest(tool=tool, arguments=arguments):
                raw = copy.deepcopy(states['divination'])
                raw['transition'] = {'complete': True, 'stop_reason': 'action_completed', 'events': []}
                client = MediaClient(raw); tools = GameTools(client); tools.snapshot_id = raw['snapshot_id']
                result = await getattr(tools, tool)(arguments)
                self.assertNotIn('error', result)
                self.assertEqual(client.options, [{'include_divination_image': required}])
                self.assertEqual(getattr(result, 'image', None) is not None, required)

    async def test_execution_facts_never_authorize_contradictory_unsubmitted_play(self):
        states = json.loads((DATA/'states.json').read_text())
        for execution in [
            {'ui_interaction_started': True, 'action_submission_observed': False, 'state_captured': True},
            {'ui_interaction_started': False, 'action_submission_observed': True, 'state_captured': True},
            {'ui_interaction_started': 'bad', 'action_submission_observed': False, 'state_captured': False}]:
            with self.subTest(execution=execution):
                client = MediaClient(states['observation']); tools = GameTools(client); tools.snapshot_id = 'existing'
                client.error = {'code': 'illegal_action', 'action_submitted': False}
                client.execution = execution
                result = await tools.play_card({'card_id': 7})
                self.assertIn('error', result)
                self.assertIsNone(tools.snapshot_id)
                self.assertNotIn('execution', result)
