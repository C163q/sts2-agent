"""Validate public view tools without admitting covered gameplay actions."""
import copy
import unittest

from sts2_mcp.output.game_output import observation_details
from tests.python.test_map_travel import map_observation
from tests.python.test_run_ending import state as result_state
from tests.python.test_events import state as event_state


class AvailableViewTests(unittest.TestCase):
    def test_epilogue_can_open_deck_without_exposing_covered_dialogue(self):
        raw = event_state()
        raw.update(scene='epilogue', event=None, screen={'status': 'visible', 'view': 'epilogue'},
                   available_actions=['advance_dialogue', 'inspect_deck'],
                   epilogue={'status': 'visible', 'dialogue': None,
                             'continue': {'text': 'Continue', 'enabled': True}, 'proceed': None})
        self.assertIn('inspect_deck', observation_details(raw)['available_actions'])
        raw.update(screen={'status': 'covered', 'view': 'deck'},
                   available_actions=['inspect_deck', 'close_card_view', 'inspect_map'])
        raw['epilogue'].update(status='covered')
        raw['epilogue']['continue'] = None
        self.assertEqual(observation_details(raw)['screen'], raw['screen'])
        raw['available_actions'].append('inspect_ui')
        self.assertIn('inspect_ui', observation_details(raw)['available_actions'])
        for action in ('advance_dialogue', 'proceed', 'play_card'):
            broken = copy.deepcopy(raw)
            broken['available_actions'].append(action)
            with self.subTest(action=action), self.assertRaises(ValueError):
                observation_details(broken)

    def test_map_accepts_visible_relic_inspection(self):
        for scene in ('combat', 'treasure'):
            raw = map_observation()
            raw.update(scene=scene, treasure=None)
            if scene == 'treasure':
                raw['treasure'] = {'status': 'covered', 'chest': None, 'relic': None, 'proceed': None}
            raw['available_actions'].append('inspect_relics')
            self.assertIn('inspect_relics', observation_details(raw)['available_actions'])

    def test_result_accepts_visible_relic_inspection(self):
        raw = result_state()
        raw['available_actions'].append('inspect_relics')
        self.assertIn('inspect_relics', observation_details(raw)['available_actions'])

    def test_unready_result_can_still_offer_readable_top_bar(self):
        raw = result_state()
        raw['run_result'].update(status='not_ready')
        raw['run_result']['options'][0]['enabled'] = False
        raw['available_actions'] = ['inspect_potions', 'inspect_relics', 'inspect_run_result']
        self.assertEqual(observation_details(raw)['available_actions'], raw['available_actions'])
        for action in ('run_result_option', 'play_card', 'inspect_deck'):
            broken = copy.deepcopy(raw)
            broken['available_actions'].append(action)
            with self.subTest(action=action), self.assertRaises(ValueError):
                observation_details(broken)

    def test_covered_result_cannot_offer_top_bar_inspections(self):
        raw = result_state()
        raw['run_result'].update(status='covered', title=None, texts=[], options=[])
        raw['screen']['status'] = 'covered'
        for tool in ('inspect_relics', 'inspect_potions'):
            raw['available_actions'] = [tool]
            with self.subTest(tool=tool), self.assertRaises(ValueError):
                observation_details(raw)
