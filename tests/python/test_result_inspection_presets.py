"""Validate current result snapshots before compacting or publishing permission."""
import copy
import unittest
from sts2_mcp.game_tools import GameTools
from tests.python.test_run_ending import state


def result():
    raw = state('summary')
    raw.update(schema_version=47, available_actions=['inspect_run_result','run_result_option'])
    raw['run_result'].update(
        badges=[{'name':'Hunter','rarity':'gold'}], discoveries=[{'kind':'cards','count':12}],
        cards=[{'id':'card:0','name':'Defend','type':'Skill','rarity':'basic','visual_card_pool':'ironclad',
                'energy_cost':'1','star_cost':None,'enchantment':None,'affliction':None,
                'description':'Gain 5 Block.','hover_tips':[{'title':'Block','description':'Prevents damage.'}]}],
        relics=[{'name':'Anchor','description':'Gain Block.','hover_tips':[]}],
        potions=[{'name':'Block Potion','description':'Gain 12 Block.','hover_tips':[]}],
        hover_tips=[{'source':'badge:0','title':'Hunter','description':'Defeated enemies.'},
                    {'source':'discovery:cards','title':'Cards','description':'Discovered 12 cards.'}],
        hover_sources=['badge:0','discovery:cards'], unavailable_hover_sources=[])
    return raw


class ResultPacket:
    def __init__(self): self.raw=result()
    def call(self, operation, expected_state=None, arguments=None, response_options=None):
        return {'ok':True, 'state':copy.deepcopy(self.raw)}


class ResultInspectionPresetTests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_keeps_titles_and_story_but_drops_effect_text(self):
        client=ResultPacket();tools=GameTools(client)
        value=await tools.inspect_run_result({'preset':'summary'})
        self.assertNotIn('error',value)
        body=value['run_result']
        self.assertEqual(body['hover_tips'],[{'source':'badge:0','title':'Hunter'},
                                             {'source':'discovery:cards','title':'Cards'}])
        self.assertEqual(body['cards'],[{'id':'card:0','name':'Defend','type':'Skill','energy_cost':'1'}])
        self.assertEqual(body['relics'],[{'name':'Anchor'}])
        self.assertEqual(body['potions'],[{'name':'Block Potion'}])
        self.assertEqual(body['texts'],['Your damage: 100'])
        self.assertEqual(body['score_lines'],[])
        self.assertNotIn('hover_sources',body)
        full=await tools.inspect_run_result({'preset':'full'})
        self.assertEqual(full['run_result']['cards'][0]['description'],'Gain 5 Block.')
        self.assertEqual(full['run_result']['hover_tips'][0]['description'],'Defeated enemies.')

    async def test_bad_context_or_missing_full_fields_clears_existing_permission_in_every_preset(self):
        mutations=[lambda r:r.update(screen={'status':'covered','view':'deck'}),
                   lambda r:r.update(screen={'status':'visible','view':'shop'}),
                   lambda r:r.update(screen={'status':'visible'}),
                   lambda r:r['run_result'].pop('hover_tips'),
                   lambda r:r['run_result']['hover_tips'][0].pop('description'),
                   lambda r:r['run_result']['cards'][0].pop('description'),
                   lambda r:r['run_result']['potions'][0].pop('description'),
                   lambda r:r['run_result']['badges'][0].pop('name'),
                   lambda r:r['run_result']['hover_tips'][0].update(source='badge:999'),
                   lambda r:r['run_result'].pop('hover_sources')]
        for preset in ('full','default','summary'):
            for mutate in mutations:
                with self.subTest(preset=preset,mutation=mutate):
                    client=ResultPacket();tools=GameTools(client)
                    await tools.get_observation();self.assertIsNotNone(tools.snapshot_id)
                    mutate(client.raw)
                    value=await tools.inspect_run_result({'preset':preset})
                    self.assertEqual(value.get('error',{}).get('code'),'transport_error',value)
                    self.assertIsNone(tools.snapshot_id)

    async def test_partial_read_and_complete_disabled_buttons_are_both_readable(self):
        for status in ('not_ready','visible'):
            client=ResultPacket();client.raw['run_result']['status']=status
            client.raw['available_actions']=['inspect_run_result']
            for option in client.raw['run_result']['options']:option['enabled']=False
            tools=GameTools(client)
            value=await tools.inspect_run_result()
            self.assertNotIn('error',value)
            self.assertEqual(value['run_result']['status'],status)
            self.assertIsNotNone(tools.snapshot_id)
            if status=='not_ready':self.assertIn('run_result',value['notes']['presentation']['sources'])

    async def test_basic_observation_uses_static_result_titles_and_card_faces(self):
        tools=GameTools(ResultPacket())
        for preset in ('full','default','summary'):
            body=(await tools.get_observation({'preset':preset}))['run_result']
            self.assertIn('hover_tips', body)
            self.assertEqual(body['hover_tips'][0],{'source':'badge:0','title':'Hunter'})
            self.assertNotIn('description',body['cards'][0])
            self.assertNotIn('hover_tips',body['cards'][0])
            self.assertEqual(body['relics'],[{'name':'Anchor'}])

    async def test_partial_result_observation_rejects_underlying_run_contents(self):
        client=ResultPacket();client.raw['run_result']['status']='not_ready'
        client.raw['available_actions']=['inspect_run_result']
        for option in client.raw['run_result']['options']:option['enabled']=False
        client.raw['turn']=1
        value=await GameTools(client).get_observation()
        self.assertEqual(value.get('error',{}).get('code'),'transport_error',value)

    async def test_epoch_tip_need_not_be_a_currently_clickable_option(self):
        client=ResultPacket();client.raw['run_result'].update(phase='timeline',cards=[],relics=[],potions=[],badges=[],discoveries=[],
            hover_tips=[{'source':'epoch:9','title':'Neow','description':'Already revealed.'}],
            hover_sources=['epoch:9'],options=[{'id':'back','text':'Back','enabled':True}])
        value=await GameTools(client).inspect_run_result({'preset':'summary'})
        self.assertNotIn('error',value)
        self.assertEqual(value['run_result']['hover_tips'],[{'source':'epoch:9','title':'Neow'}])
