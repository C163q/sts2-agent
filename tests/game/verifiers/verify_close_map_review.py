"""Audit current map-close results and preflight recovery without changing behavior."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(tool, arguments=None, error=None, label=None):
                files = set((raw.directory/'responses').glob('*.json'))
                arguments = {'preset':'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                entry = {'tool':tool, 'arguments':arguments, 'label':label, 'result':result,
                    'image_count':sum(item.type == 'image' for item in response.content)}
                if tool == 'close_map':
                    added = set((raw.directory/'responses').glob('*.json'))-files
                    if added:
                        assert len(added) == 1, added
                        native = json.loads(added.pop().read_text())
                        state = native.get('state', {})
                        entry.update(native_error=native.get('error'), execution=native.get('execution'),
                            native_state_keys=sorted(state), native_selection={k:v for k,v in (state.get('selection') or {}).items() if k in {'type','status'}})
                record(entry)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result
            async def reject(label):
                result = await call('close_map', error='illegal_action', label=label)
                assert result['error']['message'] == 'The requested action is unavailable.', result
                assert result['error']['recovery'] == 'get_observation', result
                return result

            if args.scenario == 'no_map':
                await reject('no_initial_permission')
                await call('end_turn', error='observation_required')
                await call('get_observation')
                await call('close_map', {'force':True}, error='invalid_request', label='local_argument_error')
                await call('end_turn')
                await reject('closed_map_with_permission')
                await call('end_turn', error='observation_required', label='lost_permission')
                return
            state = await call('get_observation')
            if args.scenario in {'combat', 'entry'}:
                await call('proceed')
                state = await call('get_observation')
                if args.scenario == 'entry':
                    assert state['scene'] == 'map' and state['map']['act'] == 2, state
                    target = state['map']['selectable_nodes'][0]
                    await reject('mandatory_act_entry')
                    await call('travel_to_node', {'node_id':target}, error='observation_required', label='lost_permission')
                    await call('inspect_map')
                    await call('travel_to_node', {'node_id':target})
                    return
                target = state['map']['selectable_nodes'][0]
                await call('travel_to_node', {'node_id':target})
                state = await call('get_observation')
                assert state['scene'] == 'combat', state
            if args.scenario == 'selection':
                await call('inspect_selection')
                await call('set_selection_view', {'view':'battlefield'})
                await call('inspect_map')
                await call('inspect_deck')
                await reject('covered_by_deck')
                await call('close_card_view')
                closed = await call('close_map', label='selection_restored')
                observed = await call('get_observation')
                assert observed['selection']['status'] == 'battlefield', observed
                assert 'selection' not in closed and 'selection' in closed.get('notes', {}), closed
                await call('set_selection_view', {'view':'selection'})
                selection = await call('inspect_selection')
                await call('select_card', {'card_id':selection['selection']['cards'][0]['id']})
                return
            if args.scenario == 'divination':
                option = next(o for o in state['event']['options'] if o['enabled'])
                await call('choose_event_option', {'option_id':option['id']})
                state = await call('get_observation')
                assert state['divination']['status'] == 'visible', state
            await call('inspect_map')
            closed = await call('close_map', label='closed_full')
            observed = await call('get_observation')
            assert closed['scene'] == observed['scene'] and closed['screen'] == observed['screen']
            assert 'transition' not in closed, closed
            if args.scenario == 'event':
                assert observed['event']['status'] == 'visible' and 'event' not in closed, closed
            elif args.scenario == 'divination':
                assert closed['divination']['status'] == 'visible', closed
                assert evidence[-2]['image_count'] == 1, evidence[-2]
            elif args.scenario == 'combat':
                assert 'player' in closed and 'enemies' in closed, closed
                await call('inspect_map')
                await call('close_map', {'preset':'default'}, label='closed_default')
                await call('end_turn', label='direct_legal_continuation')
    print('PASS close_map audit:', args.scenario, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',choices=('no_map','combat','event','selection','entry','divination'),required=True)
    parser.add_argument('--report',type=Path,required=True)
    asyncio.run(verify(parser.parse_args()))
