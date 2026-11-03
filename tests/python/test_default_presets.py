"""Verify default output compaction at tool boundaries, after full validation."""
import copy
import json
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.mcp_server import tool_result
from sts2_mcp.output.divination_details import ImagePayload
from tests.python.test_hand_presets import HandClient
from tests.python.test_relic_presets import RelicClient
from tests.python.test_selection_presets import SelectionClient
from tests.python.test_divination import DivinationClient
from tests.python.test_action_observations import Client


REQUIRED_ARGUMENTS = {
    'run_result_option': {'option_id': 'continue'},
    'travel_to_node': {'node_id': 'map:1:0:0'},
    'respond_to_confirmation': {'option': 'cancel'},
    'set_divination_tool': {'tool': 'big'}, 'divine': {'x': 0, 'y': 0},
    'choose_event_option': {'option_id': 0}, 'choose_ancient_option': {'option_id': 0},
    'buy_item': {'item_id': 0}, 'claim_reward': {'reward_id': 0},
    'choose_rest_option': {'option_id': 'smith'}, 'inspect_targets': {'card_id': 0},
    'play_card': {'card_id': 0}, 'use_potion': {'potion_slot': 0},
    'discard_potion': {'potion_slot': 0}, 'inspect_pile': {'pile': 'discard'},
    'select_card': {'card_id': 0}, 'selection_option': {'option_id': 'skip'},
    'set_selection_view': {'view': 'selection'},
}


class BoundaryProbe(GameTools):
    """Record actual tool routing while isolating native I/O and response validation."""
    payload = {'kept': 0, 'ordinary': None, 'transition': {'events': [
        {'sequence': 1, 'type': 'stars_changed', 'before': None, 'after': 1}]}}

    def __init__(self):
        super().__init__(None)
        self.calls = []

    async def response(self, operation, *args, **kwargs):
        self.calls.append((operation, args, kwargs))
        for value in (*args, *kwargs.values()):
            assert not isinstance(value, dict) or 'preset' not in value, value
        return copy.deepcopy(self.payload)

    _inspect = _change_view = _action = response

    async def _request(self, *args, **kwargs):
        return await self.response(*args, **kwargs), 'probe-state'


