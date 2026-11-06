"""Purchase identity, pending input and preflight proof govern continuation."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_shop import ShopClient, state
from tests.python.test_selection import selection
from tests.python.test_rewards import state as reward_state


class OutcomeClient:
    def __init__(self, status='success', *, item_id=0, mode='shop', reason='action_completed', schema=44, missing=False):
        self.status, self.item_id, self.mode = status, item_id, mode
        self.reason, self.schema, self.missing = reason, schema, missing

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        raw = state()
        if operation != 'get_state':
            if self.mode == 'rewards': raw = reward_state()
            if self.mode == 'selection':
                raw.update(screen={'status': 'covered'}, selection=selection(),
                    shop={'status': 'covered', **dict.fromkeys(('view', 'items', 'open', 'back', 'proceed'))},
                    available_actions=['select_card', 'selection_option'])
                raw['selection']['can_view_battlefield'] = False
            raw.update(snapshot_id='shop-2', schema_version=self.schema,
                transition={'stop_reason': self.reason, 'complete': self.reason not in {'timeout', 'interrupted'}, 'events': []})
            if not self.missing: raw['purchase_result'] = {'item_id': self.item_id, 'status': self.status}
        return {'ok': True, 'state': raw}


def rejection(**patch):
    return {'ok': False, 'error': {'code': 'illegal_action', 'action_submitted': False,
        'public_message': 'No current item matches item_id. inspect_shop shows the current IDs.', **patch},
        'execution': {'ui_interaction_started': False, 'action_submission_observed': False, 'state_captured': True}}


class RejectingClient(ShopClient):
    def __init__(self, response):
        super().__init__(); self.response = response

    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        if operation == 'buy_item':
            self.calls.append((operation, expected_state, arguments))
            return copy.deepcopy(self.response)
        return super().call(operation, expected_state, arguments, response_options)


class PurchaseFeedbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_explicit_preflight_retains_reason_and_allows_close(self):
        tools = GameTools(RejectingClient(rejection())); await tools.get_observation()
        result = await tools.buy_item({'item_id': 2147483647})
        self.assertEqual(result['error']['recovery'], 'choose_legal_action')
        self.assertIn('inspect_shop', result['error']['message'])
        self.assertNotIn('action_submitted', result['error'])
        self.assertNotIn('error', await tools.close_shop())
        self.assertEqual([c[0] for c in tools.client.calls], ['get_state', 'buy_item', 'close_shop'])

    async def test_unknown_stale_and_interacted_rejections_do_not_restore_permission(self):
        missing = rejection(); missing['error'].pop('action_submitted')
        interacted = rejection(); interacted['execution']['ui_interaction_started'] = True
        submitted = rejection(); submitted['execution']['action_submission_observed'] = True
        for reply in (missing, interacted, submitted, rejection(action_submitted=True),
                      rejection(code='stale_state'), rejection(code='game_error')):
            with self.subTest(reply=reply):
                tools = GameTools(RejectingClient(reply)); await tools.get_observation()
                await tools.buy_item({'item_id': 0})
                self.assertEqual((await tools.close_shop())['error']['code'], 'observation_required')

    async def test_mismatched_and_out_of_range_outcomes_clear_permission(self):
        for preset in ('default', 'full'):
            for status in ('success', 'failure_space', 'canceled', 'pending'):
                for item_id in (999, 2147483648, -1, True):
                    with self.subTest(preset=preset, status=status, item_id=item_id):
                        tools = GameTools(OutcomeClient(status, item_id=item_id,
                            mode='selection' if status == 'pending' else 'shop',
                            reason='choice_required' if status == 'pending' else 'action_completed'))
                        await tools.get_observation()
                        result = await tools.buy_item({'item_id': 0, 'preset': preset})
                        self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                        self.assertIsNone(tools.snapshot_id)
                        self.assertEqual((await tools.close_shop())['error']['code'], 'observation_required')

    async def test_matching_terminal_and_pending_results_keep_compact_receipts(self):
        variants = [(s, 'shop', 'action_completed') for s in ('success', 'failure_space', 'failure_forbidden',
            'failure_gold', 'failure_out_of_stock', 'canceled')]
        variants += [('pending', 'selection', 'choice_required'), ('pending', 'rewards', 'action_completed')]
        for preset in ('default', 'full'):
            for status, mode, reason in variants:
                with self.subTest(preset=preset, status=status, mode=mode):
                    tools = GameTools(OutcomeClient(status, mode=mode, reason=reason)); await tools.get_observation()
                    result = await tools.buy_item({'item_id': 0, 'preset': preset})
                    self.assertEqual(result.get('purchase_result'), {'item_id': 0, 'status': status})
                    self.assertNotIn('shop', result); self.assertNotIn('rewards', result)
                    self.assertIsNotNone(tools.snapshot_id)

    async def test_pending_requires_supported_input_and_a_known_boundary(self):
        for mode, reason in (('shop', 'action_completed'), ('selection', 'timeout'), ('selection', 'interrupted'),
                             ('selection', 'manual_input_required'), ('selection', 'action_completed')):
            with self.subTest(mode=mode, reason=reason):
                tools = GameTools(OutcomeClient('pending', mode=mode, reason=reason)); await tools.get_observation()
                result = await tools.buy_item({'item_id': 0})
                self.assertEqual(result.get('error', {}).get('code'), 'transport_error')
                self.assertIsNone(tools.snapshot_id)

    async def test_new_schema_known_boundaries_require_result_but_legacy_can_omit(self):
        for schema, expected in ((43, None), (44, 'transport_error')):
            with self.subTest(schema=schema):
                tools = GameTools(OutcomeClient(schema=schema, missing=True)); await tools.get_observation()
                result = await tools.buy_item({'item_id': 0})
                self.assertEqual(result.get('error', {}).get('code'), expected)
                self.assertEqual(tools.snapshot_id is None, expected is not None)

    async def test_unknown_boundaries_may_omit_result_and_never_authorize_actions(self):
        for reason in ('timeout', 'interrupted', 'manual_input_required', 'run_won', 'run_lost'):
            with self.subTest(reason=reason):
                tools = GameTools(OutcomeClient(reason=reason, missing=True)); await tools.get_observation()
                result = await tools.buy_item({'item_id': 0})
                self.assertNotIn('error', result); self.assertNotIn('purchase_result', result)
                self.assertIsNone(tools.snapshot_id)

    async def test_initial_and_local_invalid_requests_cannot_create_or_lose_permission(self):
        tools = GameTools(ShopClient())
        self.assertEqual((await tools.buy_item({'item_id': 0}))['error']['code'], 'observation_required')
        await tools.get_observation()
        for args in ({'item_id': True}, {'item_id': 2147483648}, {'item_id': 0, 'preset': 'summary'}):
            self.assertEqual((await tools.buy_item(args))['error']['code'], 'invalid_request')
        self.assertNotIn('error', await tools.close_shop())
