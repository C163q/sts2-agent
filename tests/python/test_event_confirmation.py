import copy
import json
import unittest

from sts2_mcp.output.game_output import observation_details
from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_events import state as event_state


def state():
    raw = event_state()
    raw.update(snapshot_id='dialog-1', top_bar=None, screen={'status': 'visible', 'view': 'confirmation'},
               available_actions=['respond_to_confirmation'], confirmation={
                   'status': 'visible', 'type': 'abandon_run', 'title': 'Abandon Run?',
                   'description': 'Are you sure you want to abandon your run?',
                   'options': [{'id': 'confirm', 'text': 'Confirm', 'enabled': True},
                               {'id': 'cancel', 'text': 'Cancel', 'enabled': True}],
                   'private_owner': 'Trial'})
    raw['event'] = {'status': 'covered', **dict.fromkeys(('name', 'description', 'options', 'proceed'))}
    return raw


class ConfirmationOutputTests(unittest.TestCase):
    def test_modal_rejects_exposed_underlying_state_and_unusable_action(self):
        for mutate in (lambda r: r.update(top_bar=event_state()['top_bar']),
                       lambda r: r.update(turn=1),
                       lambda r: [option.update(enabled=False) for option in r['confirmation']['options']]):
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises(ValueError): observation_details(raw)

    def test_observation_preserves_dialog_and_removes_private_owner(self):
        result = player_result({'ok': True, 'state': observation_details(state())})
        self.assertEqual(result['confirmation']['title'], 'Abandon Run?')
        self.assertEqual([o['id'] for o in result['confirmation']['options']], ['confirm', 'cancel'])
        self.assertNotIn('private_owner', json.dumps(result))
        self.assertNotIn('interaction', result.get('notes', {}))
        self.assertIsNone(result['event']['description'])

    def test_incomplete_or_inconsistent_dialog_cannot_grant_action_permission(self):
        mutations = [lambda r: r.pop('confirmation'), lambda r: r['confirmation'].pop('title'),
                     lambda r: r['confirmation'].update(type='delete_save'),
                     lambda r: r['confirmation']['options'].pop(),
                     lambda r: r['confirmation']['options'][1].update(id='confirm'),
                     lambda r: r['confirmation']['options'][1].update(enabled=1),
                     lambda r: r['screen'].update(status='covered'),
                     lambda r: r.update(scene='shop'),
                     lambda r: r.update(event=event_state()['event']),
                     lambda r: r['available_actions'].append('choose_event_option')]
        for mutate in mutations:
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)):
                observation_details(raw)

    def test_unknown_dialog_keeps_manual_boundary_without_response_action(self):
        raw = state(); raw['confirmation'] = None
        raw.update(screen={'status': 'covered', 'view': 'confirmation'}, available_actions=[])
        raw['transition'] = {'complete': True, 'stop_reason': 'manual_input_required', 'events': []}
        result = player_result({'ok': True, 'state': inspection_details('choose_event_option', raw)})
        self.assertIsNone(result['confirmation'])
        self.assertEqual(result['available_actions'], [])
        self.assertIn('manual input', result['notes']['interaction'])


class ConfirmationClient:
    def __init__(self): self.raw = state(); self.calls = []
    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'respond_to_confirmation':
            if arguments['option'] == 'cancel':
                self.raw = event_state()
                self.raw['confirmation'] = None
                self.raw.update(snapshot_id='event-after-cancel', transition={
                    'complete': True, 'stop_reason': 'action_completed', 'events': []})
            else:
                self.raw = event_state()
                self.raw.update(snapshot_id='run-ended', confirmation=None, available_actions=[],
                                transition={'complete': True, 'stop_reason': 'run_lost', 'events': []})
        if operation == 'choose_event_option':
            self.raw = state()
            self.raw.update(snapshot_id='dialog-2', transition={
                'complete': True, 'stop_reason': 'action_completed', 'events': []})
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class ConfirmationSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancel_reopen_and_confirm_reuse_complete_action_observations(self):
        client = ConfirmationClient(); tools = GameTools(client)
        self.assertEqual((await tools.respond_to_confirmation({'option': 'cancel'}))['error']['code'], 'observation_required')
        await tools.get_observation()
        cancelled = await tools.respond_to_confirmation({'option': 'cancel'})
        self.assertEqual(cancelled['available_actions'], ['choose_event_option'])
        opened = await tools.choose_event_option({'option_id': 0})
        self.assertEqual(opened['available_actions'], ['respond_to_confirmation'])
        ended = await tools.respond_to_confirmation({'option': 'confirm'})
        self.assertEqual(ended['transition']['stop_reason'], 'run_lost')
        self.assertEqual(ended['available_actions'], [])
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual(client.calls[-1], ('respond_to_confirmation', 'dialog-2', {'option': 'confirm'}))

    async def test_invalid_response_never_reaches_game_and_revokes_permission(self):
        for args in (None, {}, {'option': True}, {'option': 1}, {'option': 'yes'},
                     {'option': ['cancel']}, {'option': 'cancel', 'extra': 1}):
            client = ConfirmationClient(); tools = GameTools(client); await tools.get_observation()
            with self.subTest(args=args):
                result = await tools.respond_to_confirmation(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(len(client.calls), 1)
                self.assertIsNone(tools.snapshot_id)

    async def test_missing_dialog_revokes_permission_instead_of_accepting_buttons(self):
        client = ConfirmationClient(); client.raw.pop('confirmation')
        tools = GameTools(client)
        self.assertEqual((await tools.get_observation())['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_stdio_returns_dialog_and_executes_explicit_response(self):
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER

        class DialogGame(FakeGame):
            def run(self):
                client = ConfirmationClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text())
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(response)); temporary.replace(target)
                        path.unlink()

        with DialogGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory), '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    observed = await session.call_tool('get_observation', {})
                    self.assertEqual(observed.structuredContent['confirmation']['type'], 'abandon_run')
                    cancelled = await session.call_tool('respond_to_confirmation', {'option': 'cancel'})
                    self.assertFalse(cancelled.isError)
                    self.assertEqual(cancelled.structuredContent, json.loads(cancelled.content[0].text))
                    self.assertNotIn('confirmation', cancelled.structuredContent)
                    observed = await session.call_tool('get_observation', {})
                    self.assertIsNone(observed.structuredContent['confirmation'])


if __name__ == '__main__': unittest.main()
