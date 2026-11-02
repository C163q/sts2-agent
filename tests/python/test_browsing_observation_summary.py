"""Keep browser content at default while sharing the top-bar summary."""
import copy
import json
import unittest
from pathlib import Path

from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.presets import apply_preset


EXAMPLES = Path(__file__).resolve().parents[2] / 'docs/research/2026-11-02-get-observation-browsing-examples'
REPAIRED = EXAMPLES.parent / '2026-11-02-top-bar-visibility-examples'
VIEWS = ('map', 'deck', 'draw_pile', 'discard_pile', 'exhaust_pile')


class BrowsingSummaryTests(unittest.TestCase):
    def test_actual_browser_content_matches_default_except_shared_top_bar(self):
        seen = set()
        for path in (*EXAMPLES.glob('*.full.json'), *REPAIRED.glob('*.full.json')):
            source = json.loads(path.read_text())
            view = source['screen'].get('view')
            if view not in VIEWS:
                continue
            with self.subTest(path=path.name):
                seen.add(view)
                original = copy.deepcopy(source)
                expected = apply_preset(source, 'default')
                if 'top_bar' in expected:
                    expected['top_bar'] = {k: v for k, v in expected['top_bar'].items()
                                           if k in {'gold', 'potion_slots', 'deck_count', 'relic_count'}}
                self.assertEqual(observation_preset(source, 'summary'), expected)
                self.assertEqual(source, original)
        self.assertEqual(seen, set(VIEWS))

    def test_browser_context_uses_shared_top_bar_independently_of_room(self):
        for view in VIEWS:
            for scene in ('combat', 'event', 'loading_or_noncombat'):
                with self.subTest(view=view, scene=scene):
                    source = {'scene': scene, 'screen': {'status': 'covered', 'view': view},
                              'top_bar': {'hp': 70, 'max_hp': 80, 'gold': 0, 'floor': 2,
                                          'potion_slots': [None], 'relic_count': 0, 'relics': [],
                                          'settings_visible': False, 'ascension': None},
                              'available_actions': ['inspect_deck', 'inspect_map']}
                    original = copy.deepcopy(source)
                    result = observation_preset(source, 'summary')
                    expected = apply_preset(source, 'default')
                    expected['top_bar'] = {'gold': 0, 'potion_slots': [None], 'relic_count': 0}
                    self.assertEqual(result, expected)
                    self.assertEqual(source, original)

    def test_covered_selection_keeps_default_metadata_and_hides_candidates(self):
        for view in VIEWS:
            with self.subTest(view=view):
                source = {'scene': 'combat', 'screen': {'status': 'covered', 'view': view},
                          'selection': {'type': 'deck_upgrade', 'status': 'covered', 'cards': None,
                                        'selected_ids': None, 'options': [], 'upgrade_previews': [],
                                        'can_view_battlefield': False},
                          'available_actions': ['close_card_view']}
                result = observation_preset(source, 'summary')
                self.assertEqual(result, apply_preset(source, 'default'))
                self.assertNotIn('cards', result['selection'])
                self.assertNotIn('selected_ids', result['selection'])
                self.assertEqual(result['selection']['upgrade_previews'], [])
