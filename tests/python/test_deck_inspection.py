"""Deck filters, passive browser observations and explicit rejection recovery."""
import copy
import contextlib
import io
import json
import subprocess
import sys
import unittest
from unittest.mock import patch

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.output.observation_presets import observation_preset
from sts2_mcp.output.null_fields import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.python.test_mcp_server import FakeGame, SERVER


def deck_observation():
    return {'snapshot_id': 'deck-state', 'schema_version': 39, 'scene': 'combat',
        'screen': {'status': 'covered', 'view': 'deck'}, 'turn': None, 'player': None,
        'enemies': None, 'top_bar': None, 'buttons': None,
        'available_actions': ['inspect_deck', 'close_card_view'],
        'view_upgrades': True, 'sort': {'by': 'cost', 'descending': True},
        'deck': [{'id': 'deck:8', 'name': 'Defend+', 'type': 'Skill', 'rarity': 'basic',
            'visual_card_pool': 'ironclad', 'energy_cost': '1', 'star_cost': None,
            'enchantment': None, 'affliction': {'name': 'Bound'},
            'description': 'Dedicated card effects.',
            'hover_tips': [{'title': 'Block', 'description': 'Dedicated help.'}]}]}


class DeckObservationTests(unittest.TestCase):
    def test_passive_observation_uses_face_and_shared_summary(self):
        raw = deck_observation()
        original = copy.deepcopy(raw)
        full = decode_success('get_state', raw)
        self.assertEqual(full['view_upgrades'], True)
        self.assertEqual(full['sort'], {'by': 'cost', 'descending': True})
        self.assertEqual(full['deck'][0]['id'], 'deck:8')
        self.assertIsNone(full['deck'][0]['enchantment'])
        self.assertNotIn('description', full['deck'][0])
        self.assertNotIn('hover_tips', full['deck'][0])
        self.assertNotIn('hover_tips', full)
        default = apply_preset(full, 'default')
        self.assertNotIn('enchantment', default['deck'][0])
        summary = observation_preset(full, 'summary')
        self.assertEqual(summary['deck'], [{'id': 'deck:8', 'name': 'Defend+', 'type': 'Skill',
            'energy_cost': '1', 'affliction': {'name': 'Bound'}}])
        self.assertEqual(summary['sort'], full['sort'])
        for preset in ('actions_only', 'top_bar'):
            self.assertNotIn('deck', observation_preset(full, preset))
        self.assertEqual(raw, original)

    def test_hidden_missing_and_malformed_browser_content_is_rejected(self):
        for change in ({'screen': {'status': 'visible'}}, {'sort': {'by': 'rarity', 'descending': True}},
                       {'view_upgrades': None}, {'deck': None}, {'deck': [{'id': 'deck:8'}]}):
            with self.subTest(change=change):
                raw = deck_observation()
                raw.update(change)
                with self.assertRaises((ValueError, KeyError, TypeError)):
                    decode_success('get_state', raw)
        raw = deck_observation()
        raw['deck'].append(copy.deepcopy(raw['deck'][0]))
        with self.assertRaises(ValueError):
            decode_success('get_state', raw)


class DeckInspectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_submitted_action_contradicts_an_unchanged_ui_guarantee(self):
        class InvalidClient:
            def call(self, *args, **kwargs):
                return {'ok': False, 'error': {'code': 'illegal_action', 'ui_unchanged': True,
                    'action_submitted': True}, 'execution': {'ui_interaction_started': False,
                        'action_submission_observed': False, 'state_captured': True}}
        tools = GameTools(InvalidClient())
        tools.snapshot_id = 'old'
        result = await tools.inspect_deck()
        self.assertEqual(result['error']['code'], 'transport_error')
        self.assertIsNone(tools.snapshot_id)

    async def test_unchanged_guarantee_never_creates_permission_or_applies_to_other_views(self):
        for operation, observed in [('inspect_deck', False), ('inspect_map', True)]:
            with self.subTest(operation=operation, observed=observed), FakeGame() as game:
                base = Client(game.directory)
                class RejectedClient:
                    def call(self, name, expected_state=None, **kwargs):
                        if name != operation: return base.call(name, expected_state, **kwargs)
                        return {'ok': False, 'error': {'code': 'illegal_action', 'ui_unchanged': True},
                            'execution': {'ui_interaction_started': False,
                                'action_submission_observed': False, 'state_captured': True}}
                tools = GameTools(RejectedClient())
                if observed: await tools.get_observation()
                result = await getattr(tools, operation)()
                self.assertEqual(result['error']['recovery'], 'get_observation')
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_filter_preserves_native_order_help_and_partial_errors(self):
        for preset in ('full', 'default', 'summary'):
            with self.subTest(preset=preset), FakeGame() as game:
                tools = GameTools(Client(game.directory))
                result = await tools.inspect_deck({'preset': preset,
                    'card_ids': ['deck:1', 'deck:999', 'deck:1', 'deck:998'], 'view_upgrades': True,
                    'sort_by': 'cost', 'descending': True})
                self.assertNotIn('error', result)
                self.assertEqual([c['id'] for c in result['deck']], ['deck:1'])
                self.assertEqual(result['errors'], [{'code': 'cards_not_in_deck',
                    'card_ids': ['deck:999', 'deck:998']}])
                if preset != 'summary':
                    self.assertTrue(result['hover_tips'])
                    self.assertTrue(all(t['card_ids'] == ['deck:1'] for t in result['hover_tips']))
                else:
                    self.assertNotIn('hover_tips', result)
                self.assertEqual(game.operations[-1]['arguments'],
                    {'view_upgrades': True, 'sort_by': 'cost', 'descending': True})

    async def test_null_empty_and_filtering_cannot_hide_invalid_full_cards(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            full = await tools.inspect_deck({'preset': 'full'})
            self.assertEqual(await tools.inspect_deck({'preset': 'full', 'card_ids': None}), full)
            for preset in ('full', 'default', 'summary'):
                empty = await tools.inspect_deck({'preset': preset, 'card_ids': []})
                self.assertEqual(empty['deck'], [])
                if preset != 'summary': self.assertEqual(empty['hover_tips'], [])
            game.deck_payload['deck'][0]['description'] = False
            bad = await tools.inspect_deck({'preset': 'summary', 'card_ids': []})
            self.assertEqual(bad['error']['code'], 'transport_error')

    async def test_invalid_ids_do_not_submit_or_clear_permission(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.get_observation()
            for ids in ([1], [True], ['1'], ['deck:01'], ['deck:-1'], ['pile:1'], ['deck:1\n'], 'deck:1'):
                result = await tools.inspect_deck({'card_ids': ids})
                self.assertEqual(result['error']['code'], 'invalid_request')
            self.assertEqual([o['operation'] for o in game.operations], ['get_state'])
            self.assertNotIn('error', await tools.end_turn())

    async def test_close_matches_actions_only_and_still_authorizes_actions(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            expected = await tools.get_observation({'preset': 'actions_only'})
            for preset in ('full', 'default'):
                await tools.inspect_deck()
                result = await tools.close_card_view({'preset': preset})
                self.assertEqual(result, expected)
            self.assertNotIn('error', await tools.end_turn())

    async def test_close_preserves_minimal_pending_selection(self):
        from tests.python.test_selection import state
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.inspect_deck()
            game.close_payload.update(state())
            raw = {'snapshot_id': game.token(), **game.close_payload}
            expected = observation_preset(decode_success('get_state', raw), 'actions_only')
            result = await tools.close_card_view()
            self.assertEqual(result, expected)
            self.assertEqual(result['selection'], {'type': 'choose_one', 'status': 'visible'})

    async def test_only_explicit_unchanged_deck_rejection_retains_permission(self):
        for flag, facts, expected in [
            (True, False, 'choose_legal_action'), (None, False, 'get_observation'),
            (False, False, 'get_observation'), (True, True, 'check_connection'),
            ('yes', False, 'check_connection')]:
            with self.subTest(flag=flag, facts=facts), FakeGame() as game:
                base = Client(game.directory)
                class RejectedClient:
                    def call(self, operation, expected_state=None, **kwargs):
                        if operation != 'inspect_deck': return base.call(operation, expected_state, **kwargs)
                        error = {'code': 'illegal_action', 'message': '/private/path',
                            'public_message': 'Return from the selection before opening the deck.'}
                        if flag is not None: error['ui_unchanged'] = flag
                        return {'ok': False, 'error': error, 'execution': {'ui_interaction_started': facts,
                            'action_submission_observed': False, 'state_captured': True}}
                tools = GameTools(RejectedClient())
                await tools.get_observation()
                rejection = await tools.inspect_deck()
                self.assertEqual(rejection['error']['recovery'], expected)
                self.assertNotIn('/private', json.dumps(rejection))
                continued = await tools.end_turn()
                self.assertEqual('error' not in continued, flag is True and not facts)


class DeckCliTests(unittest.TestCase):
    def test_minimal_file_close_does_not_request_board_media(self):
        from sts2_mcp import roundtrip_client
        state = deck_observation()
        for key in ('deck', 'view_upgrades', 'sort'): state.pop(key)
        state['screen'] = {'status': 'visible'}
        with patch('sys.argv', ['roundtrip_client.py', '--ipc-dir', '/tmp/unused', 'close_card_view']), \
                patch.object(roundtrip_client.Client, 'call', return_value={'ok': True, 'state': state}) as call, \
                contextlib.redirect_stdout(io.StringIO()):
            roundtrip_client.main()
        self.assertEqual(call.call_args.kwargs.get('response_options'), {'include_divination_image': False})

    def test_file_cli_filters_without_forwarding_ids_and_closes_minimally(self):
        with FakeGame() as game:
            command = [sys.executable, str(SERVER.with_name('roundtrip_client.py')), '--ipc-dir', str(game.directory)]
            result = subprocess.run([*command, 'inspect_deck', '--preset', 'summary', '--card-ids', 'deck:1'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual([c['id'] for c in json.loads(result.stdout)['deck']], ['deck:1'])
            self.assertNotIn('card_ids', game.operations[-1].get('arguments', {}))
            closed = subprocess.run([*command, 'close_card_view'], capture_output=True, text=True, timeout=10)
            self.assertEqual(closed.returncode, 0, closed.stderr)
            self.assertEqual(set(json.loads(closed.stdout)), {'scene', 'screen', 'available_actions'})
