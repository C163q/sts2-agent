"""Verify native ancient choice recovery and visible acquisition feedback."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    report=args.report.resolve()
    if report.exists(): raise FileExistsError(report)
    report.parent.mkdir(parents=True,exist_ok=True)
    raw=Client(ipc_directory());created=await asyncio.to_thread(ensure_run,raw);assert created['ok'],created
    evidence=[]
    def record(row):
        evidence.append(row);report.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'scripts/mcp_server.py'),'--ipc-dir',str(raw.directory)])
    async with stdio_client(params)as(read,write):
      async with ClientSession(read,write)as session:
        await session.initialize()
        async def call(tool,arguments=None,*,error=None,label=None):
            supplied={'preset':'full',**(arguments or {})};previous=set((raw.directory/'responses').glob('*.json'))
            response=await session.call_tool(tool,supplied);data=response.structuredContent
            files=set((raw.directory/'responses').glob('*.json'))-previous
            row={'tool':tool,'arguments':supplied,'label':label,'result':data,'native_files':[str(p.relative_to(ROOT))for p in sorted(files)]}
            if files:
                assert len(files)==1,files
                original=json.loads(next(iter(files)).read_text());row.update(execution=original.get('execution'),native_error=original.get('error'))
            record(row)
            assert data==json.loads(response.content[0].text),response
            assert response.isError==bool(error)and data.get('error',{}).get('code')==error,data
            return data
        async def native(operation,token=None,arguments=None):
            result=await asyncio.to_thread(raw.call,operation,token,arguments=arguments,response_options={'include_divination_image':False})
            record({'native_operation':operation,'arguments':arguments,'result':result});return result
        async def ready():
            deadline=time.monotonic()+15
            while True:
                value=await call('inspect_ancient',label='ready')
                if any(o['enabled']for o in value['ancient']['options']):return value
                if(value['ancient']['continue']or{}).get('enabled'):await call('advance_dialogue')
                else:await asyncio.sleep(.15)
                assert time.monotonic()<deadline,value
        async def reject(option_id,label,hint):
            before=(await native('get_state'))['state']
            result=await call('choose_ancient_option',{'option_id':option_id},error='illegal_action',label=label)
            row=evidence[-1]
            assert hint in result['error']['message']and result['error']['recovery']=='choose_legal_action',result
            assert row['native_error']['action_submitted']is False,row
            assert row['execution']['ui_interaction_started']is False and row['execution']['action_submission_observed']is False,row
            after=(await native('get_state'))['state'];assert before['snapshot_id']==after['snapshot_id'],(before,after)
        await call('choose_ancient_option',{'option_id':0},error='observation_required',label='cold')
        mode=args.scenario
        if mode=='no_ancient':
            await call('get_observation');await reject(0,'wrong_room','ancient')
            await call('end_turn',label='direct_end_turn');return
        if mode=='dialogue':
            value=await call('inspect_ancient');assert(value['ancient']['continue']or{}).get('enabled'),value
            await reject(0,'dialogue_unfinished','advance_dialogue')
            await call('advance_dialogue',label='direct_advance');return
        value=await ready();option=value['ancient']['options'][0]
        if mode=='covered':
            for view,close in [('inspect_map','close_map'),('inspect_deck','close_card_view')]:
                await call(view);await reject(option['id'],view+'_covered',close);await call(close,label='direct_close')
            return
        if mode in {'hidden_inventory','hidden_top_bar'}:
            assert(await native('set_test_relic_display',arguments={'mode':mode}))['ok']
            try:
                await call('inspect_ancient',label='hidden_before')
                receipt=await call('choose_ancient_option',{'option_id':option['id']},label='hidden_acquisition')
                assert receipt['transition']['stop_reason']=='choice_required',receipt
                assert not any(e['type']=='relic_obtained'for e in receipt['transition']['events']),receipt
            finally:assert(await native('set_test_relic_display',arguments={'mode':'normal'}))['ok']
            await call('inspect_selection',label='restored_selection')
            restored=await call('selection_option',{'option_id':'bundle:0'},label='restored_preview')
            assert not any(e['type']=='relic_obtained'for e in restored['transition']['events']),restored
            return
        if mode in {'disabled','offscreen','hidden'}:
            configured=await native('set_test_ancient_display',arguments={'mode':mode});assert configured['ok'],configured
            try:
                value=await call('inspect_ancient')
                await reject(option['id'],mode+'_rejected','enabled'if mode=='disabled'else'inspect_ancient')
                available=next(o for o in value['ancient']['options']if o['enabled']and o['id']!=option['id'])
                await call('choose_ancient_option',{'option_id':available['id']},label='direct_other_choice')
            finally:assert(await native('set_test_ancient_display',arguments={'mode':'normal'}))['ok']
            return
        if mode=='stale':
            current=(await native('get_state'))['state']
            assert(await native('choose_ancient_option',current['snapshot_id'],{'option_id':option['id']}))['ok']
            await call('choose_ancient_option',{'option_id':option['id']},error='stale_state',label='stale')
            await call('proceed',error='observation_required',label='stale_requires_read')
            await call('inspect_ancient');await call('proceed');return
        if mode=='basic':
            await reject(2147483647,'missing_id','option_id')
            for invalid in ({},{'option_id':True},{'option_id':-1},{'option_id':2147483648},{'option_id':0,'extra':1}):
                await call('choose_ancient_option',invalid,error='invalid_request',label='local_invalid')
            current=(await native('get_state'))['state']
            invalid=await native('choose_ancient_option',current['snapshot_id'],{'option_id':True})
            assert invalid['error']['code']=='invalid_request'and invalid['error']['action_submitted']is False,invalid
        receipt=await call('choose_ancient_option',{'option_id':option['id'],**({'preset':'default'}if mode=='default'else{})},label='choose')
        assert receipt['transition']['complete'],receipt
        if mode in {'transform','bundle'}:
            assert receipt['transition']['stop_reason']=='choice_required',receipt
            if mode=='bundle':
                obtained=[e for e in receipt['transition']['events']if e['type']=='relic_obtained'and e['relic']['name']=='Scroll Boxes']
                assert len(obtained)==1,receipt
                assert not any(e['type']=='card_added'for e in receipt['transition']['events']),receipt
            current=(await native('get_state'))['state']
            await reject(option['id'],'selection_covered','inspect_selection')
            if mode=='transform':
                await call('select_card',{'card_id':current['selection']['cards'][0]['id']},label='direct_select_card')
            else:await call('selection_option',{'option_id':'bundle:0'},label='direct_bundle_preview')
            return
        if mode=='nested':
            assert receipt['scene']=='rewards',receipt
            await reject(option['id'],'rewards_covered','inspect_rewards');await call('proceed',label='direct_reward_proceed');return
        assert receipt['transition']['stop_reason']=='action_completed',receipt
        if mode=='touch':
            assert [(e['type'],e['relic']['name'])for e in receipt['transition']['events']]==[
                ('relic_obtained','Touch of Orobas'),('relic_removed','Burning Blood'),('relic_obtained','Black Blood')],receipt
        else:
            assert {'relic_obtained','max_hp_changed','hp_changed'}<={e['type']for e in receipt['transition']['events']},receipt
        await reject(option['id'],'finished','proceed');await call('proceed',label='direct_proceed')
    print('PASS',args.scenario,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description='验证先古馈赠选择拒绝恢复和可见事件。')
    parser.add_argument('--scenario',required=True)
    parser.add_argument('--report',type=Path,required=True)
    asyncio.run(verify(parser.parse_args()))
