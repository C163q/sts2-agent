import copy
import unittest

from game_output import observation_details
from inspection_details import inspection_details
from player_output import player_result
from test_output_boundaries import observation
from test_selection import selection


def state():
    raw = observation()
    raw.update(snapshot_id='ancient-1', scene='ancient', turn=None, player=None, enemies=None, buttons=None,
               selection=None, available_actions=['choose_ancient_option'], ancient={
                   'status': 'visible', 'name': 'Neow', 'epithet': None, 'description': None,
                   'dialogue': [{'speaker': 'Neow', 'text': 'Awaken.'}],
                   'options': [{'id': 0, 'title': 'New Leaf', 'description': 'Transform 1 card.', 'enabled': True,
                                'hover_tips': [{'title': 'Transform', 'description': 'Replace a card.'}], 'seed': 123}],
                   'continue': None, 'proceed': None})
    return raw


class AncientOutputTests(unittest.TestCase):
    def test_observation_includes_visible_option_text_without_hover_or_secrets(self):
        basic = player_result({'ok': True, 'state': observation_details(state())})
        self.assertEqual(basic['ancient']['options'], [{'id': 0, 'title': 'New Leaf',
                         'description': 'Transform 1 card.', 'enabled': True}])
        self.assertNotIn('seed', str(basic)); self.assertNotIn('snapshot_id', basic)

    def test_visible_epithet_is_preserved(self):
        raw = state(); raw['ancient']['epithet'] = 'Mother of Life (Banished)'
        self.assertEqual(observation_details(raw)['ancient']['epithet'], 'Mother of Life (Banished)')

    def test_inspection_adds_hover_details(self):
        public = player_result({'ok': True, 'state': inspection_details('inspect_ancient', state())})
        self.assertEqual(public['ancient']['options'][0]['hover_tips'],
                         [{'title': 'Transform', 'description': 'Replace a card.'}])

    def test_covered_ancient_must_not_contain_underlying_options_or_dialogue(self):
        raw = state(); raw['ancient']['status'] = 'covered'
        with self.assertRaises(ValueError): observation_details(raw)
        raw['ancient'] = {'status': 'covered', **dict.fromkeys(('name', 'epithet', 'description', 'dialogue', 'options', 'continue', 'proceed'))}
        self.assertIsNone(observation_details(raw)['ancient']['options'])
        with self.assertRaises(ValueError): inspection_details('inspect_ancient', raw)

    def test_invalid_option_identity_and_missing_state_are_rejected(self):
        for mutate in (lambda r: r.pop('ancient'), lambda r: r['ancient']['options'][0].update(id=True),
                       lambda r: r['ancient']['options'].append(copy.deepcopy(r['ancient']['options'][0]))):
            raw = state(); mutate(raw)
            with self.subTest(raw=raw), self.assertRaises((ValueError, KeyError)):
                observation_details(raw)

    def test_enchantment_preview_keeps_original_identity_and_visible_help(self):
        raw = state(); raw['scene'] = 'combat'; raw.pop('ancient')
        choice = selection(); card = copy.deepcopy(choice['cards'][0])
        choice.update(type='deck_enchant', selected_ids=[5], cards=[], enchantment={'title': 'Imbued', 'description': 'Play at start of combat.'},
                      enchant_previews=[{'before': card, 'after': {**card, 'description': 'Gain 5 Block. Imbued.', 'rng': 'hidden'}}])
        raw['selection'] = choice
        public = observation_details(raw)['selection']
        self.assertEqual(public['enchant_previews'][0]['after']['id'], 5)
        self.assertEqual(public['enchantment']['title'], 'Imbued')
        self.assertNotIn('rng', str(public))
        choice['enchant_previews'][0]['after']['id'] = 6
        with self.assertRaises(ValueError): observation_details(raw)

    def test_hidden_enchantment_help_and_previews_are_rejected(self):
        raw = state(); raw['scene'] = 'combat'; raw.pop('ancient')
        raw['selection'] = selection('covered')
        raw['selection'].update(type='deck_enchant', enchantment=None, enchant_previews=[])
        self.assertIsNone(observation_details(raw)['selection']['enchantment'])
        raw['selection']['enchantment'] = {'title': 'Imbued', 'description': 'Hidden'}
        with self.assertRaises(ValueError): observation_details(raw)

    def test_random_transform_never_claims_a_fixed_replacement(self):
        raw = state(); raw['scene'] = 'combat'; raw.pop('ancient')
        choice = selection(); card = copy.deepcopy(choice['cards'][0])
        choice.update(type='deck_transform', selected_ids=[5], cards=[], transform_previews=[
            {'before': card, 'after': None, 'random': True}])
        raw['selection'] = choice
        self.assertTrue(observation_details(raw)['selection']['transform_previews'][0]['random'])
        choice['transform_previews'][0]['after'] = card
        with self.assertRaises(ValueError): observation_details(raw)

    def test_bundle_candidates_preserve_grouping_and_do_not_leak_under_cover(self):
        raw = state(); raw['scene'] = 'combat'; raw.pop('ancient')
        raw['selection'] = selection()
        raw['selection'].update(type='bundle', cards=[], bundles=[{'id': 'bundle:0', 'cards': [{'id': 5, 'name': 'Defend'}]}])
        self.assertEqual(observation_details(raw)['selection']['bundles'][0]['cards'][0]['name'], 'Defend')
        raw['selection'] = selection('covered')
        raw['selection'].update(type='bundle', bundles=[{'id': 'bundle:0', 'cards': [{'id': 5, 'name': 'Defend'}]}])
        with self.assertRaises(ValueError): observation_details(raw)


