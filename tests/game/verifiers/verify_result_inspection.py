"""Inspect result phases, summaries, progress, hover boundaries and read recovery."""
from scripts._bootstrap import ROOT
import argparse, asyncio, json, sys, time
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    if args.report.exists(): raise FileExistsError(args.report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw=Client(ipc_directory(),timeout=120)
    assert (await asyncio.to_thread(ensure_run,raw))['ok']
    rows=[]
    def record(row):
        rows.append(row);args.report.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'scripts/mcp_server.py'),'--ipc-dir',str(raw.directory)])
    async with stdio_client(params)as(read,write):
      async with ClientSession(read,write)as session:
        await session.initialize()
        async def call(tool,arguments=None,*,label=None,error=None):
            supplied={'preset':'full',**(arguments or {})};previous=set((raw.directory/'responses').glob('*.json'))
            reply=await session.call_tool(tool,supplied);data=reply.structuredContent
            files=set((raw.directory/'responses').glob('*.json'))-previous
            row={'tool':tool,'arguments':supplied,'label':label,'result':data,'native_files':[str(p.relative_to(ROOT))for p in sorted(files)]}
            if files:
                assert len(files)==1;packet=json.loads(next(iter(files)).read_text())
                row.update(execution=packet.get('execution'),native_error=packet.get('error'))
            record(row);assert data==json.loads(reply.content[0].text),reply
            assert reply.isError==bool(error)and data.get('error',{}).get('code')==error,data
            return data
        async def native(operation='get_state',arguments=None):
            packet=await asyncio.to_thread(raw.call,operation,arguments=arguments,response_options={'include_divination_image':False})
            record({'native_operation':operation,'arguments':arguments,'result':packet});assert packet['ok'],packet
            return packet['state']
        async def observe(action=None):
            until=time.monotonic()+30
            while True:
                data=await call('get_observation')
                if action is None or action in data['available_actions']:return data
                assert time.monotonic()<until,data;await asyncio.sleep(.15)
        async def rejected(label):
            before=await native();value=await call('inspect_run_result',label=label,error='illegal_action')
            assert 'result'in value['error']['message'].lower(),value
            assert value['error']['recovery']=='choose_legal_action',value
            assert rows[-1]['execution']['ui_interaction_started']is False
            assert before['snapshot_id']==(await native())['snapshot_id']
        async def details(label):
            before=await native();full=await call('inspect_run_result',label=label+'_full')
            assert before['snapshot_id']==(await native())['snapshot_id'],label
            body=full['run_result'];assert body['status']=='visible',full
            assert 'hover_sources'not in body and 'unavailable_hover_sources'not in body
            summary=await call('inspect_run_result',{'preset':'summary'},label=label+'_summary')
            compact=summary['run_result']
            assert compact['texts']==body['texts']and compact['options']==body['options']
            assert compact['hover_tips']==[{key:tip[key]for key in('source','title')}for tip in body['hover_tips']]
            for card in compact['cards']:assert 'description'not in card and 'hover_tips'not in card,card
            for kind in('relics','potions'):assert compact[kind]==[{'name':item['name']}for item in body[kind]]
            for card in body['cards']:assert card.get('description'),card
            for preset in('full','default','summary'):
                basic=await call('get_observation',{'preset':preset},label=label+'_observation_'+preset)
                actual=basic['run_result']
                assert actual['texts']==body['texts']and actual['hover_tips']==compact['hover_tips']
                for card in actual['cards']:assert 'description'not in card and 'hover_tips'not in card
                assert actual['relics']==compact['relics']and actual['potions']==compact['potions']
            return full
        async def progress(label):
            for mode,status in(('disabled','visible'),('partial','not_ready')):
                await native('set_test_presentation',{'mode':mode})
                try:
                    observed=await call('get_observation',label=label+'_'+mode+'_observation')
                    assert observed['run_result']['status']==status,observed
                    assert 'inspect_run_result'in observed['available_actions'],observed
                    for preset in('full','default','summary'):
                        data=await call('inspect_run_result',{'preset':preset},label=label+'_'+mode+'_'+preset)
                        assert data['run_result']['status']==status,data
                        if mode=='partial':
                            assert 'run_result'in data['notes']['presentation']['sources'],data
                            assert data['run_result']['hover_tips']==[],data
                        else:assert 'run_result_option'not in observed['available_actions'],observed
                finally:await native('set_test_presentation',{'mode':'normal'})
                restored=await call('inspect_run_result',label=label+'_restored_'+mode)
                assert restored['run_result']['status']=='visible',restored
                deadline=time.monotonic()+15
                while not any(option['enabled'] for option in restored['run_result']['options']):
                    assert time.monotonic()<deadline,restored
                    await asyncio.sleep(.15)
                    restored=await call('inspect_run_result',label=label+'_action_ready_'+mode)
        if args.scenario=='wrong_room':
            await call('inspect_run_result',error='illegal_action',label='cold_wrong_room')
            await call('end_turn',error='observation_required',label='cold_no_permission')
            await observe('end_turn');await rejected('wrong_room');await call('end_turn',label='direct_end_turn')
            for arguments in({'extra':True},{'preset':'selectable'}):await call('inspect_run_result',arguments,error='invalid_request',label='bad_arguments')
            await call('end_turn',label='direct_after_bad_arguments');return
        if args.scenario in{'victory_unlock','history'}:
            await observe('proceed');await call('proceed')
            for _ in range(15):
                current=await observe()
                if current['scene']=='run_result':break
                await call('advance_dialogue'if'advance_dialogue'in current['available_actions']else'proceed')
            else:raise AssertionError('No result')
        await details('outcome');await progress('outcome')
        if args.scenario=='history':
            await native('prepare_test_browsable_result');await call('inspect_run_result')
        await call('run_result_option',{'option_id':'continue'},label='direct_continue')
        value=await details('summary');await progress('summary')
        if args.scenario=='history':
            await native('prepare_test_browsable_history');await details('history');await native('check_test_browsable_content');return
        await call('run_result_option',{'option_id':'main_menu'})
        seen=set()
        for index in range(40):
            current=await observe()
            if current['scene']=='main_menu':break
            assert current['scene']=='run_result',current
            phase=current['run_result']['phase'];seen.add(phase)
            value=await details(phase+'_'+str(index))
            if phase=='unlock'and value['run_result']['cards']:
                await progress('cards_'+str(index))
            options=[o for o in value['run_result']['options']if o['enabled']];assert options,value
            selected=next((o for o in options if o['id']in{'continue','confirm','back'}),
                          next((o for o in options if o['text']=='Reveal'),options[0]))
            await call('run_result_option',{'option_id':selected['id']},label='direct_'+phase)
        else:raise AssertionError('Unlock flow did not finish')
        await rejected('menu_without_result')
        await native('reopen_test_timeline');await rejected('unowned_timeline');await native('close_test_timeline')
        record({'seen_phases':sorted(seen)})
    print('PASS',args.scenario,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',choices=('wrong_room','death','victory_unlock','history'),required=True)
    parser.add_argument('--report',type=Path,required=True)
    asyncio.run(verify(parser.parse_args()))
