"""Action permissions, visible transfers and narrowly scoped default compaction."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.null_fields import apply_preset
from sts2_mcp.output.transition_details import end_turn_details
from tests.python.test_action_observations import Client
from tests.python.test_output_boundaries import observation


def moved():
    return {'sequence': 1, 'type': 'card_moved', 'card': {'id': 6, 'name': 'Defend'},
            'from_pile': 'discard', 'to_pile': 'draw'}


class TransitionProjectionTests(unittest.TestCase):
    def state(self, event):
        return {**observation(), 'transition': {'stop_reason': 'player_ready', 'complete': True, 'events': [event]}}

    def test_movement_is_validated_without_exporting_positions(self):
        event = {**moved(), 'position': 'top', 'internal_index': 0}
        self.assertEqual(end_turn_details(self.state(event))['transition']['events'], [moved()])
        for field, value in [('from_pile', 'deck'), ('to_pile', None), ('from_pile', 1),
                             ('to_pile', 'discard'), ('card', {'id': True, 'name': 'Defend'})]:
            with self.subTest(field=field, value=value), self.assertRaises((ValueError, TypeError, KeyError)):
                end_turn_details(self.state({**moved(), field: value}))
        for key in ('from_pile', 'to_pile', 'card'):
            event = moved(); del event[key]
            with self.subTest(missing=key), self.assertRaises((ValueError, TypeError, KeyError)):
                end_turn_details(self.state(event))

    def test_default_only_omits_false_autoplay_on_card_played(self):
        payload = {'autoplay': False, 'transition': {'complete': False, 'events': [
            {'type': 'card_played', 'autoplay': False, 'source': None},
            {'type': 'card_played', 'autoplay': True},
            {'type': 'power_changed', 'autoplay': False, 'before': None, 'after': None}]}}
        original = copy.deepcopy(payload)
        expected = copy.deepcopy(payload)
        del expected['transition']['events'][0]['autoplay']
        self.assertEqual(apply_preset(payload, 'default'), expected)
        self.assertEqual(apply_preset(payload, 'full'), original)
        self.assertEqual(payload, original)


class TurnSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_end_turn_explicit_preflight_rejection_preserves_existing_permission(self):
        class Rejection(Client):
            def call(self, operation, expected_state=None, **kwargs):
                if operation == 'end_turn':
                    return {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False,
                        'public_message': 'Resolve the current card selection before ending the turn.'},
                        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}
                return super().call(operation, expected_state, **kwargs)
        tools = GameTools(Rejection())
        await tools.get_observation()
        result = await tools.end_turn()
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertIn('selection', result['error']['message'])
        self.assertNotIn('error', await tools.play_card({'card_id': 0}))

    async def test_uncertain_stale_and_contradictory_rejections_do_not_restore_permission(self):
        for code, flag, interaction in [('illegal_action', None, False), ('illegal_action', True, True), ('illegal_action', False, True),
                                         ('stale_state', False, False), ('expired_request', False, False)]:
            class Rejection(Client):
                def call(self, operation, expected_state=None, **kwargs):
                    if operation != 'end_turn': return super().call(operation, expected_state, **kwargs)
                    error = {'code': code}
                    if flag is not None: error['action_submitted'] = flag
                    return {'ok': False, 'error': error, 'execution': {'ui_interaction_started': interaction,
                        'action_submission_observed': flag is True, 'state_captured': True}}
            with self.subTest(code=code, flag=flag):
                tools = GameTools(Rejection())
                await tools.get_observation()
                await tools.end_turn()
                self.assertEqual((await tools.play_card({'card_id': 0}))['error']['code'], 'observation_required')

    async def test_stopped_results_keep_legal_inspections_without_authorizing_actions(self):
        for reason, complete in [('combat_won', True), ('combat_lost', True), ('timeout', False),
                                 ('interrupted', False), ('player_ready', False)]:
            with self.subTest(reason=reason, complete=complete):
                client = Client(); client.reason = reason; client.complete = complete
                client.actions = ['inspect_hand', 'inspect_relics', 'inspect_deck', 'play_card', 'end_turn']
                tools = GameTools(client)
                await tools.get_observation()
                result = await tools.end_turn()
                self.assertEqual(result['available_actions'], ['inspect_hand', 'inspect_relics', 'inspect_deck'])
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')
                self.assertNotIn('error', await tools.inspect_hand())

    async def test_false_autoplay_is_validated_before_default_projection(self):
        for preset in ('full', 'default'):
            client = Client()
            client.mutate_reply = lambda state: state['transition'].update(events=[{
                'sequence': 1, 'type': 'card_played', 'card': {'id': 0, 'name': 'Strike'}, 'autoplay': 'false'}])
            tools = GameTools(client)
            await tools.get_observation()
            self.assertEqual((await tools.end_turn({'preset': preset}))['error']['code'], 'transport_error')
            self.assertIsNone(tools.snapshot_id)
