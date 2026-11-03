import copy
import json
import sys
import unittest

from sts2_mcp.output.game_output import observation_details
from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_server import tool_result
from tests.python.test_action_observations import Client
from tests.python.test_divination import DivinationClient
from tests.python.test_output_boundaries import observation
from tests.python.test_selection import selection


class ObservationPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_explicit_full_preserve_the_existing_output(self):
        tools = GameTools(Client())
        default = await tools.get_observation()
        self.assertEqual(await tools.get_observation({}), default)
        self.assertEqual(await tools.get_observation({'preset': 'default'}), default)
        self.assertNotIn('selection', default)
        self.assertIsNone((await tools.get_observation({'preset': 'full'}))['selection'])
        self.assertIn('player', default)

    async def test_actions_only_preserves_selection_context_without_candidates_or_notes(self):
        client = Client()
        original = client.call
        def choose(operation, expected_state=None, arguments=None):
            reply = original(operation, expected_state, arguments)
            reply['state'].update(screen={'status': 'covered'}, selection=selection(),
                                  available_actions=['inspect_selection', 'select_card', 'selection_option', 'set_selection_view'])
            reply['state']['selection']['type'] = 'hand'
            return reply
        client.call = choose
        tools = GameTools(client)
        result = await tools.get_observation({'preset': 'actions_only'})
        self.assertEqual(result, {'scene': 'combat', 'screen': {'status': 'covered'},
                                 'selection': {'type': 'hand', 'status': 'visible'},
                                 'available_actions': ['inspect_selection', 'select_card', 'selection_option', 'set_selection_view']})
        self.assertEqual(tools.snapshot_id, 'state-1')
        self.assertEqual(client.calls, [('get_state', None, None)])

    async def test_actions_only_authorizes_action_and_full_observation_remains_available(self):
        client = Client(); tools = GameTools(client)
        compact = await tools.get_observation({'preset': 'actions_only'})
        self.assertEqual(set(compact), {'scene', 'screen', 'available_actions'})
        following = await tools.play_card({'card_id': 0})
        self.assertNotIn('player', following)
        self.assertIn('transition', following)
        self.assertEqual(client.calls[-1], ('play_card', 'state-1', {'card_id': 0}))
        self.assertIn('player', await tools.get_observation())
        client.revision += 1
        self.assertEqual((await tools.end_turn())['error']['code'], 'stale_state')
        self.assertIsNone(tools.snapshot_id)

    async def test_invalid_preset_preserves_permission_and_does_not_contact_game(self):
        for args in ([], '', 0, False, {'preset': None}, {'preset': True}, {'preset': []},
                     {'preset': 'action_only'}, {'preset': 'FULL'}, {'extra': 1}, {'preset': 'full', 'extra': 1}):
            client = Client(); tools = GameTools(client)
            await tools.get_observation()
            with self.subTest(args=args):
                result = await tools.get_observation(args)
                self.assertEqual(result['error']['code'], 'invalid_request')
                self.assertEqual(len(client.calls), 1)
                self.assertEqual(tools.snapshot_id, 'state-1')

    async def test_action_result_with_only_inspections_does_not_continue_action_permission(self):
        client = Client(); tools = GameTools(client)
        await tools.get_observation()
        client.mutate_reply = lambda raw: raw.update(available_actions=['inspect_hand'])
        result = await tools.end_turn()
        self.assertEqual(result['available_actions'], ['inspect_hand'])
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_compact_mode_still_validates_full_observation_and_clears_bad_reply_permission(self):
        class Broken(Client):
            def call(self, *args, **kwargs):
                reply = super().call(*args, **kwargs)
                reply['state']['player']['hp'] = True
                return reply
        tools = GameTools(Broken())
        result = await tools.get_observation({'preset': 'actions_only'})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_compact_divination_has_no_image_and_full_mode_keeps_image(self):
        tools = GameTools(DivinationClient())
        result = tool_result(await tools.get_observation({'preset': 'actions_only'}))
        self.assertEqual([c.type for c in result.content], ['text'])
        self.assertEqual(result.structuredContent, {'scene': 'event', 'screen': {'status': 'visible', 'view': 'divination'},
                                                   'available_actions': ['set_divination_tool', 'divine']})
        full = tool_result(await tools.get_observation())
        self.assertEqual([c.type for c in full.content], ['text', 'image'])


