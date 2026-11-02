"""Pin one top-bar summary contract across underlying rooms and exposed pages."""
import copy
import unittest

from sts2_mcp.output.observation_presets import observation_preset


class SharedTopBarSummaryTests(unittest.TestCase):
    def test_top_bar_summary_is_independent_of_scene_and_view(self):
        bar = {'hp': 70, 'max_hp': 80, 'gold': 0, 'floor': 2, 'deck_count': 10,
               'potion_slots': [None, {'name': 'Block Potion', 'bouncing': False}],
               'relic_count': 0, 'relics': [], 'settings_visible': True}
        expected = {'gold': 0, 'deck_count': 10, 'potion_slots': bar['potion_slots'], 'relic_count': 0}
        for scene in ('combat', 'event', 'rest_site', 'rewards', 'treasure', 'shop', 'ancient',
                      'epilogue', 'run_result', 'main_menu', 'loading_or_noncombat'):
            for view in (None, 'map', 'deck', 'draw_pile', 'discard_pile', 'exhaust_pile', 'divination'):
                with self.subTest(scene=scene, view=view):
                    source = {'scene': scene, 'screen': {'status': 'visible'},
                              'top_bar': copy.deepcopy(bar), 'available_actions': []}
                    if view:
                        source['screen']['view'] = view
                    original = copy.deepcopy(source)
                    self.assertEqual(observation_preset(source, 'summary')['top_bar'], expected)
                    self.assertEqual(source, original)

    def test_hidden_top_bar_and_unknown_count_are_not_reconstructed(self):
        source = {'scene': 'event', 'screen': {'status': 'visible'}, 'available_actions': []}
        self.assertNotIn('top_bar', observation_preset(source, 'summary'))
        source['top_bar'] = None
        self.assertNotIn('top_bar', observation_preset(source, 'summary'))
        source['top_bar'] = {'gold': 0, 'potion_slots': [None, None], 'deck_count': 0,
                             'relic_count': None, 'relics': [{'name': 'Burning Blood'}]}
        self.assertEqual(observation_preset(source, 'summary')['top_bar'],
                         {'gold': 0, 'potion_slots': [None, None], 'deck_count': 0})
        del source['top_bar']['relic_count']
        self.assertNotIn('relic_count', observation_preset(source, 'summary')['top_bar'])
