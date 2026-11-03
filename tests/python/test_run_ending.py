import copy
import unittest

from sts2_mcp.output.game_output import observation_details
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.transition_details import end_turn_details
from sts2_mcp.output.action_output import action_result
from sts2_mcp.game_tools import GameTools
from tests.python.test_events import state as event_state


def state(phase='outcome'):
    raw = event_state()
    raw.update(snapshot_id='result-1', scene='run_result', top_bar=None, event=None,
               screen={'status': 'visible', 'view': 'run_result'}, available_actions=['run_result_option'],
               run_result={'status': 'visible', 'phase': phase, 'title': 'Victory?', 'texts': ['Your damage: 100'],
                           'score_lines': [], 'badges': [], 'discoveries': [], 'cards': [], 'relics': [], 'potions': [],
                           'options': [{'id': 'continue', 'text': 'Continue', 'enabled': True}]})
    return raw


def epilogue_deck_state():
    raw = event_state()
    raw.update(snapshot_id='epilogue-deck-1', scene='epilogue', event=None,
               screen={'status': 'covered', 'view': 'deck'},
               epilogue={'status': 'covered', 'dialogue': None, 'continue': None, 'proceed': None},
               available_actions=['inspect_potions', 'inspect_relics', 'inspect_deck',
                                  'close_card_view', 'inspect_map'])
    return raw


class EndingOutputTests(unittest.TestCase):
    def test_run_won_preserves_visible_story_death_and_victory_title(self):
        raw = state()
        raw['run_result']['title'] = 'Victory...?'
        death = {'sequence': 1, 'type': 'hp_changed',
                 'target': {'id': 0, 'kind': 'player', 'name': 'The Ironclad'},
                 'before': 25, 'after': 0}
        raw['transition'] = {'stop_reason': 'run_won', 'complete': True, 'events': [death]}
        result = end_turn_details(raw)
        self.assertEqual(result['run_result']['title'], 'Victory...?')
        self.assertEqual(result['transition'], raw['transition'])
        self.assertEqual(result['available_actions'], [])
        receipt = action_result(result)
        self.assertEqual(receipt['transition'], raw['transition'])
        self.assertNotIn('run_result', receipt)
        raw['transition']['stop_reason'] = 'run_won?'
        with self.assertRaises(ValueError): end_turn_details(raw)

    def test_result_filters_private_history_and_preserves_visible_victory_question(self):
        raw = state(); raw['run_result'].update(future_score=123, saved_seed='SECRET')
        result = observation_details(raw)
        self.assertEqual(result['run_result']['title'], 'Victory?')
        self.assertNotIn('saved_seed', result['run_result'])
        self.assertEqual(result['run_result']['score_lines'], [])

    def test_stage_and_visibility_are_validated_before_action_permission(self):
        changes = [lambda r: r.pop('run_result'), lambda r: r['run_result'].update(phase='random'),
                   lambda r: r['run_result']['options'].append(r['run_result']['options'][0]),
                   lambda r: r.update(top_bar={}), lambda r: r['screen'].update(view='map'),
                   lambda r: r['run_result'].update(score_lines=[{'label': 'Floors', 'value': '+50'}]),
                   lambda r: r['run_result'].update(badges=[{'name': 'Bad', 'rarity': 'secret'}]),
                   lambda r: r['run_result']['options'][0].update(enabled=False)]
        for change in changes:
            raw = state(); change(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)): observation_details(raw)

    def test_detail_hover_help_is_only_accepted_by_dedicated_inspection(self):
        raw = state('summary'); raw['run_result']['hover_tips'] = [
            {'source': 'discovery:cards', 'title': 'Cards', 'description': 'Discovered 12 cards\n\nA\n....'}]
        self.assertNotIn('hover_tips', observation_details(raw)['run_result'])
        details = inspection_details('inspect_run_result', raw)
        self.assertEqual(details['run_result']['hover_tips'], raw['run_result']['hover_tips'])

    def test_epilogue_contains_current_line_and_no_future_dialogue(self):
        raw = event_state()
        raw.update(scene='epilogue', event=None, available_actions=['advance_dialogue'],
                   screen={'status': 'visible', 'view': 'epilogue'},
                   epilogue={'status': 'visible', 'dialogue': {'speaker': 'The Architect', 'text': 'Welcome.'},
                             'continue': {'text': 'Respond', 'enabled': True}, 'proceed': None,
                             'future_lines': ['Secret']})
        result = observation_details(raw)
        self.assertNotIn('future_lines', result['epilogue'])
        self.assertEqual(result['epilogue']['dialogue']['text'], 'Welcome.')
        raw['epilogue']['continue'] = None
        with self.assertRaises(ValueError): observation_details(raw)


class EndingSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_epilogue_deck_observation_accepts_visible_inspections_in_every_preset(self):
        from tests.python.test_events import EventClient
        client = EventClient()
        client.raw = epilogue_deck_state()
        tools = GameTools(client)
        for preset in ('default', 'full', 'summary', 'actions_only', 'top_bar'):
            with self.subTest(preset=preset):
                result = await tools.get_observation({'preset': preset})
                self.assertNotIn('error', result)
                self.assertEqual(result['screen'], {'status': 'covered', 'view': 'deck'})
                self.assertEqual(result['available_actions'], [
                    'inspect_potions', 'inspect_relics', 'inspect_deck', 'close_card_view', 'inspect_map'])
                self.assertEqual(tools.snapshot_id, 'epilogue-deck-1')
                if preset == 'full':
                    self.assertEqual(result['epilogue'], {
                        'status': 'covered', 'dialogue': None, 'continue': None, 'proceed': None})
                elif preset in ('default', 'summary'):
                    self.assertEqual(result['epilogue'], {'status': 'covered'})

    async def test_result_action_reuses_successful_observation_and_inspection_does_not_refresh_it(self):
        class Client:
            def __init__(self): self.calls = []; self.raw = state()
            def call(self, operation, expected_state=None, arguments=None, response_options=None):
                self.calls.append((operation, expected_state, arguments))
                if operation == 'run_result_option':
                    self.raw = state('summary'); self.raw['snapshot_id'] = 'result-2'
                    self.raw['transition'] = {'complete': True, 'stop_reason': 'action_completed', 'events': []}
                return {'ok': True, 'state': copy.deepcopy(self.raw)}
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        result = await tools.run_result_option({'option_id': 'continue'})
        self.assertNotIn('run_result', result)
        self.assertEqual((await tools.inspect_run_result())['run_result']['phase'], 'summary')
        self.assertEqual(tools.snapshot_id, 'result-2')
        await tools.inspect_run_result()
        self.assertEqual(tools.snapshot_id, 'result-2')
        for args in (None, {}, {'option_id': True}, {'option_id': ''}, {'option_id': 'continue', 'extra': 1}, []):
            await tools.get_observation(); before = len(client.calls)
            self.assertEqual((await tools.run_result_option(args))['error']['code'], 'invalid_request')
            self.assertEqual(len(client.calls), before)
            self.assertEqual(tools.snapshot_id, 'result-2')


