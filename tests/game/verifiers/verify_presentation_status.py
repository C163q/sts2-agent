"""Verify body display progress independently of disabled controls."""
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
    raw = Client(ipc_directory(), timeout=120)
    assert (await asyncio.to_thread(ensure_run, raw))['ok']
    rows = []
    def record(row):
        rows.append(row); args.report.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()
        async def call(tool, arguments=None, label=None):
            supplied = {'preset': 'full', **(arguments or {})}
            previous = set((raw.directory/'responses').glob('*.json'))
            reply = await session.call_tool(tool, supplied); data = reply.structuredContent
            files = set((raw.directory/'responses').glob('*.json')) - previous
            record({'tool':tool, 'arguments':supplied, 'label':label, 'result':data,
                    'native_files':[str(p.relative_to(ROOT)) for p in sorted(files)]})
            assert data == json.loads(reply.content[0].text), reply
            assert not reply.isError, data
            return data
        async def native(operation, arguments=None):
            value = await asyncio.to_thread(raw.call, operation, arguments=arguments,
                                           response_options={'include_divination_image':False})
            record({'native_operation':operation, 'arguments':arguments, 'result':value})
            assert value['ok'], value
            return value['state']
        async def ready(action):
            deadline = time.monotonic()+25
            while True:
                value = await call('get_observation')
                if action in value['available_actions']: return value
                assert time.monotonic()<deadline, value
                await asyncio.sleep(.15)
        page = args.scenario
        if page in {'epilogue','run_result'}:
            await ready('proceed'); await call('proceed')
            if page == 'run_result':
                for _ in range(15):
                    state = await call('get_observation')
                    if state['scene']=='run_result': break
                    await call('advance_dialogue' if 'advance_dialogue' in state['available_actions'] else 'proceed')
                else: raise AssertionError('No result')
        actions = {'event':'choose_event_option','ancient':'advance_dialogue','rewards':'claim_reward',
                   'rest_site':'choose_rest_option','shop':'open_shop','treasure':'loot_treasure',
                   'divination':'divine','epilogue':'advance_dialogue','run_result':'run_result_option'}
        if page == 'divination':
            event = await ready('choose_event_option')
            option = next(item for item in event['event']['options'] if item['enabled'])
            await call('choose_event_option', {'option_id':option['id']})
        await ready(actions[page])
        if page=='shop': await call('open_shop')
        if page=='treasure': await call('loot_treasure', {'open_only':True})
        stable = await call('get_observation', label='stable')
        assert stable[page]['status']=='visible', stable
        for mode, expected in [('disabled','visible'), ('partial','not_ready')]:
            assert (await native('set_test_presentation', {'mode':mode}))['mode']==mode
            try:
                for preset in ('full','default','summary'):
                    observed = await call('get_observation', {'preset':preset}, label=mode+'_'+preset)
                    assert observed[page]['status']==expected, observed
                    assert observed['screen']['status']=='visible', observed
                    if mode=='partial': assert page in observed['notes']['presentation']['sources'], observed
                    else: assert 'presentation' not in observed.get('notes',{}), observed
            finally: await native('set_test_presentation', {'mode':'normal'})
            restored = await call('get_observation', label='restored_'+mode)
            assert restored[page]['status']=='visible', restored
        if page == 'rewards': await call('proceed', label='finish_reward_fixture')
        print('PASS',page,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',required=True)
    parser.add_argument('--report',type=Path,required=True)
    asyncio.run(verify(parser.parse_args()))
