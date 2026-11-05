"""Closing a map validates the entire native response before returning minimal context."""
import copy
import json
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_tool_contracts import DATA, ContractReply


def states():
    return json.loads((DATA/'states.json').read_text())


class CloseMapResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_and_full_return_identical_minimal_context(self):
        fixtures=states()
        choice=copy.deepcopy(fixtures['observation']); choice.update(fixtures['selection'])
        for raw in (fixtures['observation'], fixtures['event'], fixtures['divination'], choice):
            for preset in ('default','full'):
                tools=GameTools(ContractReply(raw))
                result=await tools.close_map({'preset':preset})
                expected={k:raw[k] for k in ('scene','screen','available_actions')}
                if raw.get('selection') is not None:
                    expected['selection']={k:raw['selection'][k] for k in ('type','status')}
                self.assertEqual(result,expected)
                self.assertIsNone(getattr(result,'image',None))
                self.assertEqual(tools.snapshot_id,raw['snapshot_id'])

    async def test_missing_or_corrupt_room_and_selection_fail_before_projection(self):
        fixtures=states()
        choice=copy.deepcopy(fixtures['observation']); choice.update(fixtures['selection'])
        corrupt=copy.deepcopy(choice); corrupt['selection']['selected_ids']=['not an id']
        missing=copy.deepcopy(fixtures['event']); missing.pop('event')
        damaged=copy.deepcopy(fixtures['event']); damaged['event']={'invalid':'missing fields'}
        for raw in (corrupt,missing,damaged):
            tools=GameTools(ContractReply(raw)); tools.snapshot_id='previous'
            result=await tools.close_map({'preset':'full'})
            self.assertEqual(result.get('error',{}).get('code'),'transport_error',result)
            self.assertIsNone(tools.snapshot_id)

    async def test_rejections_recover_only_explicit_unchanged_existing_permission(self):
        for code,guarantee,retained in [('illegal_action',True,True),('invalid_request',True,True),
                ('illegal_action',False,False),('illegal_action',None,False),
                ('stale_state',True,False),('game_error',True,False)]:
            error={'code':code,'public_message':'The map return button is disabled.'}
            if guarantee is not None:error['ui_unchanged']=guarantee
            tools=GameTools(ContractReply({},error)); tools.snapshot_id='previous'
            result=await tools.close_map()
            self.assertEqual(tools.snapshot_id,'previous' if retained else None)
            if code=='illegal_action':
                self.assertEqual(result['error']['recovery'],'choose_legal_action' if retained else 'get_observation')
                self.assertEqual(result['error']['message'],error['public_message'])
        tools=GameTools(ContractReply({}, {'code':'illegal_action','ui_unchanged':True}))
        result=await tools.close_map()
        self.assertIsNone(tools.snapshot_id)
        self.assertEqual(result['error']['recovery'],'get_observation')

    async def test_interaction_never_claims_unchanged(self):
        class Interacted(ContractReply):
            def call(self,*args,**kwargs):
                result=super().call(*args,**kwargs)
                result['execution']={'ui_interaction_started':True,'action_submission_observed':False,'state_captured':True}
                return result
        for guarantee in (None,True):
            error={'code':'illegal_action'}
            if guarantee is not None:error['ui_unchanged']=guarantee
            tools=GameTools(Interacted({},error));tools.snapshot_id='previous'
            result=await tools.close_map()
            self.assertIsNone(tools.snapshot_id)
            self.assertEqual(result['error']['code'],'transport_error' if guarantee else 'illegal_action')

    async def test_only_default_and_full_are_accepted_without_clearing_permission(self):
        client=ContractReply(states()['observation']);tools=GameTools(client);tools.snapshot_id='previous'
        for args in ({'preset':'summary'},{'preset':'actions_only'},{'force':True}):
            result=await tools.close_map(args)
            self.assertEqual(result['error']['code'],'invalid_request')
            self.assertEqual(tools.snapshot_id,'previous')
        self.assertEqual(client.calls,[])
