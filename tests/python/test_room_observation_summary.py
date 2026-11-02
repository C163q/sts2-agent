"""Keep room observations complete while preserving explicit visible absence."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.presets import apply_preset
from tests.python.test_treasure import TreasureClient


class RoomNullTests(unittest.TestCase):
    def test_summary_keeps_room_choices_empty_lists_and_button_semantics(self):
        rooms = {
            'rewards': {'status': 'visible', 'title': 'Rewards', 'items': [],
                        'proceed': {'text': 'Proceed', 'enabled': True, 'skips_remaining': False}},
            'rest_site': {'status': 'visible', 'prompt': 'Rest', 'description': 'Cannot upgrade.',
                          'options': [{'id': 'SMITH', 'text': 'Smith', 'enabled': False}],
                          'proceed': {'text': 'Proceed', 'enabled': True}},
            'treasure': {'status': 'visible', 'chest': 'open', 'relic': None,
                         'proceed': {'text': 'Proceed', 'enabled': True, 'skips_remaining': False}},
        }
        for scene, room in rooms.items():
            with self.subTest(scene=scene):
                raw = {'scene': scene, 'screen': {'status': 'visible'}, scene: copy.deepcopy(room),
                       'available_actions': ['proceed']}
                expected = copy.deepcopy(raw)
                self.assertEqual(observation_preset(raw, 'summary'), expected)
                self.assertEqual(raw, expected)

    def test_visible_treasure_keeps_absent_relic_for_every_chest_state(self):
        for chest in ('closed', 'opening', 'open'):
            raw = {'treasure': {'status': 'visible', 'chest': chest,
                                'relic': None, 'proceed': None}, 'relic': None}
            original = copy.deepcopy(raw)
            with self.subTest(chest=chest):
                expected = {'treasure': {'status': 'visible', 'chest': chest, 'relic': None}}
                self.assertEqual(apply_preset(raw, 'default'), expected)
                self.assertEqual(apply_preset(expected, 'default'), expected)
                self.assertEqual(apply_preset(raw, 'full'), original)
                self.assertEqual(raw, original)

    def test_covered_missing_and_unrelated_nulls_are_not_visible_absence(self):
        for status in ('covered', None):
            with self.subTest(status=status):
                self.assertEqual(apply_preset({'treasure': {
                    'status': status, 'chest': None, 'relic': None, 'proceed': None}}, 'default'),
                    {'treasure': {'status': status} if status else {}})
        self.assertEqual(apply_preset({'treasure': {'status': 'visible'}}, 'default'),
                         {'treasure': {'status': 'visible'}})
        self.assertEqual(apply_preset({'other': {'status': 'visible', 'relic': None}}, 'default'),
                         {'other': {'status': 'visible'}})


class RoomToolPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_observation_and_inspection_preserve_visible_absence_at_public_boundary(self):
        for chest in ('closed', 'opening', 'open'):
            client = TreasureClient()
            client.raw['treasure']['chest'] = chest
            tools = GameTools(client)
            for preset in ('default', 'summary', 'full'):
                with self.subTest(chest=chest, preset=preset):
                    result = await tools.get_observation({'preset': preset})
                    self.assertIn('relic', result['treasure'])
                    self.assertIsNone(result['treasure']['relic'])
                    self.assertEqual(result['treasure']['chest'], chest)
                    if preset == 'full':
                        self.assertIn('proceed', result['treasure'])
                    else:
                        self.assertNotIn('proceed', result['treasure'])
            result = await tools.inspect_treasure()
            self.assertEqual(result['treasure'], {
                'status': 'visible', 'chest': chest, 'relic': None})