class AncientClient:
    def __init__(self): self.calls = []; self.raw = state()

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'choose_ancient_option':
            self.raw.update(snapshot_id='ancient-2', transition={'stop_reason': 'action_completed', 'complete': True, 'events': []}, available_actions=['proceed'])
            self.raw['ancient'].update(options=[], proceed={'text': 'Proceed', 'enabled': True})
        if operation == 'proceed':
            self.raw.update(snapshot_id='ancient-3', transition={'stop_reason': 'action_completed', 'complete': True, 'events': []}, available_actions=[])
        return {'ok': True, 'state': copy.deepcopy(self.raw)}


class AncientSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_actions_use_permission_and_inspection_preserves_same_snapshot(self):
        from game_tools import GameTools
        client = AncientClient(); tools = GameTools(client)
        await tools.inspect_ancient()
        self.assertEqual((await tools.choose_ancient_option({'option_id': 0}))['error']['code'], 'observation_required')
        await tools.get_observation(); await tools.inspect_ancient()
        result = await tools.choose_ancient_option({'option_id': 0})
        self.assertIn('proceed', result['available_actions'])
        self.assertNotIn('error', await tools.proceed())
        self.assertEqual(client.calls[-1], ('proceed', 'ancient-2', None))

    async def test_invalid_arguments_never_reach_game(self):
        from game_tools import GameTools
        for arguments in ({'option_id': True}, {'option_id': -1}, {'option_id': '0'}, {'option_id': 0, 'extra': 0}, {}):
            client = AncientClient(); tools = GameTools(client)
            await tools.get_observation()
            self.assertEqual((await tools.choose_ancient_option(arguments))['error']['code'], 'invalid_request')
            self.assertEqual(len(client.calls), 1)

    async def test_stdio_forwards_ancient_action_arguments(self):
        import json
        import sys
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from test_mcp_server import FakeGame, SERVER

        class AncientGame(FakeGame):
            def run(self):
                client = AncientClient()
                while not self.stopped.wait(.002):
                    for path in self.requests.glob('*.json'):
                        request = json.loads(path.read_text()); self.operations.append(request)
                        response = client.call(request['operation'], request.get('expected_state'), request.get('arguments'))
                        response['id'] = request['id']
                        target = self.responses / path.name
                        temporary = target.with_suffix('.tmp'); temporary.write_text(json.dumps(response)); temporary.replace(target)
                        path.unlink()

        with AncientGame() as game:
            params = StdioServerParameters(command=sys.executable, args=[str(SERVER), '--ipc-dir', str(game.directory), '--config', str(game.config)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    await session.call_tool('get_observation', {})
                    result = await session.call_tool('choose_ancient_option', {'option_id': 0})
                    self.assertNotIn('error', result.structuredContent)
                    self.assertEqual(json.loads(result.content[0].text), result.structuredContent)
            self.assertEqual(game.operations[-1]['arguments'], {'option_id': 0})
