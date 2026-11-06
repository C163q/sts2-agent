"""Verify public counter events and explicit rest-action rejection recovery."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_rest_site import RestClient


def counter(before=0, after=1):
    return {'sequence': 1, 'type': 'relic_counter_changed', 'relic': {'name': 'Girya'},
            'before': before, 'after': after}


class FeedbackClient(RestClient):
    def __init__(self, *, rejection=None, events=None):
        super().__init__()
        self.rejection = rejection
        self.events = events

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'choose_rest_option' and arguments['option_id'] == 'BAD':
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.rejection)
        reply = super().call(operation, expected_state, arguments, response_options)
        if operation == 'choose_rest_option' and reply['ok'] and self.events is not None:
            reply['state']['transition']['events'] = copy.deepcopy(self.events)
        return reply


def rejection(**error):
    return {'ok': False, 'error': {'code': 'illegal_action', 'public_message': 'No current option matches this ID.',
            'action_submitted': False, **error},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class RestOptionFeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_rejection_retains_permission_and_reason(self):
        client = FeedbackClient(rejection=rejection())
        tools = GameTools(client)
        await tools.get_observation()
        result = await tools.choose_rest_option({'option_id': 'BAD'})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertIn('No current option', result['error']['message'])
        self.assertNotIn('error', await tools.choose_rest_option({'option_id': 'HEAL'}))
        self.assertEqual([c[0] for c in client.calls], ['get_state', 'choose_rest_option', 'choose_rest_option'])

    async def test_unknown_stale_and_interacted_rejections_cannot_restore_permission(self):
        variants = [rejection(code='stale_state'), rejection(code='game_error'), rejection(action_submitted=True)]
        missing = rejection(); missing['error'].pop('action_submitted'); variants.append(missing)
        contradictory = rejection(); contradictory['execution']['ui_interaction_started'] = True; variants.append(contradictory)
        for reply in variants:
            with self.subTest(reply=reply):
                tools = GameTools(FeedbackClient(rejection=reply))
                await tools.get_observation()
                await tools.choose_rest_option({'option_id': 'BAD'})
                result = await tools.choose_rest_option({'option_id': 'HEAL'})
                self.assertEqual(result['error']['code'], 'observation_required')

    async def test_counter_events_keep_nullable_endpoints_in_both_presets(self):
        for preset in ('full', 'default'):
            for before, after in ((0, 1), (5, 10), (None, 0), (1, None), (-1, 0)):
                with self.subTest(preset=preset, before=before, after=after):
                    event = counter(before, after)
                    tools = GameTools(FeedbackClient(events=[event]))
                    await tools.get_observation()
                    result = await tools.choose_rest_option({'option_id': 'HEAL', 'preset': preset})
                    self.assertEqual(result['transition']['events'], [event])
                    self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'transition'})

    async def test_malformed_counter_events_clear_permission(self):
        variants = [counter(None, None), counter(1, 1)]
        for patch in ({'before': True}, {'after': 1.5}, {'after': '1'}, {'relic': {'name': None}},
                      {'relic': {'name': ''}}, {'target': {'id': 0, 'kind': 'player', 'name': 'Ironclad'}},
                      {'pile': 'deck'}, {'autoplay': False}):
            variants.append({**counter(), **patch})
        for field in ('before', 'after', 'relic'):
            event = counter(); event.pop(field); variants.append(event)
        for event in variants:
            with self.subTest(event=event):
                tools = GameTools(FeedbackClient(events=[event]))
                await tools.get_observation()
                result = await tools.choose_rest_option({'option_id': 'HEAL'})
                self.assertEqual(result['error']['code'], 'transport_error')
                result = await tools.choose_rest_option({'option_id': 'HEAL'})
                self.assertEqual(result['error']['code'], 'observation_required')

    async def test_mixed_events_keep_order_and_drop_unrecognized_private_fields(self):
        events = [counter(5, 4), {'sequence': 2, 'type': 'hp_changed',
            'target': {'id': 0, 'kind': 'player', 'name': 'The Ironclad'}, 'before': 40, 'after': 41},
            {**counter(4, 3), 'sequence': 3}]
        raw = copy.deepcopy(events); raw[0]['private_model_value'] = 999
        tools = GameTools(FeedbackClient(events=raw))
        await tools.get_observation()
        result = await tools.choose_rest_option({'option_id': 'HEAL'})
        self.assertEqual(result['transition']['events'], events)
        self.assertNotIn('error', await tools.choose_rest_option({'option_id': 'HEAL'}))
