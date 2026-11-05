"""Reward output filters preserve identities, complete validation and static observation parity."""
import copy
import unittest

from sts2_mcp.game_tools import GameTools
from tests.python.test_rewards import state
from tests.python.test_tool_contracts import ContractReply


def details():
    raw = state()
    raw['rewards']['items'][0]['hover_tips'] = []
    raw['rewards']['items'][1]['hover_tips'] = [{'title':'Help', 'description':'Visible help.'}]
    return raw


class RewardPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_matches_default_and_summary_basic_observation(self):
        raw = details()
        expected = {'status':'visible', 'title':'Loot!', 'items':[
            {'id':12,'type':'gold','text':'17 Gold','enabled':True},
            {'id':14,'type':'card','text':'Add a card to your deck.','enabled':True}],
            'proceed':{'text':'Skip','enabled':True,'skips_remaining':True}}
        summary = await GameTools(ContractReply(raw)).inspect_rewards({'preset':'summary'})
        self.assertNotIn('error',summary)
        self.assertEqual(summary['rewards'],expected)
        for preset in ('default','summary'):
            observed = await GameTools(ContractReply(raw)).get_observation({'preset':preset})
            self.assertEqual(observed['rewards'],expected)
        observed = await GameTools(ContractReply(raw)).get_observation({'preset':'full'})
        for row in observed['rewards']['items']:
            self.assertNotIn('hover_tips',row)
            self.assertIsNone(row['linked_group'])

    async def test_full_and_default_keep_hover_help_and_original_fields(self):
        for preset in ('full','default'):
            client=ContractReply(details()); tools=GameTools(client)
            result=await tools.inspect_rewards({'preset':preset,'reward_ids':None})
            self.assertNotIn('error',result)
            self.assertEqual(result['rewards']['items'][1]['hover_tips'],[{'title':'Help','description':'Visible help.'}])
            self.assertEqual('linked_group' in result['rewards']['items'][0],preset=='full')
            self.assertEqual(client.calls,[{'operation':'inspect_rewards','expected_state':None,'arguments':None}])
            self.assertEqual(tools.snapshot_id,'reward-1')

    async def test_filter_keeps_native_order_and_reports_missing_ids_together(self):
        for preset in ('full','default','summary'):
            for requested,want,missing in [(None,[12,14],[]),([],[],[]),([14],[14],[]),
                    ([14,12,14],[12,14],[]),([999,14,998,999],[14],[999,998])]:
                with self.subTest(preset=preset,requested=requested):
                    result=await GameTools(ContractReply(details())).inspect_rewards({'preset':preset,'reward_ids':requested})
                    self.assertNotIn('error',result)
                    self.assertEqual([r['id'] for r in result['rewards']['items']],want)
                    self.assertEqual(result['rewards']['title'],'Loot!')
                    self.assertEqual(result['rewards']['proceed'],{'text':'Skip','enabled':True,'skips_remaining':True})
                    self.assertEqual(result.get('errors',[]),[{'code':'reward_ids_not_found','reward_ids':missing}] if missing else [])
                    self.assertTrue(all(('hover_tips' in r)==(preset!='summary') for r in result['rewards']['items']))

    async def test_context_contradictions_are_rejected_before_refreshing_permission(self):
        for screen in [{'status':'covered','view':'map'},{'status':'hidden'},{'status':'not_ready'},
                       {'status':'visible','view':'deck'}]:
            for arguments in ({},{'preset':'summary'},{'reward_ids':[]}):
                with self.subTest(screen=screen,arguments=arguments):
                    raw=details();raw['screen']=screen
                    tools=GameTools(ContractReply(raw));tools.snapshot_id='previous'
                    result=await tools.inspect_rewards(arguments)
                    self.assertIn('error',result)
                    self.assertEqual(result['error']['code'],'transport_error')
                    self.assertIsNone(tools.snapshot_id)

    async def test_damaged_unselected_hover_help_is_still_validated(self):
        raw=details();raw['rewards']['items'][1]['hover_tips']=[{'title':'Missing description'}]
        for arguments in ({'preset':'summary'},{'reward_ids':[]},{'reward_ids':[12]}):
            tools=GameTools(ContractReply(raw));tools.snapshot_id='previous'
            result=await tools.inspect_rewards(arguments)
            self.assertEqual(result['error']['code'],'transport_error')
            self.assertIsNone(tools.snapshot_id)

    async def test_invalid_filter_arguments_preserve_existing_permission_without_ipc(self):
        for value in (False,[True],[-1],[2**31],['12'],{}):
            client=ContractReply(details());tools=GameTools(client);tools.snapshot_id='previous'
            result=await tools.inspect_rewards({'reward_ids':value})
            self.assertEqual(result['error']['code'],'invalid_request')
            self.assertEqual(tools.snapshot_id,'previous')
            self.assertEqual(client.calls,[])

    async def test_empty_pages_and_linked_groups_preserve_page_context(self):
        raw=details();raw['rewards']['items'][0]['linked_group']=77
        raw['rewards']['items'][1]['linked_group']=77
        selected=await GameTools(ContractReply(raw)).inspect_rewards({'preset':'summary','reward_ids':[14]})
        self.assertNotIn('error',selected)
        self.assertEqual(selected['rewards']['items'][0]['linked_group'],77)
        empty=copy.deepcopy(raw);empty['rewards'].update(title=None,items=[],proceed={'text':'Proceed','enabled':True,'skips_remaining':False})
        result=await GameTools(ContractReply(empty)).inspect_rewards({'preset':'summary','reward_ids':[12]})
        self.assertEqual(result['rewards'],{'status':'visible','items':[],'proceed':{'text':'Proceed','enabled':True,'skips_remaining':False}})
        self.assertEqual(result['errors'],[{'code':'reward_ids_not_found','reward_ids':[12]}])
