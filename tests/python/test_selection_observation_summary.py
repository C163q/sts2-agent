"""Pin compact selection observations and shared card-summary semantics."""
import copy
import json
import unittest
from pathlib import Path

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.card_summary import card_summary
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.presets import apply_preset
from tests.python.test_hand_presets import HandClient
from tests.python.test_selection_presets import SelectionClient
from tests.python.test_relic_presets import RelicClient

EXAMPLES = Path(__file__).resolve().parents[2] / 'docs/research/2026-11-02-get-observation-selection-examples'


def example(name):
    return json.loads((EXAMPLES / f'{name}.full.json').read_text())


def cards(choice):
    yield from choice.get('cards') or []
    for bundle in choice.get('bundles', []):
        yield from bundle['cards']
    pairs = ([choice['upgrade_preview']] if choice.get('upgrade_preview') else [])
    for key in ('upgrade_previews', 'enchant_previews', 'transform_previews'):
        pairs += choice.get(key, [])
    for pair in pairs:
        yield pair['before']
        if pair['after'] is not None:
            yield pair['after']


class SelectionSummaryTests(unittest.TestCase):
    def test_absent_card_decoration_does_not_become_a_playability_claim(self):
        value = {'id': 1, 'name': 'Defend', 'type': 'Skill', 'energy_cost': '0',
                 'star_cost': None, 'outline': 'none', 'unplayable_markers': []}
        self.assertEqual(card_summary(value), {'id': 1, 'name': 'Defend', 'type': 'Skill', 'energy_cost': '0'})
        self.assertEqual(value['unplayable_markers'], [])
        self.assertNotIn('outline', card_summary({'id': 1}))

    def test_nonempty_markers_colors_and_visible_enchantment_survive(self):
        for outline in ('cyan', 'gold', 'red', 'other'):
            card = {'id': 3, 'name': 'A card', 'energy_cost': 'X', 'star_cost': '?',
                    'energy_cost_color': 'green', 'outline': outline, 'unplayable_markers': ['energy', 'star'],
                    'enchantment': {'name': 'Sharp', 'amount': 0, 'dimmed': False}}
            self.assertEqual(card_summary(card), card)

    def test_all_existing_selection_shapes_use_one_card_whitelist(self):
        for path in EXAMPLES.glob('*.full.json'):
            with self.subTest(path=path.name):
                source = json.loads(path.read_text())
                original = copy.deepcopy(source)
                result = observation_preset(source, 'summary')
                choice = result['selection']
                self.assertEqual(choice['type'], source['selection']['type'])
                self.assertEqual(choice['status'], source['selection']['status'])
                self.assertEqual(choice['options'], source['selection']['options'])
                if source['selection']['selected_ids'] is not None:
                    self.assertEqual(choice['selected_ids'], source['selection']['selected_ids'])
                for card in cards(choice):
                    self.assertNotIn('description', card)
                    self.assertNotIn('rarity', card)
                    self.assertNotIn('visual_card_pool', card)
                    self.assertNotEqual(card.get('outline'), 'none')
                    self.assertNotEqual(card.get('unplayable_markers'), [])
                for field in ('bundles', 'upgrade_previews', 'enchant_previews', 'transform_previews'):
                    self.assertNotEqual(choice.get(field), [])
                self.assertEqual(source, original)

    def test_empty_context_is_kept_while_unopened_preview_is_omitted(self):
        result = observation_preset(example('smith-candidates'), 'summary')['selection']
        self.assertNotIn('upgrade_previews', result)
        self.assertEqual(result['selected_ids'], [])
        self.assertTrue(result['cards'])
        result = observation_preset(example('smith-selected'), 'summary')['selection']
        self.assertEqual(result['cards'], [])
        self.assertEqual(len(result['upgrade_previews']), 1)
        result = observation_preset(example('bundle-selected'), 'summary')['selection']
        self.assertNotIn('bundles', result)
        self.assertEqual(len(result['cards']), 3)

    def test_unknown_original_and_random_result_are_not_compacted_away(self):
        result = observation_preset(example('upgrade-multi-selected'), 'summary')['selection']
        self.assertIsNone(result['upgrade_previews'][0]['before']['name'])
        self.assertIn('id', result['upgrade_previews'][0]['before'])
        result = observation_preset(example('transform-selected'), 'summary')['selection']
        self.assertIsNone(result['transform_previews'][0]['after'])
        self.assertTrue(result['transform_previews'][0]['random'])
        result = observation_preset(example('enchant-selected'), 'summary')['selection']
        self.assertIn('description', result['enchantment'])
        self.assertEqual(result['enchant_previews'][0]['after']['enchantment']['amount'], 2)

    def test_hidden_selection_and_existing_presets_keep_their_boundaries(self):
        for name in ('hand-upgrade-battlefield', 'hand-upgrade-deck-covered', 'hand-upgrade-map-covered'):
            source = example(name)
            result = observation_preset(source, 'summary')
            self.assertNotIn('cards', result['selection'])
            self.assertNotIn('upgrade_preview', result['selection'])
            self.assertIn('selection', result['notes'])
            self.assertEqual(observation_preset(source, 'full'), source)
            self.assertEqual(observation_preset(source, 'top_bar')['selection'],
                             {k: source['selection'][k] for k in ('type', 'status')})
        source = example('smith-selected')
        self.assertEqual(apply_preset(source, 'default')['selection']['upgrade_previews'][0]['before'],
                         source['selection']['upgrade_previews'][0]['before'])


class DedicatedSummaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_hand_summary_inherits_default_and_keeps_explicit_zero(self):
        result = await GameTools(HandClient()).inspect_hand({'preset': 'summary'})
        self.assertEqual(result['hand'][-1], {'id': 7, 'name': 'Unknown'})
        self.assertEqual(result['hand'][0]['energy_cost'], '0')
        self.assertNotIn('unplayable_markers', result['hand'][0])
        self.assertNotIn('outline', result['hand'][1])

    async def test_selection_summary_filters_before_compacting_and_preserves_errors(self):
        client = SelectionClient()
        result = await GameTools(client).inspect_selection({'preset': 'summary', 'card_ids': [9, 999]})
        self.assertEqual([c['id'] for c in result['selection']['cards']], [9])
        self.assertNotIn('unplayable_markers', result['selection']['cards'][0])
        self.assertEqual(result['selection']['cards'][0]['enchantment']['dimmed'], False)
        self.assertEqual(result['errors'], [{'code': 'cards_not_in_selection', 'card_ids': [999]}])

    async def test_relic_summary_omits_nulls_but_preserves_zero_and_false(self):
        self.assertEqual(await GameTools(RelicClient()).inspect_relics({'preset': 'summary'}), {'relics': [
            {'name': 'Anchor', 'melted': False}, {'name': 'Pen Nib', 'counter': 0},
            {'name': 'Anchor', 'melted': True}]})
