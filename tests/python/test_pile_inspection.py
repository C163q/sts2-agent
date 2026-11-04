"""Pile filters, passive faces and explicit preflight rejection recovery."""
import copy
import json
import subprocess
import sys
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.null_fields import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.python.test_mcp_server import FakeGame, SERVER
from tests.python.test_mcp_piles import opened
from tests.python.test_deck_inspection import deck_observation


def pile_observation():
    state = deck_observation()
    for key in ('deck', 'view_upgrades', 'sort'): state.pop(key)
    state.update(screen={'status': 'covered', 'view': 'draw_pile'}, pile='draw',
        message='Cards shown are sorted by rarity.', cards=opened()['cards'])
    state['cards'][0].update(enchantment=None, affliction={'name': 'Bound'})
    return state


class PileObservationTests(unittest.TestCase):
    def test_observation_keeps_static_faces_without_hover_or_summary_help(self):
        state = pile_observation()
        original = copy.deepcopy(state)
        full = decode_success('get_state', state)
        self.assertEqual(full['pile'], 'draw')
        self.assertEqual(full['message'], 'Cards shown are sorted by rarity.')
        card = full['cards'][0]
        self.assertEqual(card['id'], 'pile:0')
        self.assertIsNone(card['enchantment'])
        self.assertNotIn('description', card)
        self.assertNotIn('hover_tips', card)
        self.assertNotIn('hover_tips', full)
        self.assertNotIn('enchantment', apply_preset(full, 'default')['cards'][0])
        summary = observation_preset(full, 'summary')
        self.assertEqual(summary['cards'], [{'id': 'pile:0', 'name': 'Defend', 'type': 'Skill',
            'energy_cost': '1', 'affliction': {'name': 'Bound'}}])
        self.assertNotIn('message', summary)
        for preset in ('actions_only', 'top_bar'):
            self.assertFalse({'pile', 'cards', 'message'} & observation_preset(full, preset).keys())
        self.assertEqual(state, original)

    def test_partial_or_wrong_page_content_cannot_survive_decode(self):
        for change in ({'pile': 'hand'}, {'screen': {'status': 'covered', 'view': 'deck'}},
                       {'cards': None}, {'cards': [{'id': 'pile:0'}]}, {'message': None},
                       {'screen': {'status': 'visible'}}, {'scene': 'main_menu'}):
            with self.subTest(change=change):
                state = pile_observation()
                state.update(change)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    decode_success('get_state', state)
        for missing in ('pile', 'cards', 'message'):
            state = pile_observation()
            state.pop(missing)
            with self.subTest(missing=missing), self.assertRaises((ValueError, KeyError)):
                decode_success('get_state', state)


class PileInspectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_filters_keep_native_order_help_and_partial_success(self):
        for preset in ('full', 'default', 'summary'):
            with self.subTest(preset=preset), FakeGame() as game:
                payload = opened()
                other = copy.deepcopy(payload['cards'][0])
                other.update(id='pile:7', name='Guard')
                payload['cards'].append(other)
                game.pile_payload = payload
                tools = GameTools(Client(game.directory))
                result = await tools.inspect_pile({'pile': 'draw', 'preset': preset,
                    'card_ids': ['pile:7', 'pile:999', 'pile:0', 'pile:7', 'pile:998']})
                self.assertNotIn('error', result)
                self.assertEqual([c['id'] for c in result['cards']], ['pile:0', 'pile:7'])
                self.assertEqual(result['errors'], [{'code': 'cards_not_in_pile',
                    'card_ids': ['pile:999', 'pile:998']}])
                self.assertEqual(game.operations[-1]['arguments'], {'pile': 'draw'})
                if preset == 'summary':
                    self.assertNotIn('hover_tips', result)
                    self.assertNotIn('message', result)
                else:
                    self.assertEqual(result['hover_tips'][0]['card_ids'], ['pile:0', 'pile:7'])
                    single = await tools.inspect_pile({'pile': 'draw', 'preset': preset, 'card_ids': ['pile:7']})
                    self.assertEqual(single['hover_tips'][0]['card_ids'], ['pile:7'])

    async def test_null_empty_and_complete_validation_before_filter(self):
        with FakeGame() as game:
            game.pile_payload = opened()
            tools = GameTools(Client(game.directory))
            all_cards = await tools.inspect_pile({'pile': 'draw', 'preset': 'full'})
            self.assertEqual(await tools.inspect_pile({'pile': 'draw', 'preset': 'full', 'card_ids': None}), all_cards)
            for preset in ('full', 'default', 'summary'):
                empty = await tools.inspect_pile({'pile': 'draw', 'preset': preset, 'card_ids': []})
                self.assertEqual(empty['cards'], [])
                self.assertEqual(empty['status'], 'opened')
                if preset != 'summary': self.assertEqual(empty['hover_tips'], [])
            game.pile_payload['cards'][0]['description'] = False
            bad = await tools.inspect_pile({'pile': 'draw', 'preset': 'summary', 'card_ids': []})
            self.assertEqual(bad['error']['code'], 'transport_error')

    async def test_empty_and_unavailable_preserve_feedback_but_differ_on_membership(self):
        for status, cards in [('empty', []), ('unavailable', None)]:
            for preset in ('full', 'default', 'summary'):
                with self.subTest(status=status, preset=preset), FakeGame() as game:
                    game.pile_payload = {'scene': 'combat', 'screen': {'status': 'visible'},
                        'pile': 'discard', 'status': status, 'cards': cards, 'message': 'Native feedback.'}
                    if status == 'unavailable': game.pile_payload['reason'] = 'entry_disabled'
                    tools = GameTools(Client(game.directory))
                    result = await tools.inspect_pile({'pile': 'discard', 'preset': preset, 'card_ids': ['pile:9']})
                    self.assertEqual(result['message'], 'Native feedback.')
                    if status == 'empty':
                        self.assertEqual(result['cards'], [])
                        self.assertEqual(result['errors'], [{'code': 'cards_not_in_pile', 'card_ids': ['pile:9']}])
                    else:
                        self.assertNotIn('errors', result)
                        self.assertEqual(result['reason'], 'entry_disabled')
                        if preset == 'full': self.assertIsNone(result['cards'])
                        else: self.assertNotIn('cards', result)

    async def test_invalid_ids_preserve_permission_without_ipc(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            for ids in ([1], [True], ['pile:01'], ['pile:-1'], ['pile:1\n'], ['deck:1'], 'pile:1'):
                result = await tools.inspect_pile({'pile': 'draw', 'card_ids': ids})
                self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertEqual([op['operation'] for op in game.operations], ['get_state'])
            self.assertNotIn('error', await tools.end_turn())

    async def test_only_explicit_no_interaction_guarantee_retains_old_permission(self):
        for flag, interaction, observed, expected in [
            (True, False, True, 'choose_legal_action'), (True, False, False, 'get_observation'),
            (None, False, True, 'get_observation'), (False, True, True, 'get_observation'),
            (True, True, True, 'check_connection')]:
            with self.subTest(flag=flag, interaction=interaction, observed=observed), FakeGame() as game:
                base = Client(game.directory)
                class RejectedClient:
                    def call(self, operation, expected_state=None, **kwargs):
                        if operation != 'inspect_pile': return base.call(operation, expected_state, **kwargs)
                        error = {'code': 'illegal_action', 'message': '/private/path',
                            'public_message': 'Return from the card selection before opening a pile.'}
                        if flag is not None: error['ui_unchanged'] = flag
                        return {'ok': False, 'error': error, 'execution': {'ui_interaction_started': interaction,
                            'action_submission_observed': False, 'state_captured': True}}
                tools = GameTools(RejectedClient())
                if observed: await tools.get_observation()
                result = await tools.inspect_pile({'pile': 'draw'})
                self.assertEqual(result['error']['recovery'], expected)
                self.assertNotIn('/private', json.dumps(result))
                continued = await tools.end_turn()
                self.assertEqual('error' not in continued, flag is True and not interaction and observed)


class PileCliTests(unittest.TestCase):
    def test_file_cli_filters_and_does_not_forward_ids(self):
        with FakeGame() as game:
            game.pile_payload = opened()
            command = [sys.executable, str(SERVER.with_name('roundtrip_client.py')), '--ipc-dir', str(game.directory),
                'inspect_pile', '--pile', 'draw', '--preset', 'summary', '--card-ids', 'pile:0']
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload['cards'], [{'id': 'pile:0', 'name': 'Defend', 'type': 'Skill', 'energy_cost': '1'}])
            self.assertNotIn('message', payload)
            self.assertEqual(game.operations[-1]['arguments'], {'pile': 'draw'})