class DefaultProjectionTests(unittest.TestCase):
    def apply(self, value, preset='default'):
        from sts2_mcp.output.presets import apply_preset
        return apply_preset(value, preset)

    def test_only_null_object_fields_disappear_without_mutating_input(self):
        value = {'gone': None, 'zero': 0, 'false': False, 'text': '', 'empty': [], 'object': {},
                 'nested': {'gone': None}, 'slots': [None, {'gone': None}, None]}
        original = copy.deepcopy(value)
        expected = {k: v for k, v in value.items() if k != 'gone'}
        expected.update(nested={}, slots=[None, {}, None])
        self.assertEqual(self.apply(value), expected)
        self.assertEqual(value, original)
        self.assertEqual(self.apply(self.apply(value)), expected)
        self.assertEqual(self.apply(value, 'full'), value)

    def test_events_keep_all_existing_nulls_but_do_not_gain_fields(self):
        events = [
            {'sequence': 1, 'type': 'stars_changed', 'before': None, 'after': 1},
            {'sequence': 2, 'type': 'power_changed', 'before': None, 'after': None},
            {'sequence': 3, 'type': 'damage', 'hp_loss': None, 'source': None},
            {'sequence': 4, 'type': 'card_added', 'pile': None, 'card': {'id': 7, 'name': None}},
        ]
        result = self.apply({'transition': {'events': events}, 'before': None, 'source': None})
        self.assertEqual(result, {'transition': {'events': events}})
        self.assertNotIn('actor', result['transition']['events'][0])

    def test_every_preview_keeps_both_subtrees_and_random_unknown_result(self):
        pair = {'before': {'id': 7, 'energy_cost': None},
                'after': {'id': 7, 'energy_cost': '1', 'star_cost': None}}
        choice = {'upgrade_preview': pair, 'upgrade_previews': [pair], 'enchant_previews': [pair],
                  'transform_previews': [{'before': pair['before'], 'after': None, 'random': True}],
                  'cards': [{'id': 7, 'energy_cost': None}], 'prompt': None}
        expected = {**choice, 'cards': [{'id': 7}]}
        del expected['prompt']
        self.assertEqual(self.apply({'selection': choice}), {'selection': expected})
        self.assertEqual(self.apply({'selection': {'upgrade_preview': None}}), {'selection': {}})

    def test_images_survive_and_both_mcp_json_representations_match(self):
        payload = ImagePayload({'gone': None, 'divination': {'tool': None}}, 'aW1hZ2U=')
        result = tool_result(self.apply(payload))
        self.assertEqual([c.type for c in result.content], ['text', 'image'])
        self.assertEqual(result.content[1].data, payload.image)
        self.assertEqual(result.structuredContent, {'divination': {}})
        self.assertEqual(json.loads(result.content[0].text), result.structuredContent)

    def test_errors_and_named_presets_are_unchanged(self):
        value = {'counter': None}
        for preset in ('full', 'summary', 'selectable', 'actions_only'):
            self.assertEqual(self.apply(value, preset), value)
        error = {'error': {'code': 'transport_error', 'outcome': 'unknown'}}
        self.assertEqual(self.apply(error), error)

    def test_all_gameplay_schemas_and_target_branches_offer_default_full(self):
        tools = tool_definitions(screenshots_enabled=True)
        self.assertEqual(len(tools), 43)
        for tool in tools:
            with self.subTest(tool=tool.name):
                props = tool.inputSchema['properties']
                if tool.name == 'capture_screenshot':
                    self.assertNotIn('preset', props)
                    continue
                self.assertEqual(props['preset']['default'], 'default')
                self.assertTrue({'default', 'full'} <= set(props['preset']['enum']))
                self.assertTrue(getattr(getattr(GameTools, tool.name), 'supports_output_presets', False))
                for branch in tool.inputSchema.get('oneOf', []):
                    self.assertIn('preset', branch['properties'])
                    self.assertFalse(branch['additionalProperties'])
        indexed = {t.name: t.inputSchema for t in tools}
        self.assertNotIn('detail_level', indexed['inspect_deck']['properties'])
        self.assertIn('summary', indexed['inspect_deck']['properties']['preset']['enum'])
        self.assertEqual(indexed['inspect_pile']['required'], ['pile'])
        self.assertEqual(indexed['inspect_deck']['dependentRequired'], {'descending': ['sort_by']})

    def test_schema_composition_preserves_target_exclusivity_and_sort_dependencies(self):
        from jsonschema import Draft202012Validator
        definitions = {t.name: t for t in tool_definitions()}
        target = Draft202012Validator(definitions['inspect_targets'].inputSchema)
        for args in ({'card_id': 0}, {'card_id': 0, 'preset': 'default'},
                     {'potion_slot': 0, 'preset': 'full'}):
            self.assertEqual(list(target.iter_errors(args)), [])
        for args in ({'card_id': 0, 'potion_slot': 0, 'preset': 'full'},
                     {'preset': 'default'}, {'card_id': 0, 'unknown': True}):
            self.assertTrue(list(target.iter_errors(args)), args)
        deck = Draft202012Validator(definitions['inspect_deck'].inputSchema)
        self.assertTrue(list(deck.iter_errors({'preset': 'default', 'descending': False})))
        self.assertEqual(list(deck.iter_errors({'preset': 'default', 'sort_by': 'cost', 'descending': False})), [])

    def test_every_success_fixture_satisfies_its_published_schema(self):
        from jsonschema import Draft202012Validator
        for definition in tool_definitions():
            for preset in (None, 'default', 'full'):
                with self.subTest(tool=definition.name, preset=preset):
                    args = {**REQUIRED_ARGUMENTS.get(definition.name, {}),
                            **({'preset': preset} if preset else {})}
                    errors = list(Draft202012Validator(definition.inputSchema).iter_errors(args))
                    self.assertEqual(errors, [])

    def test_catalog_and_legacy_full_arguments_do_not_mutate_shared_input(self):
        from sts2_mcp.output.hand_presets import HAND_SCHEMA
        from tests.game.support.verification_actions import full_output_arguments
        original = copy.deepcopy(HAND_SCHEMA)
        self.assertEqual(tool_definitions(), tool_definitions())
        self.assertEqual(HAND_SCHEMA, original)
        args = {'card_ids': [7]}
        self.assertEqual(full_output_arguments('inspect_hand', args), {'preset': 'full', 'card_ids': [7]})
        self.assertEqual(args, {'card_ids': [7]})
        self.assertEqual(full_output_arguments('inspect_hand', {'preset': 'summary'}), {'preset': 'summary'})
        self.assertEqual(full_output_arguments('capture_screenshot'), {})


class DefaultToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_presets_are_rejected_by_every_tool_before_native_io(self):
        class NoRequests:
            def call(self, *args, **kwargs):
                raise AssertionError('Invalid output arguments reached the game.')

        for definition in tool_definitions():
            tools = GameTools(NoRequests())
            tools.snapshot_id = 'known-state'
            for invalid in (None, [], True, 0, 'invalid'):
                with self.subTest(tool=definition.name, preset=invalid):
                    arguments = {**REQUIRED_ARGUMENTS.get(definition.name, {}), 'preset': invalid}
                    result = await getattr(tools, definition.name)(arguments)
                    self.assertEqual(result['error']['code'], 'invalid_request')

    async def test_every_public_boundary_accepts_both_presets_without_forwarding_them(self):
        for definition in tool_definitions():
            tools = BoundaryProbe()
            arguments = REQUIRED_ARGUMENTS.get(definition.name, {})
            for preset in (None, 'default', 'full'):
                with self.subTest(tool=definition.name, preset=preset):
                    options = {**arguments, **({'preset': preset} if preset else {})}
                    result = await getattr(tools, definition.name)(options)
                    expected = copy.deepcopy(tools.payload)
                    if preset != 'full':
                        del expected['ordinary']
                    self.assertEqual(result, expected)
            self.assertEqual(len(tools.calls), 3)

    async def test_hand_default_keeps_full_content_and_filters_before_compacting(self):
        client = HandClient()
        tools = GameTools(client)
        full = await tools.inspect_hand({'preset': 'full', 'card_ids': [9, 7, 80]})
        for args in ({'card_ids': [9, 7, 80]}, {'preset': 'default', 'card_ids': [9, 7, 80]}):
            result = await tools.inspect_hand(args)
            self.assertEqual([c['id'] for c in result['hand']], [9, 7])
            self.assertIn('description', result['hand'][0])
            self.assertNotIn('star_cost', result['hand'][0])
            self.assertNotIn('description', result['hand'][1])
            self.assertEqual(result['errors'], full['errors'])
        self.assertIsNone(full['hand'][0]['star_cost'])
        self.assertTrue(all(args is None for op, token, args in client.calls if op == 'inspect_hand'))

    async def test_relic_summary_and_default_omit_ordinary_nulls(self):
        tools = GameTools(RelicClient())
        default = await tools.inspect_relics({'relic_indices': [1]})
        full = await tools.inspect_relics({'preset': 'full', 'relic_indices': [1]})
        summary = await tools.inspect_relics({'preset': 'summary', 'relic_indices': [1]})
        self.assertNotIn('melted', default['relics'][0])
        self.assertIsNone(full['relics'][0]['melted'])
        self.assertNotIn('melted', summary['relics'][0])
        self.assertEqual(default['relics'][0]['counter'], 0)

    async def test_selection_preserves_random_comparison_and_partial_errors(self):
        client = SelectionClient()
        before = client.choice['cards'][0]
        client.choice.update(type='deck_transform', selected_ids=[9], transform_previews=[
            {'before': before, 'after': None, 'random': True}])
        tools = GameTools(client)
        result = await tools.inspect_selection({'card_ids': [9, 80]})
        pair = result['selection']['transform_previews'][0]
        self.assertIsNone(pair['after'])
        self.assertIsNone(pair['before']['star_cost'])
        self.assertNotIn('star_cost', result['selection']['cards'][0])
        self.assertEqual(result['errors'], [{'code': 'cards_not_in_selection', 'card_ids': [80]}])

    async def test_observation_default_and_images_keep_action_permission(self):
        tools = GameTools(DivinationClient())
        default = await tools.get_observation()
        self.assertIsInstance(default, ImagePayload)
        self.assertNotIn('player', default)
        self.assertEqual(default, await tools.get_observation({'preset': 'default'}))
        full = await tools.get_observation({'preset': 'full'})
        self.assertIsNone(full['player'])
        compact = await tools.get_observation({'preset': 'actions_only'})
        self.assertNotIsInstance(compact, ImagePayload)
        self.assertIsNotNone(tools.snapshot_id)

    async def test_bad_full_response_is_rejected_before_default_can_hide_it(self):
        client = HandClient()
        client.hand[0]['description'] = False
        tools = GameTools(client)
        result = await tools.inspect_hand()
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_action_presets_do_not_reach_native_request_or_change_receipts(self):
        client = Client()
        tools = GameTools(client)
        await tools.get_observation()
        result = await tools.end_turn({'preset': 'default'})
        self.assertIn('transition', result)
        self.assertNotIn('player', result)
        self.assertEqual(client.calls[-1][0], 'end_turn')
        self.assertNotIn('preset', client.calls[-1][2] or {})
        self.assertNotIn('error', await tools.end_turn({'preset': 'full'}))
        count = len(client.calls)
        self.assertEqual((await tools.end_turn({'preset': 'summary'}))['error']['code'], 'invalid_request')
        self.assertEqual(len(client.calls), count)
        self.assertIsNone(tools.snapshot_id)


class DefaultStdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_42_tools_dispatch_presets_over_real_stdio(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        program = ('import anyio; from tests.python.test_default_presets import BoundaryProbe; '
                   'from sts2_mcp.mcp_server import run_stdio; anyio.run(run_stdio, BoundaryProbe())')
        params = StdioServerParameters(command=sys.executable, args=['-c', program], cwd=str(root))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                definitions = (await session.list_tools()).tools
                self.assertEqual(len(definitions), 42)
                for definition in definitions:
                    args = REQUIRED_ARGUMENTS.get(definition.name, {})
                    for preset in (None, 'default', 'full'):
                        with self.subTest(tool=definition.name, preset=preset):
                            options = {**args, **({'preset': preset} if preset else {})}
                            result = await session.call_tool(definition.name, options)
                            self.assertFalse(result.isError, result)
                            expected = copy.deepcopy(BoundaryProbe.payload)
                            if preset != 'full':
                                del expected['ordinary']
                            self.assertEqual(result.structuredContent, expected)
                            self.assertEqual(json.loads(result.content[0].text), expected)


if __name__ == '__main__':
    unittest.main()