class AvailableToolOutputTests(unittest.TestCase):
    def test_public_details_and_views_survive_but_private_unknown_and_duplicates_do_not(self):
        raw = observation()
        raw['available_actions'] = ['inspect_hand', 'inspect_targets', 'inspect_map', 'end_turn', 'inspect_hand',
                                    'start_test_combat', 'get_observation', 'capture_screenshot', 'unknown']
        self.assertEqual(observation_details(raw)['available_actions'], ['inspect_hand', 'inspect_targets', 'inspect_map', 'end_turn'])

    def test_exposed_map_accepts_only_its_current_views_and_travel(self):
        raw = observation()
        raw.update(screen={'status': 'visible', 'view': 'map'}, player=None, enemies=None, turn=None, buttons=None,
                   map={'status': 'visible', 'act': 1, 'current_node': None, 'can_travel': True,
                        'selectable_nodes': ['map:1:1:0']}, available_actions=['inspect_map', 'close_map', 'inspect_deck',
                        'inspect_potions', 'inspect_relics', 'travel_to_node'])
        self.assertEqual(observation_details(raw)['available_actions'], raw['available_actions'])
        for tool in ('play_card', 'end_turn', 'select_card', 'inspect_hand', 'inspect_selection',
                     'inspect_targets', 'use_potion', 'discard_potion'):
            broken = copy.deepcopy(raw); broken['available_actions'].append(tool)
            with self.subTest(tool=tool), self.assertRaises(ValueError): observation_details(broken)

    def test_noncombat_map_preserves_visible_potion_tools_without_allowing_combat(self):
        from tests.python.test_map_travel import map_observation
        for tools in (['inspect_map', 'inspect_potions', 'travel_to_node'],
                      ['inspect_map', 'inspect_potions', 'inspect_targets', 'use_potion', 'discard_potion', 'travel_to_node']):
            raw = map_observation()
            raw['available_actions'] = tools
            self.assertEqual(observation_details(raw)['available_actions'], tools)

    def test_epilogue_allows_current_native_top_bar_potion_tools(self):
        from tests.python.test_events import state as event_state
        raw = event_state()
        raw.update(scene='epilogue', event=None, screen={'status': 'visible', 'view': 'epilogue'},
                   epilogue={'status': 'visible', 'dialogue': None, 'continue': None,
                             'proceed': {'text': 'Continue', 'enabled': True}},
                   available_actions=['proceed', 'inspect_ui', 'inspect_combatants', 'inspect_relics',
                                      'inspect_potions', 'inspect_targets', 'use_potion', 'discard_potion'])
        self.assertEqual(observation_details(raw)['available_actions'], raw['available_actions'])

    def test_close_map_restores_epilogue_and_current_dialogue_context(self):
        from sts2_mcp.output.map_details import closed_map
        from tests.python.test_events import state as event_state
        raw = event_state()
        raw.update(scene='epilogue', event=None, screen={'status': 'visible', 'view': 'epilogue'},
                   epilogue={'status': 'visible', 'dialogue': {'speaker': 'The Architect', 'text': 'Welcome.'},
                             'continue': {'text': 'Respond', 'enabled': True}, 'proceed': None},
                   available_actions=['advance_dialogue', 'inspect_map'])
        restored = closed_map(raw)
        self.assertEqual(restored['scene'], 'epilogue')
        self.assertEqual(restored['epilogue']['dialogue']['text'], 'Welcome.')
        self.assertEqual(restored['available_actions'], ['advance_dialogue', 'inspect_map'])

    def test_result_details_do_not_require_an_enabled_result_button(self):
        from tests.python.test_run_ending import state
        raw = state(); raw['available_actions'] = ['inspect_run_result']
        raw['run_result']['options'][0]['enabled'] = False
        self.assertEqual(observation_details(raw)['available_actions'], ['inspect_run_result'])
        raw['available_actions'].append('run_result_option')
        with self.assertRaises(ValueError): observation_details(raw)

    def test_choice_action_result_keeps_current_inspections_and_view_switch(self):
        from sts2_mcp.output.transition_details import end_turn_details
        raw = observation()
        raw.update(selection=selection(), screen={'status': 'covered'},
                   available_actions=['inspect_selection', 'select_card', 'selection_option', 'set_selection_view'],
                   transition={'complete': True, 'stop_reason': 'choice_required', 'events': []})
        self.assertEqual(end_turn_details(raw)['available_actions'], raw['available_actions'])


class ObservationPresetStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_schema_presets_and_invalid_arguments(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from tests.python.test_mcp_server import FakeGame, SERVER
        with FakeGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    schema = next(t.inputSchema for t in (await session.list_tools()).tools if t.name == 'get_observation')
                    self.assertEqual(schema['properties']['preset']['enum'], ['default', 'full', 'actions_only', 'summary', 'top_bar'])
                    compact = await session.call_tool('get_observation', {'preset': 'actions_only'})
                    self.assertFalse(compact.isError)
                    self.assertEqual(set(compact.structuredContent), {'scene', 'screen', 'available_actions'})
                    self.assertEqual(json.loads(compact.content[0].text), compact.structuredContent)
                    count = len(game.operations)
                    bad = await session.call_tool('get_observation', {'preset': 'invalid'})
                    self.assertEqual(bad.structuredContent['error']['code'], 'invalid_request')
                    self.assertEqual(len(game.operations), count)
                    full = await session.call_tool('get_observation', {})
                    self.assertIn('player', full.structuredContent)


if __name__ == '__main__':
    unittest.main()
