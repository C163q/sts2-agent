"""Verify compact map-close results, full decoding and explicit preflight recovery."""
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
    if args.scenario == 'legacy':
        from tests.game.verifiers.verify_mcp_map import verify as verify_legacy
        await verify_legacy(argparse.Namespace(ipc_dir=raw.directory, output_dir=args.report.parent))
        args.report.write_text((args.report.parent/'mcp-map-evidence.json').read_text())
        return
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
                if tool == 'close_map' and not error:
                    keys = {'scene','screen','available_actions'} | ({'selection'} if entry.get('native_selection') else set())
                    assert set(result) == keys and entry['image_count'] == 0, entry
                    assert 'player' in entry['native_state_keys'], entry
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result
            async def reject(label, message, recovery="choose_legal_action"):
                result = await call('close_map', error='illegal_action', label=label)
                assert message in result['error']['message'], result
                assert result['error']['recovery'] == recovery, result
                return result

            if args.scenario == 'no_map':
                await reject('no_initial_permission', 'No map is open', 'get_observation')
                await call('end_turn', error='observation_required')
                await call('get_observation')
                await call('close_map', {'force':True}, error='invalid_request', label='local_argument_error')
                await call('end_turn')
                await reject('closed_map_with_permission', 'No map is open')
                await call('end_turn', label='retained_permission')
                return
            state = await call('get_observation')
            if args.scenario in {'combat', 'entry'}:
                await call('proceed')
                state = await call('get_observation')
                if args.scenario == 'entry':
                    assert state['scene'] == 'map' and state['map']['act'] == 2, state
                    target = state['map']['selectable_nodes'][0]
                    await reject('mandatory_act_entry', 'return button is disabled')
                    await call('travel_to_node', {'node_id':target})
                    return
                target = state['map']['selectable_nodes'][0]
                await call('travel_to_node', {'node_id':target})
                state = await call('get_observation')
                assert state['scene'] == 'combat', state
            if args.scenario == 'selection':
                original = await call('inspect_selection')
                card_id = original['selection']['cards'][0]['id']
                await call('set_selection_view', {'view':'battlefield'})
                await call('inspect_map')
                await call('inspect_deck')
                await reject('covered_by_deck', 'close_card_view')
                await call('select_card', {'card_id':card_id}, error='illegal_action', label='retained_while_covered')
                await call('close_card_view')
                closed = await call('close_map', label='selection_restored')
                observed = await call('get_observation')
                assert observed['selection']['status'] == 'battlefield', observed
                assert closed['selection'] == {'type':observed['selection']['type'], 'status':'battlefield'}, closed
                await call('select_card', {'card_id':card_id}, error='illegal_action', label='close_refreshed_permission')
                await call('set_selection_view', {'view':'selection'})
                await call('select_card', {'card_id':card_id}, label='direct_selection_continuation')
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
                assert observed['divination']['status'] == 'visible' and 'divination' not in closed, closed
                assert evidence[-2]['image_count'] == 0, evidence[-2]
            elif args.scenario == 'combat':
                assert 'player' not in closed and 'enemies' not in closed, closed
                await call('inspect_map')
                await call('close_map', {'preset':'default'}, label='closed_default')
                await call('end_turn', label='direct_legal_continuation')
    print('PASS close_map results:', args.scenario, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',choices=('no_map','combat','event','selection','entry','divination','legacy'),required=True)
    parser.add_argument('--report',type=Path,required=True)
    asyncio.run(verify(parser.parse_args()))
