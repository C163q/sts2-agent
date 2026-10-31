import asyncio
import threading
import unittest

import anyio

from game_tools import GameTools
from test_output_boundaries import observation
from test_selection import selection


class Client:
    def __init__(self):
        self.revision = 1
        self.calls = []
        self.reason = 'player_ready'
        self.complete = True
        self.actions = ['play_card', 'end_turn', 'use_potion', 'discard_potion']
        self.reply_error = None
        self.mutate_reply = lambda state: None

    @property
    def token(self):
        return f'state-{self.revision}'

    def call(self, operation, expected_state=None, arguments=None):
        self.calls.append((operation, expected_state, arguments))
        if operation == 'inspect_hand':
            return {'ok': True, 'state': {'snapshot_id': self.token, 'hand': []}}
        if operation == 'inspect_selection':
            choice = selection()
            choice['cards'][0]['hover_tips'] = []
            return {'ok': True, 'state': {'snapshot_id': self.token, 'scene': 'card_selection', 'selection': choice}}
        if operation != 'get_state':
            if self.reply_error:
                if isinstance(self.reply_error, Exception):
                    raise self.reply_error
                return {'ok': False, 'error': {'code': self.reply_error}}
            if expected_state != self.token:
                return {'ok': False, 'error': {'code': 'stale_state'}}
            self.revision += 1
        state = observation()
        state.update(snapshot_id=self.token, available_actions=self.actions.copy(), selection=None)
        if operation != 'get_state':
            state['transition'] = {'stop_reason': self.reason, 'complete': self.complete, 'events': []}
            if self.reason == 'choice_required':
                state.update(selection=selection(), screen={'status': 'covered'},
                             available_actions=['select_card', 'selection_option'])
            self.mutate_reply(state)
        return {'ok': True, 'state': state}


class ActionObservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actions_return_only_context_and_complete_event_journal(self):
        actions = [('play_card', {'card_id': 0}), ('end_turn', None),
                   ('use_potion', {'potion_slot': 0}), ('discard_potion', {'potion_slot': 0}),
                   ('select_card', {'card_id': 5}), ('selection_option', {'option_id': 'confirm'})]
        event = {'type': 'card_drawn', 'sequence': 1, 'card': {'id': 8, 'name': 'Strike'}}
        for name, arguments in actions:
            with self.subTest(action=name):
                client = Client()
                client.mutate_reply = lambda state: state['transition'].update(events=[event])
                tools = GameTools(client)
                observed = await tools.get_observation()
                self.assertIn('player', observed)
                result = await getattr(tools, name)(arguments)
                self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'transition'})
                self.assertEqual(result['transition']['events'], [event])
                self.assertEqual(tools.snapshot_id, 'state-2')

    async def test_choice_receipt_omits_candidates_but_inspection_still_returns_them(self):
        client = Client(); client.reason = 'choice_required'
        tools = GameTools(client)
        await tools.get_observation()
        result = await tools.play_card({'card_id': 0})
        self.assertEqual(result['selection'], {'type': 'choose_one', 'status': 'visible'})
        self.assertEqual(set(result['notes']), {'selection'})
        self.assertIn('set_selection_view', result['notes']['selection'])
        self.assertNotIn('player', result)
        self.assertEqual(tools.snapshot_id, 'state-2')
        inspected = await tools.inspect_selection()
        self.assertEqual(inspected['selection']['cards'][0]['id'], 5)
        self.assertEqual(tools.snapshot_id, 'state-2')

    async def test_manual_input_note_and_incomplete_journal_survive_projection(self):
        for reason, complete in [('manual_input_required', True), ('timeout', False)]:
            with self.subTest(reason=reason):
                client = Client(); client.reason = reason; client.complete = complete
                tools = GameTools(client)
                await tools.get_observation()
                result = await tools.end_turn()
                self.assertNotIn('player', result)
                self.assertEqual(result['transition'], {'stop_reason': reason, 'complete': complete, 'events': []})
                if reason == 'manual_input_required':
                    self.assertEqual(set(result['notes']), {'interaction'})
                self.assertIsNone(tools.snapshot_id)

    async def test_purchase_and_reward_receipts_keep_native_outcome(self):
        from test_shop import state as shop_state
        from test_rewards import state as reward_state
        for operation, arguments, make_state, key, outcome in [
                ('buy_item', {'item_id': 0}, shop_state, 'purchase_result', {'item_id': 0, 'status': 'failure_space'}),
                ('claim_reward', {'reward_id': 12}, reward_state, 'reward_result', {'reward_id': 12, 'status': 'not_obtained'})]:
            class ReceiptClient:
                def call(self, name, expected_state=None, arguments=None):
                    state = make_state()
                    if name != 'get_state':
                        state.update(transition={'stop_reason': 'action_completed', 'complete': True, 'events': []},
                                     **{key: outcome})
                    return {'ok': True, 'state': state}
            with self.subTest(operation=operation):
                tools = GameTools(ReceiptClient())
                await tools.get_observation()
                result = await getattr(tools, operation)(arguments)
                self.assertEqual(result[key], outcome)
                self.assertEqual(set(result), {'scene', 'screen', 'available_actions', 'transition', key})

    async def test_divination_receipt_is_text_only_but_inspection_preserves_image(self):
        from mcp_server import tool_result
        from test_divination import DivinationClient
        tools = GameTools(DivinationClient())
        observed = tool_result(await tools.get_observation())
        self.assertEqual([c.type for c in observed.content], ['text', 'image'])
        receipt = tool_result(await tools.divine({'x': 0, 'y': 0}))
        self.assertEqual(set(receipt.structuredContent), {'scene', 'screen', 'available_actions', 'transition'})
        self.assertEqual([c.type for c in receipt.content], ['text'])
        self.assertIsNotNone(tools.snapshot_id)
        inspected = tool_result(await tools.inspect_event())
        self.assertEqual([c.type for c in inspected.content], ['text', 'image'])

    async def test_all_six_actions_advance_the_token_without_extra_observation(self):
        actions = [('play_card', {'card_id': 0}), ('end_turn', None),
                   ('use_potion', {'potion_slot': 0}), ('discard_potion', {'potion_slot': 0}),
                   ('select_card', {'card_id': 5}), ('selection_option', {'option_id': 'confirm'})]
        for name, arguments in actions:
            with self.subTest(action=name):
                client = Client()
                tools = GameTools(client)
                await tools.get_observation()
                result = await (getattr(tools, name)() if arguments is None else getattr(tools, name)(arguments))
                self.assertNotIn('error', result)
                self.assertEqual(tools.snapshot_id, 'state-2')
                following = await tools.end_turn()
                self.assertNotIn('error', following)
                self.assertEqual(client.calls, [('get_state', None, None), (name, 'state-1', arguments),
                                                ('end_turn', 'state-2', None)])
                self.assertEqual(tools.snapshot_id, 'state-3')
                self.assertNotIn('snapshot_id', result)

    async def test_choice_result_authorizes_selection_then_confirmation(self):
        client = Client()
        client.reason = 'choice_required'
        tools = GameTools(client)
        await tools.get_observation()
        await tools.use_potion({'potion_slot': 0})
        await tools.select_card({'card_id': 5})
        client.reason = 'player_ready'
        result = await tools.selection_option({'option_id': 'confirm'})
        self.assertNotIn('error', result)
        self.assertEqual([call[1] for call in client.calls], [None, 'state-1', 'state-2', 'state-3'])
        self.assertEqual([call[0] for call in client.calls].count('get_state'), 1)

    async def test_noncombat_completed_potion_can_chain_to_discard(self):
        client = Client()
        client.reason = 'action_completed'
        client.mutate_reply = lambda state: state.update(scene='loading_or_noncombat', player=None,
                                                         enemies=None, turn=None, buttons=None)
        tools = GameTools(client)
        await tools.get_observation()
        await tools.use_potion({'potion_slot': 0})
        self.assertNotIn('error', await tools.discard_potion({'potion_slot': 1}))
        self.assertEqual([call[0] for call in client.calls], ['get_state', 'use_potion', 'discard_potion'])

    async def test_noninteractive_or_incomplete_results_clear_permission(self):
        cases = [('timeout', False, lambda state: None), ('interrupted', False, lambda state: None),
                 ('player_ready', False, lambda state: None), ('action_canceled', True, lambda state: None),
                 ('combat_won', True, lambda state: None), ('combat_lost', True, lambda state: None),
                 ('selection_resolved', True, lambda state: None),
                 ('manual_input_required', True, lambda state: None),
                 ('player_ready', True, lambda state: state.update(available_actions=[])),
                 ('player_ready', True, lambda state: state.update(screen={'status': 'covered'})),
                 ('player_ready', True, lambda state: state.update(selection=selection('covered'))),
                 ('choice_required', True, lambda state: state.update(selection=selection('unsupported')))]
        for reason, complete, mutate in cases:
            with self.subTest(reason=reason, complete=complete, mutate=mutate):
                client = Client()
                tools = GameTools(client)
                await tools.get_observation()
                await tools.end_turn()
                client.reason, client.complete, client.mutate_reply = reason, complete, mutate
                await tools.end_turn()
                self.assertIsNone(tools.snapshot_id)
                count = len(client.calls)
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')
                self.assertEqual(len(client.calls), count)

    async def test_failures_after_a_successful_chain_do_not_retry_or_restore_permission(self):
        for error in ['stale_state', 'illegal_action', 'expired_request', 'game_error', TimeoutError(), OSError()]:
            with self.subTest(error=error):
                client = Client()
                tools = GameTools(client)
                await tools.get_observation()
                await tools.end_turn()
                client.reply_error = error
                result = await tools.end_turn()
                self.assertIn('error', result)
                self.assertIsNone(tools.snapshot_id)
                self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')
                self.assertEqual([call[0] for call in client.calls], ['get_state', 'end_turn', 'end_turn'])

    async def test_corrupt_action_result_cannot_grant_a_new_token(self):
        for mutate in [lambda state: state.pop('screen'), lambda state: state.update(snapshot_id=''),
                       lambda state: state['transition'].update(complete='yes'),
                       lambda state: state['player'].update(hp=True)]:
            with self.subTest(mutate=mutate):
                client = Client()
                tools = GameTools(client)
                await tools.get_observation()
                await tools.end_turn()
                client.mutate_reply = mutate
                self.assertEqual((await tools.end_turn())['error']['code'], 'transport_error')
                self.assertIsNone(tools.snapshot_id)

    async def test_external_state_change_rejects_the_chained_action_without_refresh(self):
        client = Client()
        tools = GameTools(client)
        await tools.get_observation()
        await tools.end_turn()
        client.revision += 1
        result = await tools.play_card({'card_id': 0})
        self.assertEqual(result['error']['code'], 'stale_state')
        self.assertEqual(client.calls[-1], ('play_card', 'state-2', {'card_id': 0}))
        self.assertEqual(len(client.calls), 3)
        self.assertIsNone(tools.snapshot_id)

    async def test_read_only_inspection_preserves_only_the_matching_action_result(self):
        client = Client()
        tools = GameTools(client)
        await tools.get_observation()
        await tools.end_turn()
        await tools.inspect_hand()
        self.assertEqual(tools.snapshot_id, 'state-2')
        client.revision += 1
        await tools.inspect_hand()
        self.assertIsNone(tools.snapshot_id)

    async def test_cancelled_action_does_not_publish_its_new_permission(self):
        started, release = threading.Event(), threading.Event()

        class BlockingClient(Client):
            def call(self, operation, expected_state=None, arguments=None):
                result = super().call(operation, expected_state, arguments)
                if operation == 'end_turn':
                    started.set()
                    if not release.wait(3):
                        raise TimeoutError('Test did not release the action')
                return result

        client = BlockingClient()
        tools = GameTools(client)
        await tools.get_observation()
        scopes = []

        async def act():
            with anyio.CancelScope() as scope:
                scopes.append(scope)
                await tools.end_turn()

        async with anyio.create_task_group() as group:
            group.start_soon(act)
            await anyio.to_thread.run_sync(started.wait)
            scopes[0].cancel()
            release.set()
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual((await tools.end_turn())['error']['code'], 'observation_required')
        self.assertEqual(len(client.calls), 2)


if __name__ == '__main__':
    unittest.main()
