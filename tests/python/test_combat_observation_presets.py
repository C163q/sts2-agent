"""Exercise observation projections against full native state and public tool calls."""
import copy
import json
import unittest
from pathlib import Path

from sts2_mcp.game_tools import GameTools
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.mcp_server import tool_result
from sts2_mcp.output.card_summary import card_summary
from sts2_mcp.output.divination_details import ImagePayload
from sts2_mcp.output.game_output import observation_details
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.presets import apply_preset
from tests.python.test_action_observations import Client
from tests.python.test_divination import DivinationClient


EXAMPLES = Path(__file__).resolve().parents[2] / 'docs/research/2026-11-02-get-observation-examples'


def sample(name='combat'):
    result = json.loads((EXAMPLES / f'{name}.full.json').read_text())
    result['top_bar']['relic_count'] = len(result['top_bar']['relics'])
    return result


class CombatProjectionTests(unittest.TestCase):
    def test_combat_and_top_bar_match_approved_design_examples(self):
        for preset, filename in [('summary', 'combat.summary-design.json'),
                                 ('top_bar', 'combat.top-bar-design.json')]:
            with self.subTest(preset=preset):
                value = sample()
                original = copy.deepcopy(value)
                expected = json.loads((EXAMPLES / filename).read_text())
                if preset == 'summary':
                    for card in expected['player']['hand']:
                        card.pop('unplayable_markers', None)
                        if card.get('outline') == 'none':
                            card.pop('outline')
                self.assertEqual(observation_preset(value, preset), expected)
                self.assertEqual(value, original)

    def test_all_health_displays_apply_to_player_enemies_and_allies(self):
        for status, expected in [('numeric', '70/80'), ('infinite', '∞'),
                                 ('dead', 'dead'), ('hidden', None), ('unknown', 'unknown')]:
            with self.subTest(status=status):
                value = sample()
                unit = {'hp': 70 if status == 'numeric' else None,
                        'max_hp': 80 if status == 'numeric' else None, 'hp_display': status, 'block': 0}
                value['player'].update(unit)
                value['enemies'] = [{'id': 1, **unit}]
                value['allies'] = [{'id': 4, 'block_shared_with': 'player', **unit}]
                result = observation_preset(value, 'summary')
                for compact in [result['player'], *result['enemies'], *result['allies']]:
                    self.assertIn('health', compact)
                    self.assertEqual(compact['health'], expected)
                    self.assertFalse({'hp', 'max_hp', 'hp_display'} & compact.keys())
                    self.assertEqual(compact['block'], 0)
                self.assertEqual(result['allies'][0]['block_shared_with'], 'player')

    def test_missing_numeric_health_and_energy_do_not_invent_values(self):
        value = sample()
        value['player']['max_hp'] = None
        value['player']['max_energy'] = None
        result = observation_preset(value, 'summary')['player']
        self.assertIsNone(result['health'])
        self.assertNotIn('energy', result)
        self.assertNotIn('max_energy', result)

    def test_energy_zero_and_stars_are_preserved(self):
        value = sample('regent-blade')
        value['player']['energy'] = 0
        value['player']['stars'] = 0
        result = observation_preset(value, 'summary')['player']
        self.assertEqual(result['energy'], '0/3')
        self.assertEqual(result['stars'], 0)
        self.assertEqual(result['sovereign_blades'], value['player']['sovereign_blades'])

    def test_orb_positions_and_enchantments_use_default_null_semantics(self):
        value = sample('orbs')
        result = observation_preset(value, 'summary')['player']
        self.assertEqual(len(result['orb_slots']), 5)
        self.assertIsNone(result['orb_slots'][-1])
        self.assertEqual(result['orb_slots'][3], {'name': 'Plasma'})
        value['player']['orb_slots'] = [None, None, None]
        self.assertEqual(observation_preset(value, 'summary')['player']['orb_slots'], [None] * 3)
        value = sample('enchantments')
        cards = observation_preset(value, 'summary')['player']['hand']
        self.assertEqual(cards, [card_summary(c) for c in apply_preset(value, 'default')['player']['hand']])
        self.assertEqual(cards[0]['enchantment']['amount'], 3)
        self.assertTrue(cards[1]['enchantment']['dimmed'])
        self.assertNotIn('amount', cards[2]['enchantment'])
        self.assertNotIn('enchantment', cards[3])

    def test_empty_powers_disappear_but_zero_amount_and_other_empty_arrays_remain(self):
        value = sample()
        value['enemies'][0]['powers'] = [{'name': 'Strength', 'amount': 0}]
        result = observation_preset(value, 'summary')
        self.assertNotIn('powers', result['player'])
        self.assertEqual(result['enemies'][0]['powers'][0]['amount'], 0)
        self.assertNotIn('powers', result['enemies'][1])
        self.assertEqual(result['allies'], [])
        self.assertNotIn('unplayable_markers', result['player']['hand'][0])

    def test_unreadable_relic_count_never_falls_back_to_filtered_list_length(self):
        for preset in ('summary', 'top_bar'):
            for count in (None, 0, 8):
                with self.subTest(preset=preset, count=count):
                    value = sample()
                    value['top_bar']['relic_count'] = count
                    result = observation_preset(value, preset)['top_bar']
                    self.assertNotIn('relics', result)
                    if count is None:
                        self.assertNotIn('relic_count', result)
                    else:
                        self.assertEqual(result['relic_count'], count)
            value = sample()
            del value['top_bar']['relic_count']
            self.assertNotIn('relic_count', observation_preset(value, preset)['top_bar'])

    def test_top_bar_keeps_choice_context_and_omits_picture_notes_and_combat_details(self):
        value = sample()
        value['selection'] = {'type': 'hand', 'status': 'battlefield', 'cards': [{'id': 5}]}
        value = ImagePayload(value, 'aW1hZ2U=')
        result = observation_preset(value, 'top_bar')
        self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'selection', 'top_bar'})
        self.assertEqual(result['selection'], {'type': 'hand', 'status': 'battlefield'})
        self.assertEqual([c.type for c in tool_result(result).content], ['text'])

    def test_covered_combat_does_not_reconstruct_hidden_units(self):
        value = sample()
        value.update(screen={'status': 'covered'}, player=None, enemies=None, allies=None, top_bar=None)
        result = observation_preset(value, 'summary')
        self.assertNotIn('player', result)
        self.assertNotIn('top_bar', result)
        self.assertNotIn('top_bar', observation_preset(value, 'top_bar'))

    def test_rest_and_divination_summary_share_top_bar_and_preserve_other_content_and_image(self):
        for name in ('rest-site', 'divination'):
            value = sample(name)
            if name == 'divination':
                value = ImagePayload(value, 'aW1hZ2U=')
            expected = apply_preset(value, 'default')
            expected['top_bar'] = {k: v for k, v in expected['top_bar'].items()
                                   if k in {'gold', 'potion_slots', 'deck_count', 'relic_count'}}
            if name == 'divination':
                expected['divination'].pop('instructions', None)
            self.assertEqual(observation_preset(value, 'summary'), expected)
            result = tool_result(observation_preset(value, 'summary'))
            self.assertEqual(len(result.content), 2 if name == 'divination' else 1)
            if name == 'divination':
                self.assertEqual([c.type for c in tool_result(observation_preset(value, 'top_bar')).content], ['text'])

    def test_existing_full_actions_only_and_errors_are_unchanged(self):
        value = sample()
        self.assertIs(observation_preset(value, 'full'), value)
        self.assertEqual(set(observation_preset(value, 'actions_only')), {'scene', 'screen', 'available_actions'})
        error = {'error': {'code': 'transport_error'}}
        for preset in ('summary', 'top_bar'):
            self.assertIs(observation_preset(error, preset), error)

    def test_public_schema_offers_both_new_presets(self):
        schema = next(t.inputSchema for t in tool_definitions() if t.name == 'get_observation')
        self.assertEqual(schema['properties']['preset']['enum'], ['default', 'full', 'actions_only', 'summary', 'top_bar'])

    def test_invalid_native_counts_are_rejected_before_projection(self):
        for count in (-1, True, 1.5, '3', []):
            with self.subTest(count=count):
                value = sample()
                value['top_bar']['relic_count'] = count
                with self.assertRaises(ValueError):
                    observation_details(value)


class ObservationToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_divination_summary_omits_teaching_but_keeps_visible_board_media_and_permission(self):
        client = DivinationClient()
        client.raw['divination']['dialogue'] = 'There is much to uncover...'
        original = copy.deepcopy(client.raw)
        tools = GameTools(client)
        full = await tools.get_observation({'preset': 'full'})
        summary = await tools.get_observation({'preset': 'summary'})
        self.assertNotIn('instructions', summary['divination'])
        self.assertEqual(summary['divination'], {
            'status': 'visible', 'phase': 'playing', 'remaining': 3, 'tool': 'big',
            'tools': [{'id': 'big', 'text': 'Big Divination', 'enabled': True},
                      {'id': 'small', 'text': 'Small Divination', 'enabled': True}],
            'dialogue': 'There is much to uncover...',
            'grid': {'columns': 11, 'rows': 11, 'covered_rows': ['###########'] * 11,
                     'image': {'width': 1, 'height': 1}}})
        self.assertIn('# covered', summary['notes']['divination'])
        self.assertEqual(summary['available_actions'], ['set_divination_tool', 'divine'])
        response = tool_result(summary)
        self.assertEqual([block.type for block in response.content], ['text', 'image'])
        self.assertEqual(response.content[1].data, tool_result(full).content[1].data)
        self.assertEqual(json.loads(response.content[0].text), response.structuredContent)
        for result in (full, await tools.get_observation(), await tools.inspect_event()):
            self.assertEqual(result['divination']['instructions'], {
                'title': 'How to divine', 'description': 'Uncover the future.'})
        self.assertEqual(client.raw, original)
        await tools.get_observation({'preset': 'summary'})
        self.assertEqual(tools.snapshot_id, 'sphere-1')
        self.assertNotIn('error', await tools.set_divination_tool({'tool': 'small'}))

    async def test_invalid_divination_instructions_are_rejected_before_summary_omits_them(self):
        client = DivinationClient()
        client.raw['divination']['instructions']['description'] = 123
        tools = GameTools(client)
        result = await tools.get_observation({'preset': 'summary'})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual([block.type for block in tool_result(result).content], ['text'])

    async def test_native_count_survives_validation_and_both_public_projections(self):
        class CountClient(Client):
            def call(self, *args, **kwargs):
                reply = super().call(*args, **kwargs)
                reply['state']['top_bar']['relic_count'] = 8
                return reply
        tools = GameTools(CountClient())
        for preset in ('full', 'default', 'summary', 'top_bar'):
            result = await tools.get_observation({'preset': preset})
            self.assertNotIn('error', result)
            self.assertEqual(result['top_bar']['relic_count'], 8)

    async def test_new_presets_refresh_permission_and_do_not_forward_output_arguments(self):
        for preset in ('summary', 'top_bar'):
            client = Client()
            tools = GameTools(client)
            result = await tools.get_observation({'preset': preset})
            self.assertNotIn('error', result)
            self.assertEqual(client.calls, [('get_state', None, None)])
            self.assertEqual(tools.snapshot_id, 'state-1')
            self.assertNotIn('error', await tools.play_card({'card_id': 0}))

    async def test_new_presets_reject_bad_full_state_before_projection(self):
        class Broken(Client):
            def call(self, *args, **kwargs):
                reply = super().call(*args, **kwargs)
                reply['state']['player']['hp'] = True
                return reply
        for preset in ('summary', 'top_bar'):
            tools = GameTools(Broken())
            self.assertEqual((await tools.get_observation({'preset': preset}))['error']['code'], 'transport_error')
            self.assertIsNone(tools.snapshot_id)

    async def test_top_bar_divination_is_text_only_and_summary_has_image(self):
        tools = GameTools(DivinationClient())
        for preset, types in [('summary', ['text', 'image']), ('top_bar', ['text'])]:
            reply = tool_result(await tools.get_observation({'preset': preset}))
            self.assertFalse(reply.isError)
            self.assertEqual([c.type for c in reply.content], types)
            self.assertEqual(json.loads(reply.content[0].text), reply.structuredContent)
