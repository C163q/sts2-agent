import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_events import EventClient, state as event_state
from tests.python.test_divination import DivinationClient, state as divination_state


def text_board():
    raw = divination_state()
    raw['schema_version'] = 45
    raw['divination']['grid'].pop('covered_rows')
    raw['divination']['grid'].update(
        cell_rows=['###########'] * 5 + ['#####s#####'] + ['###########'] * 5,
        visible_fragments=[{'x': 5, 'y': 5, 'appearance': 'potion.base'}])
    return raw


class EventInspectionPresets(unittest.IsolatedAsyncioTestCase):
    async def test_event_validates_nonvisible_auxiliary_board_before_authorizing(self):
        for preset in ('default', 'full', 'summary'):
            for status in ('covered', 'garbage'):
                with self.subTest(preset=preset, status=status):
                    client = EventClient()
                    client.raw['divination'] = text_board()['divination']
                    client.raw['divination']['status'] = status
                    tools = GameTools(client)
                    result = await tools.inspect_event({'preset': preset})
                    self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                    self.assertIsNone(tools.session.permission.token)
            client = EventClient()
            board = text_board()['divination']
            client.raw['divination'] = {key: 'covered' if key == 'status' else None for key in board}
            tools = GameTools(client)
            result = await tools.inspect_event({'preset': preset})
            self.assertNotIn('error', result)
            self.assertEqual(tools.session.permission.token, 'event-1')

    async def test_legacy_revealed_cells_are_not_described_as_known_empty(self):
        client = DivinationClient()
        client.raw['divination']['grid']['covered_rows'][5] = '#####.#####'
        result = await GameTools(client).get_observation()
        self.assertNotIn('error', result)
        self.assertIn('revealed with unknown contents', result['notes']['divination'])
        self.assertNotIn('visible_fragments', result['divination']['grid'])

    async def test_present_covered_parent_is_validated_before_omitting_it(self):
        client = DivinationClient(); client.raw = text_board()
        client.raw['event']['description'] = 'Hidden parent text'
        result = await GameTools(client).inspect_event({'preset': 'summary'})
        self.assertEqual(result.get('error', {}).get('code'), 'transport_error')

    async def test_native_board_details_need_not_repeat_the_covered_parent_event(self):
        client = DivinationClient(); client.raw = text_board(); client.raw.pop('event')
        result = await GameTools(client).inspect_event({'include_image': True})
        self.assertNotIn('error', result)
        self.assertTrue(getattr(result, 'image', None))

    async def test_observation_presets_share_static_event_without_narrative_or_false_warning(self):
        for preset in ('full', 'default', 'summary'):
            with self.subTest(preset=preset):
                client = EventClient()
                client.raw['event']['options'].append({
                    'id': 1, 'title': 'Leave', 'description': 'Leave.', 'enabled': False,
                    'lethal_warning': False, 'hover_tips': []})
                result = await GameTools(client).get_observation({'preset': preset})
                self.assertNotIn('description', result['event'])
                self.assertEqual(result['event']['options'][0]['description'], 'Lose 3 HP.')
                self.assertTrue(result['event']['options'][0]['lethal_warning'])
                self.assertNotIn('lethal_warning', result['event']['options'][1])
                self.assertFalse(result['event']['options'][1]['enabled'])
                self.assertNotIn('hover_tips', str(result))

    async def test_inspection_summary_omits_help_and_narrative_but_full_keeps_them(self):
        tools = GameTools(EventClient())
        for preset in ('full', 'default'):
            result = await tools.inspect_event({'preset': preset})
            self.assertEqual(result['event']['description'], 'The water is warm.')
            self.assertEqual(result['event']['options'][0]['hover_tips'][0]['title'], 'Max HP')
        result = await tools.inspect_event({'preset': 'summary'})
        self.assertNotIn('error', result)
        self.assertNotIn('description', result['event'])
        self.assertNotIn('hover_tips', result['event']['options'][0])

    async def test_bad_context_rejects_even_summary_and_does_not_authorize(self):
        for factory, screen in ((event_state, {'status': 'covered', 'view': 'map'}),
                                (text_board, {'status': 'covered', 'view': 'deck'})):
            for preset in ('full', 'summary'):
                with self.subTest(factory=factory.__name__, preset=preset):
                    client = EventClient(); client.raw = factory(); client.raw['screen'] = screen
                    tools = GameTools(client)
                    result = await tools.inspect_event({'preset': preset})
                    self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                    self.assertIsNone(tools.session.permission.token)

    async def test_text_board_works_without_png_and_summary_keeps_all_fragments(self):
        for operation in ('get_observation', 'inspect_event'):
            for preset in ('full', 'default', 'summary'):
                with self.subTest(operation=operation, preset=preset):
                    client = DivinationClient(); client.raw = text_board()
                    client.raw.pop('divination_image')
                    result = await getattr(GameTools(client), operation)({'preset': preset})
                    self.assertNotIn('error', result)
                    self.assertEqual(result['divination']['grid']['cell_rows'][5], '#####s#####')
                    self.assertEqual(result['divination']['grid']['visible_fragments'],
                                     [{'x': 5, 'y': 5, 'appearance': 'potion.base'}])
                    self.assertNotIn('image', result['divination']['grid'])
                    if operation == 'get_observation' or preset == 'summary':
                        self.assertNotIn('instructions', result['divination'])
                    else:
                        self.assertIn('instructions', result['divination'])

    async def test_explicit_image_requires_valid_png_and_never_reaches_observation_arguments(self):
        client = DivinationClient(); client.raw = text_board()
        result = await GameTools(client).inspect_event({'include_image': True})
        self.assertNotIn('error', result)
        self.assertTrue(getattr(result, 'image', None))
        client.raw['divination_image']['png_base64'] = 'broken'
        tools = GameTools(client)
        result = await tools.inspect_event({'include_image': True})
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.session.permission.token)
        for operation, arguments in (('get_observation', {'include_image': True}),
                                     ('inspect_event', {'include_image': 1}),
                                     ('inspect_event', {'option_ids': []})):
            result = await getattr(GameTools(EventClient()), operation)(arguments)
            self.assertEqual(result['error']['code'], 'invalid_request')

    async def test_malformed_fragments_are_rejected_before_summary_and_permission(self):
        changes = [
            lambda grid: grid['visible_fragments'].clear(),
            lambda grid: grid['visible_fragments'].append(copy.deepcopy(grid['visible_fragments'][0])),
            lambda grid: grid['visible_fragments'][0].update(x=0),
            lambda grid: grid['visible_fragments'][0].update(x=True),
            lambda grid: grid['visible_fragments'][0].update(appearance='secret_relic_model'),
            lambda grid: grid.update(cell_rows=['###########'] * 11),
        ]
        for change in changes:
            with self.subTest(change=change):
                client = DivinationClient(); client.raw = text_board()
                change(client.raw['divination']['grid'])
                tools = GameTools(client)
                result = await tools.inspect_event({'preset': 'summary'})
                self.assertEqual(result['error']['code'], 'transport_error')
                self.assertIsNone(tools.session.permission.token)
