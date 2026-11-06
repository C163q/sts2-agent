"""Check same-snapshot details and media failures in an isolated graphical run."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from sts2_mcp.mcp_server import SERVER_VERSION
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory(), timeout=90)
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, token=None, arguments=None, response_options=None):
        value = await asyncio.to_thread(raw.call, operation, token, arguments=arguments, response_options=response_options)
        record({'native': operation, 'response_options': response_options, 'result': value})
        return value

    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(args.report.parent/'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            assert (await session.initialize()).serverInfo.version == SERVER_VERSION

            async def call(tool, arguments=None, error=None):
                options = arguments or {}
                if tool != 'capture_screenshot': options = {'preset': 'full', **options}
                reply = await session.call_tool(tool, options)
                data = reply.structuredContent
                record({'tool': tool, 'arguments': options, 'result': data,
                        'images': sum(item.type == 'image' for item in reply.content)})
                assert data == json.loads(reply.content[0].text)
                assert not {'snapshot_id', 'schema_version', 'execution', 'response_options'} & data.keys(), data
                if error: assert reply.isError and data['error']['code'] == error, data
                else: assert not reply.isError, data
                return data

            async def contexts(label):
                state = await call('get_observation')
                reference = {key: state[key] for key in ('scene', 'screen')}
                for tool in ('inspect_hand', 'inspect_potions', 'inspect_relics', 'inspect_targets'):
                    if tool not in state['available_actions']: continue
                    arguments = None
                    if tool == 'inspect_targets':
                        if not (state.get('player') or {}).get('hand'): continue
                        arguments = {'card_id': state['player']['hand'][0]['id']}
                    data = await call(tool, arguments)
                    assert {key: data[key] for key in reference} == reference, (label, tool, data, reference)
                return state

            state = await call('get_observation')
            if args.scenario in {'event_selection', 'divination'}:
                option = next(option for option in state['event']['options'] if option['enabled'])
                receipt = await call('choose_event_option', {'option_id': option['id']})
                assert receipt['transition']['complete'], receipt
            state = await contexts('initial')
            if args.scenario == 'event_selection':
                details = await call('inspect_selection')
                assert details['scene'] == state['scene'] == 'event'
                assert details['selection']['status'] == 'visible'

            await call('capture_screenshot', {'filename': 'initial.png'})
            if args.scenario == 'combat':
                for tool, arguments in [('inspect_map', None), ('inspect_deck', None), ('inspect_pile', {'pile': 'draw'})]:
                    state = await call('get_observation')
                    if tool not in state['available_actions']: continue
                    await call(tool, arguments)
                    covered = await contexts(tool)
                    if covered['screen'].get('view') in {'deck', 'draw_pile', 'discard_pile', 'exhaust_pile'}:
                        await call('close_card_view')
                    state = await call('get_observation')
                    if 'close_map' in state['available_actions']: await call('close_map')
            if args.scenario == 'divination':
                assert state['divination']['status'] == 'visible', state
                rows = state['divination']['grid']['cell_rows']
                y = next(index for index, row in enumerate(rows) if '#' in row); x = rows[y].index('#')
                default = await native('get_state'); no_image = await native('get_state', response_options={'include_divination_image': False})
                assert default['ok'] and no_image['ok']
                assert 'divination_image' in default['state'] and 'divination_image' not in no_image['state']
                assert default['state']['snapshot_id'] == no_image['state']['snapshot_id']
                try:
                    assert (await native('set_test_capture_failure', arguments={'enabled': True}))['ok']
                    await call('inspect_event', {'include_image': True}, error='screenshot_unavailable')
                    await call('get_observation')
                    await call('get_observation', {'preset': 'actions_only'})
                    await call('get_observation', {'preset': 'top_bar'})
                    chosen = 'small' if state['divination']['tool'] == 'big' else 'big'
                    await call('set_divination_tool', {'tool': chosen})
                    before = (await native('get_state', response_options={'include_divination_image': False}))['state']
                    switched = 'small' if chosen == 'big' else 'big'
                    failed = await native('set_divination_tool', before['snapshot_id'], {'tool': switched})
                    assert not failed['ok'] and failed['error']['code'] == 'screenshot_unavailable', failed
                    assert failed['execution']['ui_interaction_started'] and failed['execution']['state_captured'], failed
                    after = (await native('get_state', response_options={'include_divination_image': False}))['state']
                    assert after['divination']['tool'] == switched and before['snapshot_id'] != after['snapshot_id']
                    await call('get_observation', {'preset': 'actions_only'})
                    receipt = await call('divine', {'x': x, 'y': y})
                    assert receipt['transition']['complete'] and 'divination' not in receipt, receipt
                finally:
                    await native('set_test_capture_failure', arguments={'enabled': False})
                await call('get_observation')
                await call('capture_screenshot', {'filename': 'after-media-recovery.png'})
    print('PASS native responses', args.scenario, len(evidence), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('combat', 'context', 'divination', 'event_selection'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
