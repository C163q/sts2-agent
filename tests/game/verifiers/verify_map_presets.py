"""Check map output scopes against the native full graph through real stdio MCP."""
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


def check_subgraph(full, result, steps):
    nodes = {n['id']: n for n in full['nodes']}
    # Enumerate short native paths independently of the projection's breadth-first traversal.
    def walk(node, budget):
        return {node} | (set().union(*(walk(child, budget - 1) for child in nodes[node]['next'])) if budget else set())
    if full['current_node'] is not None:
        expected = walk(full['current_node'], steps)
    else:
        first_row = min(n['row'] for n in full['nodes'])
        expected = set().union(*(walk(n['id'], steps - 1) for n in full['nodes'] if n['row'] == first_row))
    assert [n['id'] for n in result['nodes']] == [n['id'] for n in full['nodes'] if n['id'] in expected], result
    assert result['max_steps'] == steps, result
    for node in result['nodes']:
        original = nodes[node['id']]
        assert node == {**original, 'next': [child for child in original['next'] if child in expected]}, node
    for field in ('scene', 'screen', 'act', 'current_node', 'visited_path', 'can_travel', 'selectable_nodes'):
        assert result[field] == full[field], (field, result, full)


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(args.report.parent / 'screenshots')}}))
    evidence = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert data == json.loads(response.content[0].text), response
                if error:
                    assert response.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not response.isError and 'error' not in data, data
                return data

            if args.scenario in {'entry', 'double'}:
                await call('inspect_rewards')
                receipt = await call('proceed')
                assert receipt['transition']['complete'], receipt
            if args.scenario == 'combat':
                await call('inspect_rewards')
                entry = await call('inspect_map')
                receipt = await call('travel_to_node', {'node_id': entry['selectable_nodes'][0]})
                assert receipt['scene'] == 'combat' and receipt['transition']['complete'], receipt
            full = await call('inspect_map')
            before = await asyncio.to_thread(raw.call, 'get_state')
            assert before['ok'], before
            assert before['state']['screen'] == {'status': 'visible', 'view': 'map'}, before
            summary = before['state']['map']
            assert summary['status'] == 'visible', before
            assert all(summary[key] == full[key] for key in ('act', 'current_node', 'can_travel', 'selectable_nodes')), before
            assert await call('inspect_map', {'preset': 'full', 'max_steps': 0}) == full
            for steps in (1, 2, 3):
                check_subgraph(full, await call('inspect_map', {'max_steps': steps}), steps)

            selected = await call('inspect_map', {'preset': 'selectable'})
            assert selected['can_travel'] == full['can_travel'], selected
            assert selected['selectable_nodes'] == full['selectable_nodes'], selected
            assert selected['nodes'] == [{k: v for k, v in n.items() if k != 'next'}
                                         for n in full['nodes'] if n['id'] in full['selectable_nodes']], selected
            assert 'visited_path' not in selected and selected['preset'] == 'selectable', selected
            assert await call('inspect_map', {'preset': 'selectable', 'max_steps': 1}) == selected
            await call('capture_screenshot', {'filename': 'native-map.png'})
            after = await asyncio.to_thread(raw.call, 'get_state')
            record({'before': before, 'after': after})
            assert after['ok'] and after['state']['snapshot_id'] == before['state']['snapshot_id'], after

            if args.scenario == 'combat':
                assert not selected['can_travel'] and selected['nodes'] == [], selected
                await call('close_map')
                receipt = await call('end_turn')
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
            else:
                assert selected['can_travel'] and selected['nodes'], selected
                if args.scenario == 'flight':
                    current = next(n for n in full['nodes'] if n['id'] == full['current_node'])
                    target = next(n['id'] for n in selected['nodes'] if n['id'] not in current['next'])
                    await call('inspect_map', {'max_steps': -1}, error='invalid_request')
                elif args.scenario == 'entry':
                    assert full['current_node'] is None and full['act'] == 2, full
                    assert selected['nodes'][0]['type'] == 'ancient', selected
                    target = selected['selectable_nodes'][0]
                else:
                    bosses = [n for n in full['nodes'] if n['type'] == 'boss']
                    assert len(bosses) == 2 and selected['nodes'][0]['type'] == 'boss', full
                    target = selected['selectable_nodes'][0]
                receipt = await call('travel_to_node', {'node_id': target})
                assert receipt['transition']['complete'], receipt
                assert receipt['scene'] == {'flight': 'rest_site', 'entry': 'ancient', 'double': 'combat'}[args.scenario], receipt
            assert not any(e.get('tool') == 'get_observation' for e in evidence)
    print('PASS map presets:', args.scenario, 'full parity, candidate priority, directed subgraphs and native continuation', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证地图预设、前瞻子图及无需额外观察的原生选路。')
    parser.add_argument('--scenario', choices=('flight', 'combat', 'entry', 'double'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