class EndingBoundaryTests(unittest.TestCase):
    def test_epilogue_deck_inspections_do_not_allow_underlying_actions(self):
        for action in ('advance_dialogue', 'proceed', 'use_potion', 'discard_potion',
                       'play_card', 'end_turn', 'travel_to_node', 'inspect_hand',
                       'inspect_combatants', 'inspect_targets', 'inspect_pile',
                       'respond_to_confirmation'):
            raw = epilogue_deck_state()
            raw['available_actions'].append(action)
            with self.subTest(action=action), self.assertRaises(ValueError):
                observation_details(raw)

    def test_epilogue_deck_inspections_do_not_reveal_dialogue_or_extend_other_views(self):
        raw = epilogue_deck_state()
        raw['epilogue']['dialogue'] = {'speaker': 'The Architect', 'text': 'Hidden.'}
        with self.assertRaises(ValueError):
            observation_details(raw)
        for view in ('confirmation', 'draw_pile', 'run_result'):
            raw = epilogue_deck_state()
            raw['screen']['view'] = view
            with self.subTest(view=view), self.assertRaises(ValueError):
                observation_details(raw)
        raw = state()
        raw['run_result'].update(status='covered', title=None, texts=[], options=[])
        raw.update(screen={'status': 'covered', 'view': 'run_result'},
                   available_actions=['inspect_potions', 'inspect_relics'])
        with self.assertRaises(ValueError):
            observation_details(raw)

    def test_all_result_phases_and_covered_screens(self):
        from sts2_mcp.output.run_ending_details import PHASES
        for phase in PHASES:
            raw = state(phase)
            self.assertEqual(observation_details(raw)['run_result']['phase'], phase)
            raw['run_result'].update(status='covered', title=None, texts=[], options=[])
            raw.update(screen={'status': 'covered', 'view': 'run_result'}, available_actions=[])
            self.assertEqual(observation_details(raw)['run_result']['status'], 'covered')
            raw['run_result']['texts'] = ['hidden']
            with self.subTest(phase=phase), self.assertRaises(ValueError): observation_details(raw)

    def test_unlock_card_face_and_inspection_hover_help_have_separate_boundaries(self):
        raw = state('unlock')
        raw['run_result']['cards'] = [{'id': 'card:0', 'name': 'Molten Fist', 'description': 'Deal 10 damage.',
                                      'hover_tips': [{'title': 'Vulnerable', 'description': 'Extra damage.'}],
                                      'hidden_upgrade': 'secret'}]
        raw['run_result']['potions'] = [{'name': 'Potion', 'description': 'hover only', 'owner': 'secret', 'hover_tips': []}]
        result = observation_details(raw)['run_result']
        self.assertEqual(result['cards'][0], {'id': 'card:0', 'name': 'Molten Fist', 'description': 'Deal 10 damage.',
                                                   'hover_tips': [{'title': 'Vulnerable', 'description': 'Extra damage.'}]})
        self.assertEqual(result['potions'], [{'name': 'Potion'}])
        detail = inspection_details('inspect_run_result', raw)['run_result']
        self.assertEqual(detail['potions'][0]['description'], 'hover only')
        self.assertNotIn('owner', detail['potions'][0])

    def test_ending_payload_cannot_grant_unrelated_game_actions(self):
        for action in ['play_card', 'end_turn', 'respond_to_confirmation', 'travel_to_node']:
            raw = state(); raw['available_actions'].append(action)
            with self.subTest(action=action), self.assertRaises(ValueError): observation_details(raw)


class EndingStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_public_tools_validate_options_and_return_structured_results(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER

        class EndingGame(FakeGame):
            def run(self):
                current = state()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text()); raw = copy.deepcopy(current)
                        if request['operation'] == 'run_result_option':
                            raw = state('summary')
                            raw.update(snapshot_id='after-continue', transition={'complete': True, 'stop_reason': 'action_completed', 'events': []})
                            current = raw
                        self.operations.append(request)
                        (self.responses / path.name).write_text(json.dumps({'id': request['id'], 'ok': True, 'state': raw}))
                        path.unlink()
        with EndingGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    names = {t.name for t in (await session.list_tools()).tools}
                    self.assertTrue({'inspect_run_result', 'run_result_option'} <= names)
                    await session.call_tool('get_observation', {})
                    before = len(game.operations)
                    bad = await session.call_tool('run_result_option', {'option_id': 'continue', 'extra': 1})
                    self.assertEqual(bad.structuredContent['error']['code'], 'invalid_request')
                    self.assertEqual(len(game.operations), before)
                    await session.call_tool('get_observation', {})
                    result = await session.call_tool('run_result_option', {'option_id': 'continue'})
                    self.assertEqual(result.structuredContent, json.loads(result.content[0].text))
                    self.assertNotIn('run_result', result.structuredContent)
                    details = await session.call_tool('inspect_run_result', {})
                    self.assertEqual(details.structuredContent['run_result']['phase'], 'summary')


class EndingUiHelpTests(unittest.TestCase):
    def test_epilogue_deck_keeps_visible_top_bar_help_available(self):
        raw = epilogue_deck_state()
        raw['available_actions'].append('inspect_ui')
        self.assertIn('inspect_ui', observation_details(raw)['available_actions'])

    def test_unready_result_can_expose_top_bar_help_without_result_actions(self):
        from sts2_mcp.output.game_output import TOP_BAR
        raw = state()
        raw['run_result'].update(status='not_ready', title=None, texts=[], options=[])
        raw['top_bar'] = {key: None for key in TOP_BAR}
        raw['top_bar'].update(bosses=[], map_visible=False, deck_visible=False, settings_visible=False)
        raw['available_actions'] = ['inspect_ui']
        self.assertEqual(observation_details(raw)['available_actions'], ['inspect_ui'])

    def test_result_without_visible_top_bar_rejects_ui_help(self):
        raw = state()
        raw['available_actions'] = ['inspect_ui']
        with self.assertRaises(ValueError): observation_details(raw)
