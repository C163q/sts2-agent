"""Explicit close preflight evidence preserves only an existing permission."""
import json
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.roundtrip_client import Client
from tests.python.test_mcp_server import FakeGame


class CloseRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_unchanged_rejection_retains_permission_and_safe_reason(self):
        with FakeGame() as game:
            base = Client(game.directory)
            class RejectedClient:
                def call(self, operation, expected_state=None, **kwargs):
                    if operation != 'close_card_view': return base.call(operation, expected_state, **kwargs)
                    return {'ok': False, 'error': {'code': 'illegal_action', 'message': '/private/path',
                        'public_message': 'No supported card browsing page is open.', 'ui_unchanged': True},
                        'execution': {'ui_interaction_started': False, 'action_submission_observed': False,
                            'state_captured': True}}
            tools = GameTools(RejectedClient())
            await tools.get_observation()
            rejected = await tools.close_card_view()
            self.assertEqual(rejected['error']['message'], 'No supported card browsing page is open.')
            self.assertEqual(rejected['error']['recovery'], 'choose_legal_action')
            self.assertNotIn('/private', json.dumps(rejected))
            self.assertNotIn('error', await tools.end_turn())

    async def test_missing_guarantee_interaction_or_no_old_permission_cannot_authorize(self):
        for flag, interaction, observed in [(None, False, True), (False, True, True), (True, False, False)]:
            with self.subTest(flag=flag, interaction=interaction, observed=observed), FakeGame() as game:
                base = Client(game.directory)
                class RejectedClient:
                    def call(self, operation, expected_state=None, **kwargs):
                        if operation != 'close_card_view': return base.call(operation, expected_state, **kwargs)
                        error = {'code': 'illegal_action'}
                        if flag is not None: error['ui_unchanged'] = flag
                        return {'ok': False, 'error': error, 'execution': {'ui_interaction_started': interaction,
                            'action_submission_observed': False, 'state_captured': True}}
                tools = GameTools(RejectedClient())
                if observed: await tools.get_observation()
                result = await tools.close_card_view()
                self.assertEqual(result['error']['recovery'], 'get_observation')
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_contradictory_or_malformed_guarantee_fails_closed(self):
        for flag, interaction, submitted in [(True, True, False), (True, False, True), ('yes', False, False)]:
            with self.subTest(flag=flag, interaction=interaction, submitted=submitted), FakeGame() as game:
                base = Client(game.directory)
                class InvalidClient:
                    def call(self, operation, expected_state=None, **kwargs):
                        if operation != 'close_card_view': return base.call(operation, expected_state, **kwargs)
                        return {'ok': False, 'error': {'code': 'illegal_action', 'ui_unchanged': flag,
                            'action_submitted': submitted}, 'execution': {'ui_interaction_started': interaction,
                                'action_submission_observed': submitted, 'state_captured': True}}
                tools = GameTools(InvalidClient())
                await tools.get_observation()
                self.assertEqual((await tools.close_card_view())['error']['code'], 'transport_error')
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_omitted_player_is_validated_before_minimal_close_projection(self):
        with FakeGame() as game:
            tools = GameTools(Client(game.directory))
            await tools.inspect_deck()
            game.close_payload['player'] = {'hp': False, 'max_hp': 80, 'hand': []}
            self.assertEqual((await tools.close_card_view())['error']['code'], 'transport_error')
            self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')
