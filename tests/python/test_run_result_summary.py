"""Keep current-page result context while compacting displayed card faces."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_run_ending import state


class ResultClient:
    def __init__(self):
        self.raw = state('unlock')
        self.raw['available_actions'] = ['run_result_option', 'inspect_run_result']
        self.raw['run_result'].update(title=None, texts=['Cards Unlocked!', 'The following cards will appear in future runs.'],
            cards=[{'id': 'card:0', 'name': 'Automation', 'type': 'Power', 'rarity': 'uncommon',
                    'visual_card_pool': 'colorless', 'energy_cost': '1', 'star_cost': None,
                    'description': 'Every 10 cards you draw, gain <Energy>.', 'hover_tips': []},
                   {'id': 'card:1', 'name': 'Star card', 'type': 'Skill', 'rarity': 'rare',
                    'visual_card_pool': 'regent', 'energy_cost': '0', 'star_cost': '2',
                    'description': 'Visible card text.', 'hover_tips': []}], hover_tips=[])

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation not in {'get_state', 'inspect_run_result'}: raise AssertionError(operation)
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class RunResultSummaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_compacts_result_cards_without_losing_story_buttons_or_empty_lists(self):
        client = ResultClient()
        original = copy.deepcopy(client.raw)
        tools = GameTools(client)
        result = await tools.get_observation({'preset': 'summary'})
        self.assertNotIn('error', result)
        self.assertEqual(result['run_result'], {
            'status': 'visible', 'phase': 'unlock',
            'texts': ['Cards Unlocked!', 'The following cards will appear in future runs.'],
            'score_lines': [], 'badges': [], 'discoveries': [],
            'options': [{'id': 'continue', 'text': 'Continue', 'enabled': True}],
            'cards': [{'id': 'card:0', 'name': 'Automation', 'type': 'Power', 'energy_cost': '1'},
                      {'id': 'card:1', 'name': 'Star card', 'type': 'Skill', 'energy_cost': '0', 'star_cost': '2'}],
            'relics': [], 'potions': [], 'hover_tips': [],
        })
        self.assertEqual(tools.snapshot_id, 'result-1')
        self.assertEqual(client.raw, original)
        for preset in ('full', 'default'):
            current = await tools.get_observation({'preset': preset})
            self.assertNotIn('description', current['run_result']['cards'][0])
            self.assertEqual(current['run_result']['cards'][0]['rarity'], 'uncommon')
            self.assertEqual(current['run_result']['cards'][0]['visual_card_pool'], 'colorless')
        detail = await tools.inspect_run_result()
        self.assertEqual(detail['run_result']['cards'][0]['description'], 'Every 10 cards you draw, gain <Energy>.')
        self.assertEqual(detail['run_result']['cards'][0]['hover_tips'], [])

    async def test_non_card_result_pages_keep_their_visible_text_and_context(self):
        client = ResultClient()
        for phase in ('outcome', 'summary', 'history', 'leaderboard', 'timeline', 'epoch', 'unlock', 'tutorial'):
            with self.subTest(phase=phase):
                client.raw['run_result'].update(phase=phase, cards=[], texts=['Visible chapter or progress: [140/200]'])
                result = await GameTools(client).get_observation({'preset': 'summary'})
                self.assertNotIn('error', result)
                self.assertEqual(result['run_result']['texts'], ['Visible chapter or progress: [140/200]'])
                self.assertEqual(result['run_result']['options'], [{'id': 'continue', 'text': 'Continue', 'enabled': True}])
                self.assertEqual(result['run_result']['cards'], [])
                self.assertEqual(result['run_result']['relics'], [])

    async def test_invalid_full_card_text_is_rejected_before_summary_can_omit_it(self):
        client = ResultClient()
        client.raw['run_result']['cards'][0]['description'] = 123
        tools = GameTools(client)
        result = await tools.get_observation({'preset': 'summary'})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)
