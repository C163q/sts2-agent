"""Capture native map travel boundaries and the current rejection contract."""
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

    async def native(operation, arguments=None, token=None, error=None):
        response = await asyncio.to_thread(raw.call, operation, token, arguments=arguments)
        record({'native_test': operation, 'result': response})
        assert response['ok'] == (error is None), response
        if error is not None:
            assert response['error']['code'] == error, response
            return response
        return response['state']

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT/'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                files = set((raw.directory/'responses').glob('*.json'))
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                entry = {'tool': tool, 'arguments': arguments, 'label': label, 'result': result,
                         'image_count': sum(item.type == 'image' for item in response.content)}
                if tool == 'travel_to_node':
                    added = set((raw.directory/'responses').glob('*.json')) - files
                    if added:
                        assert len(added) == 1, added
                        reply = json.loads(added.pop().read_text())
                        entry.update(native_error=reply.get('error'), execution=reply.get('execution'))
                record(entry)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            await call('travel_to_node', {'node_id': 'map:1:2:0'}, 'observation_required', 'no_permission')
            await call('get_observation')
            if args.scenario in {'entry', 'double'}:
                await call('proceed')
            if args.scenario == 'basic':
                rejected = await call('travel_to_node', {'node_id': 'map:1:2:0'}, 'illegal_action', 'map_closed')
                assert 'inspect_map' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('proceed', label='direct_after_closed')
            graph = await call('inspect_map')
            before = await native('check_test_navigation')
            source = next((n for n in graph['nodes'] if n['id'] == graph['current_node']), None)
            if args.scenario == 'flight':
                target = next(i for i in graph['selectable_nodes'] if i not in source['next'])
            else:
                target = source['next'][0] if source else graph['selectable_nodes'][0]
            assert target in graph['selectable_nodes'], graph

            if args.scenario == 'basic':
                current = await native('get_state')
                invalid = await native('travel_to_node', {'node_id': True}, current['snapshot_id'], 'invalid_request')
                assert invalid['error']['action_submitted'] is False, invalid
                assert invalid['execution']['ui_interaction_started'] is False, invalid
                await call('travel_to_node', {'node_id': target, 'force': True}, 'invalid_request', 'extra_argument')
                # The native rejection proves local validation preserved the existing permission.
                rejected = await call('travel_to_node', {'node_id': graph['current_node']}, 'illegal_action', 'not_selectable')
                assert 'selectable_nodes' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('travel_to_node', {'node_id': graph['current_node']}, 'illegal_action', 'retained_after_candidate')
                await call('inspect_map')
                await call('inspect_deck')
                rejected = await call('travel_to_node', {'node_id': target}, 'illegal_action', 'covered')
                assert 'close_card_view' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('end_turn', error='illegal_action', label='retained_after_cover')
                await call('close_card_view')
                await native('set_test_navigation_drawing')
                await call('travel_to_node', {'node_id': target}, 'stale_state', 'drawing_changed')
                await call('get_observation')
                rejected = await call('travel_to_node', {'node_id': target}, 'illegal_action', 'drawing')
                assert 'drawing mode' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('travel_to_node', {'node_id': target}, 'illegal_action', 'retained_after_drawing')
                await native('clear_test_navigation_drawing')
                await call('inspect_map')
                await native('scroll_test_navigation')

            if args.scenario == 'scroll_failure':
                await native('scroll_test_navigation')
                prepared = await native('arm_test_navigation_scroll_failure')
                target = prepared['offscreen_nodes'][0]
                rejected = await call('travel_to_node', {'node_id': target}, 'illegal_action', 'after_scroll')
                assert 'map changed' in rejected['error']['message'] and rejected['error']['recovery'] == 'get_observation', rejected
                facts = evidence[-1]
                assert facts['execution']['ui_interaction_started'] is True, facts
                assert 'action_submitted' not in facts['native_error'], facts
                await call('travel_to_node', {'node_id': target}, 'observation_required', 'lost_after_scroll')
                await native('clear_test_navigation_scroll_failure')
                await call('inspect_map')

            receipt = await call('travel_to_node', {'node_id': target, **({'preset':'default'} if args.scenario == 'flight' else {})}, label='arrival')
            reason = 'choice_required' if args.scenario == 'choice' else (
                'player_ready' if args.scenario in {'combat', 'double', 'antler'} else 'action_completed')
            assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == reason, receipt
            assert set(receipt) <= {'scene', 'screen', 'available_actions', 'selection', 'transition', 'notes'}, receipt
            assert not {'player', 'map', 'top_bar'} & receipt.keys(), receipt
            if args.scenario == 'antler':
                added = [e for e in receipt['transition']['events'] if e['type'] == 'card_added']
                assert len(added) == 3, receipt
                assert all(e['card']['name'] == 'Dazed' and e['pile'] == 'draw' for e in added), added
                assert len({e['card']['id'] for e in added}) == 3, added
                assert all(set(e) == {'type', 'sequence', 'card', 'pile'} for e in added), added
            if args.scenario == 'combat':
                await call('end_turn', label='direct_continuation')
            elif args.scenario == 'choice':
                assert receipt['selection']['status'] == 'visible', receipt
                # Reading is needed for candidate IDs, rather than for permission renewal.
                selection = await call('inspect_selection')
                await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
                state = await call('get_observation')
                if state.get('selection'):
                    option = next(o for o in state['selection']['options'] if o['enabled'])
                    await call('selection_option', {'option_id': option['id']})
            elif args.scenario in {'basic', 'flight', 'scroll_failure'}:
                await call('choose_rest_option', {'option_id': 'HEAL'}, label='direct_continuation')
            after = await native('check_test_navigation')
            assert after['current_node'] == target and after['rewards'] is False, after
            if args.scenario in {'basic', 'flight'}:
                assert after['boots_used'] == (3 if args.scenario == 'flight' else before['boots_used']), after
            observed = await call('get_observation')
            expected = {'basic': 'rest_site', 'flight': 'rest_site', 'combat': 'combat', 'choice': 'combat',
                        'shop': 'shop', 'treasure': 'treasure', 'entry': 'ancient', 'double': 'combat', 'antler': 'combat', 'scroll_failure': 'rest_site'}
            assert observed['scene'] == expected.get(args.scenario, 'event'), observed
            assert observed['scene'] == receipt['scene'], (receipt, observed)
    print('PASS travel review:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('basic', 'flight', 'combat', 'choice', 'shop', 'treasure', 'unknown', 'entry', 'double', 'antler', 'scroll_failure'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
