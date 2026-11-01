import copy
import unittest

from game_output import observation_details
from inspection_details import inspection_details
from player_output import player_result
from test_output_boundaries import observation


def state():
    raw = observation()
    raw.update(snapshot_id='event-1', scene='event', turn=None, player=None, enemies=None, buttons=None,
               selection=None, available_actions=['choose_event_option'], event={
                   'status': 'visible', 'name': 'Abyssal Baths', 'description': 'The water is warm.',
                   'options': [{'id': 0, 'title': 'Immerse', 'description': 'Lose 3 HP.', 'enabled': True,
                                'lethal_warning': True, 'rng': 42,
                                'hover_tips': [{'title': 'Max HP', 'description': 'Your maximum health.'}]}],
                   'proceed': None})
    return raw


class EventOutputTests(unittest.TestCase):
    def test_observation_keeps_visible_warning_and_filters_hover_and_hidden_rng(self):
        public = player_result({'ok': True, 'state': observation_details(state())})
        self.assertEqual(public['event']['options'], [{'id': 0, 'title': 'Immerse', 'description': 'Lose 3 HP.',
                                                     'enabled': True, 'lethal_warning': True}])
        self.assertNotIn('rng', str(public))
        self.assertNotIn('snapshot_id', public)

    def test_inspection_adds_current_hover_help(self):
        public = player_result({'ok': True, 'state': inspection_details('inspect_event', state())})
        self.assertEqual(public['event']['options'][0]['hover_tips'],
                         [{'title': 'Max HP', 'description': 'Your maximum health.'}])

    def test_covered_state_cannot_expose_underlying_text_or_options(self):
        raw = state(); raw['event']['status'] = 'covered'
        with self.assertRaises(ValueError): observation_details(raw)
        raw['event'] = {'status': 'covered', **dict.fromkeys(('name', 'description', 'options', 'proceed'))}
        self.assertIsNone(observation_details(raw)['event']['options'])
        with self.assertRaises(ValueError): inspection_details('inspect_event', raw)

    def test_malformed_option_identity_warning_and_buttons_are_rejected(self):
        for mutate in (lambda r: r.pop('event'), lambda r: r['event']['options'][0].update(id=True),
                       lambda r: r['event']['options'][0].update(id=2147483648),
                       lambda r: r['event']['options'][0].pop('lethal_warning'),
                       lambda r: r['event']['options'].append(copy.deepcopy(r['event']['options'][0])),
                       lambda r: r['event'].update(proceed={'enabled': True})):
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)): observation_details(raw)

    def test_noncombat_death_and_unsupported_overlay_revoke_actions(self):
        for reason in ('run_lost', 'manual_input_required'):
            raw = state(); raw['transition'] = {'stop_reason': reason, 'complete': True, 'events': []}
            public = inspection_details('choose_event_option', raw)
            self.assertEqual(public['transition']['stop_reason'], reason)
            self.assertEqual(public['available_actions'], [])

    def test_observation_identifies_unsupported_native_event_views(self):
        for view in ('confirmation',):
            raw = state(); raw['screen'] = {'status': 'covered', 'view': view}; raw['available_actions'] = []
            raw['event'] = {'status': 'covered', **dict.fromkeys(('name', 'description', 'options', 'proceed'))}
            public = player_result({'ok': True, 'state': observation_details(raw)})
            self.assertEqual(public['screen']['view'], view)
            self.assertIn('manual input', public.get('notes', {}).get('interaction', ''))


class EventClient:
    def __init__(self): self.calls = []; self.raw = state()

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'choose_event_option':
            self.raw.update(snapshot_id='event-2', transition={'stop_reason': 'action_completed', 'complete': True, 'events': []},
                            available_actions=['proceed'])
            self.raw['event'].update(options=[], proceed={'text': 'Proceed', 'enabled': True})
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class EventSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_inspection_and_action_snapshot_can_be_reused(self):
        from game_tools import GameTools
        client = EventClient(); tools = GameTools(client)
        await tools.inspect_event()
        result = await tools.choose_event_option({'option_id': 0})
        self.assertEqual(result['available_actions'], ['proceed'])
        self.assertNotIn('error', await tools.proceed())
        self.assertEqual(client.calls[-1], ('proceed', 'event-2', None))

    async def test_invalid_arguments_never_reach_game(self):
        from game_tools import GameTools
        for arguments in ({'option_id': True}, {'option_id': -1}, {'option_id': 2147483648}, {'option_id': '0'},
                          {'option_id': 0, 'extra': 0}, {}, None):
            client = EventClient(); tools = GameTools(client); await tools.get_observation()
            self.assertEqual((await tools.choose_event_option(arguments))['error']['code'], 'invalid_request')
            self.assertEqual(len(client.calls), 1)

    async def test_stdio_forwards_event_choice_and_preserves_structured_output(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from test_mcp_server import FakeGame, SERVER

        class EventGame(FakeGame):
            def run(self):
                client = EventClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text()); self.operations.append(request)
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(response)); temporary.replace(target)
                        path.unlink()

        with EventGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory), '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.call_tool('get_observation', {})
                    result = await session.call_tool('choose_event_option', {'option_id': 0})
                    self.assertNotIn('error', result.structuredContent)
                    self.assertEqual(json.loads(result.content[0].text), result.structuredContent)
            self.assertEqual(game.operations[-1]['arguments'], {'option_id': 0})
