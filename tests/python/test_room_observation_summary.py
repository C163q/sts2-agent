"""Keep room observations complete while preserving explicit visible absence."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.presets import apply_preset
from tests.python.test_treasure import TreasureClient
from tests.python.test_shop import ShopClient
from tests.python.test_events import EventClient


class RoomNullTests(unittest.TestCase):
    def test_finished_event_keeps_empty_choices_and_covered_rooms_stay_covered(self):
        raw = {'scene': 'event', 'screen': {'status': 'visible'},
               'event': {'status': 'visible', 'description': 'The story ends.', 'options': [],
                         'proceed': {'text': 'Proceed', 'enabled': True}}, 'available_actions': ['proceed']}
        self.assertEqual(observation_preset(raw, 'summary')['event'], {
            'status': 'visible', 'options': [], 'proceed': {'text': 'Proceed', 'enabled': True}})
        for scene, fields in (
            ('event', ('name', 'description', 'options', 'proceed')),
            ('shop', ('view', 'items', 'open', 'back', 'proceed')),
        ):
            raw.update(scene=scene, **{scene: {'status': 'covered', **dict.fromkeys(fields)}})
            self.assertEqual(observation_preset(raw, 'summary')[scene], {'status': 'covered'})

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
    async def test_shop_cards_share_compact_fields_without_changing_item_identity_or_full(self):
        client = ShopClient()
        client.raw['shop']['items'][0]['id'] = 7
        client.raw['shop']['items'][0].update(price=0, affordable=False, enabled=False)
        tools = GameTools(client)
        original = copy.deepcopy(client.raw)
        result = await tools.get_observation({'preset': 'summary'})
        self.assertEqual(result['shop']['items'], [{
            'id': 7, 'kind': 'card', 'position': 'character_card:0', 'price': 0,
            'affordable': False, 'enabled': False, 'on_sale': False,
            'card': {'name': 'Strike+', 'type': 'Attack', 'energy_cost': '1', 'star_cost': '0'}}])
        for preset in ('default', 'full'):
            card = (await tools.get_observation({'preset': preset}))['shop']['items'][0]['card']
            self.assertEqual(card['rarity'], 'basic')
            self.assertEqual(card['visual_card_pool'], 'Ironclad')
            self.assertNotIn('description', card)
        detail = await tools.inspect_shop()
        self.assertEqual(detail['shop']['items'][0]['card']['description'], 'Deal 9 damage.')
        self.assertEqual(client.raw, original)

    async def test_event_summary_omits_narrative_and_absent_warning_but_keeps_option_effects(self):
        client = EventClient()
        client.raw['event']['options'].append({
            'id': 1, 'title': 'Locked', 'description': 'No eligible cards.',
            'enabled': False, 'lethal_warning': False, 'hover_tips': []})
        tools = GameTools(client)
        result = await tools.get_observation({'preset': 'summary'})
        self.assertEqual(result['event'], {
            'status': 'visible', 'name': 'Abyssal Baths', 'options': [
                {'id': 0, 'title': 'Immerse', 'description': 'Lose 3 HP.',
                 'enabled': True, 'lethal_warning': True},
                {'id': 1, 'title': 'Locked', 'description': 'No eligible cards.', 'enabled': False}]})
        for preset in ('default', 'full'):
            event = (await tools.get_observation({'preset': preset}))['event']
            self.assertEqual(event['description'], 'The water is warm.')
            self.assertIs(event['options'][1]['lethal_warning'], False)
        detail = await tools.inspect_event()
        self.assertEqual(detail['event']['description'], 'The water is warm.')
        await tools.get_observation({'preset': 'summary'})
        result = await tools.choose_event_option({'option_id': 0})
        self.assertNotIn('error', result)
        self.assertEqual(client.calls[-1], ('choose_event_option', 'event-1', {'option_id': 0}))

    async def test_summary_still_rejects_invalid_warning_before_hiding_it(self):
        client = EventClient()
        client.raw['event']['options'][0]['lethal_warning'] = 0
        tools = GameTools(client)
        result = await tools.get_observation({'preset': 'summary'})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

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
