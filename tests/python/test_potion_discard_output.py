"""A discard receipt reports this request; events retain only witnessed changes."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from sts2_mcp.output.inspection_details import inspection_details
from tests.python.test_output_boundaries import observation
from tests.python.test_selection import selection


def event():
    return {'sequence': 1, 'type': 'potion_discarded',
            'potion': {'slot_index': 1, 'name': 'Block Potion'}}


def receipt(status='discarded'):
    state = observation()
    state['potion_discard'] = {'slot_index': 1, 'name': 'Block Potion', 'status': status}
    state['transition'] = {'stop_reason': 'player_ready', 'complete': True,
                           'events': [event()] if status == 'discarded' else []}
    state['available_actions'] = ['end_turn', 'use_potion', 'discard_potion', 'inspect_potions']
    if status == 'queued':
        state.update(screen={'status': 'covered'}, selection=selection(),
                     available_actions=['select_card', 'selection_option', 'discard_potion', 'inspect_selection'])
        state['transition']['stop_reason'] = 'choice_required'
    if status == 'not_discarded':
        state['transition']['stop_reason'] = 'action_canceled'
    return state


class DiscardClient:
    def __init__(self, status='discarded'):
        self.status = status
        self.revision = 1
        self.calls = []
        self.mutate = lambda state: None

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        self.calls.append((operation, expected_state, arguments))
        if operation != 'get_state':
            assert expected_state == f'state-{self.revision}'
            self.revision += 1
        state = receipt(self.status)
        if operation == 'get_state':
            state.pop('potion_discard'); state.pop('transition')
        elif operation != 'discard_potion':
            state.pop('potion_discard')
            state['transition'] = {'stop_reason': 'player_ready', 'complete': True, 'events': [event()]}
            state.pop('selection', None); state['screen'] = {'status': 'visible'}
            state['available_actions'] = ['end_turn']
        self.mutate(state)
        state['snapshot_id'] = f'state-{self.revision}'
        return {'ok': True, 'state': state}


class PotionDiscardOutputTests(unittest.TestCase):
    def test_result_is_top_level_and_filters_unrequested_internal_data(self):
        raw = receipt(); raw['potion_discard']['model_id'] = 'hidden'
        result = inspection_details('discard_potion', raw, {'potion_slot': 1})
        self.assertEqual(result['potion_discard'], {'slot_index': 1, 'name': 'Block Potion', 'status': 'discarded'})
        self.assertEqual(result['transition']['events'], [event()])

    def test_invalid_identity_status_and_missing_visible_discard_are_rejected(self):
        mutations = [lambda s: s.pop('potion_discard'),
            lambda s: s.update(potion_discard=None),
            lambda s: s['potion_discard'].pop('name'),
            lambda s: s['potion_discard'].update(name=None),
            lambda s: s['potion_discard'].update(name=''),
            lambda s: s['potion_discard'].update(slot_index=True),
            lambda s: s['potion_discard'].update(slot_index=-1),
            lambda s: s['potion_discard'].update(slot_index=2**31),
            lambda s: s['potion_discard'].update(slot_index=0),
            lambda s: s['potion_discard'].update(status='finished'),
            lambda s: s['transition'].update(events=[]),
            lambda s: s['transition']['events'][0]['potion'].update(name='Fire Potion')]
        for mutate in mutations:
            state = receipt(); mutate(state)
            with self.subTest(state=state), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details('discard_potion', state, {'potion_slot': 1})

    def test_queued_requires_a_complete_visible_choice_and_no_discard_event(self):
        for mutate in (lambda s: s['transition'].update(stop_reason='player_ready'),
                       lambda s: s['transition'].update(complete=False),
                       lambda s: s['transition'].update(events=[event()]),
                       lambda s: s.update(selection=None),
                       lambda s: s['selection'].update(status='battlefield')):
            state = receipt('queued'); mutate(state)
            with self.subTest(state=state), self.assertRaises((ValueError, KeyError, TypeError)):
                inspection_details('discard_potion', state, {'potion_slot': 1})

    def test_other_actions_do_not_gain_a_discard_result(self):
        raw = receipt()
        for operation in ('use_potion', 'select_card', 'end_turn', 'get_state'):
            self.assertNotIn('potion_discard', inspection_details(operation, raw))


class PotionDiscardPermissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_immediate_full_and_default_keep_result_and_event_and_allow_next_action(self):
        for preset in ('full', 'default'):
            tools = GameTools(DiscardClient())
            await tools.get_observation()
            result = await tools.discard_potion({'potion_slot': 1, 'preset': preset})
            self.assertEqual(result['potion_discard']['status'], 'discarded')
            self.assertEqual(result['transition']['events'], [event()])
            self.assertNotIn('player', result)
            self.assertNotIn('error', await tools.end_turn())
            self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'discard_potion', 'end_turn'])

    async def test_queued_allows_another_slot_and_selection_without_a_new_read(self):
        tools = GameTools(DiscardClient('queued'))
        await tools.get_observation()
        queued = await tools.discard_potion({'potion_slot': 1})
        self.assertEqual(queued['potion_discard']['status'], 'queued')
        self.assertEqual(queued['transition']['events'], [])
        self.assertIn('discard_potion', queued['available_actions'])
        self.assertIn('select_card', queued['available_actions'])
        resolved = await tools.select_card({'card_id': 5})
        self.assertNotIn('error', resolved)
        self.assertNotIn('potion_discard', resolved)
        self.assertEqual(resolved['transition']['events'], [event()])
        self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'discard_potion', 'select_card'])

    async def test_unknown_and_canceled_never_restore_action_permission(self):
        for status in ('unknown', 'not_discarded'):
            tools = GameTools(DiscardClient(status))
            await tools.get_observation()
            result = await tools.discard_potion({'potion_slot': 1})
            self.assertEqual(result['potion_discard']['status'], status)
            self.assertIsNone(tools.snapshot_id)
            self.assertNotIn('end_turn', result['available_actions'])
            self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')

    async def test_malformed_result_after_submission_clears_permission(self):
        client = DiscardClient(); tools = GameTools(client)
        await tools.get_observation()
        client.mutate = lambda s: s.pop('potion_discard', None)
        self.assertIn('error', await tools.discard_potion({'potion_slot': 1}))
        self.assertIsNone(tools.snapshot_id)
