"""Verify grouped maps and preflight recovery through the real MCP process."""
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


def grouped(nodes):
    groups = {}
    for node in nodes:
        groups.setdefault(node['type'], []).append(node['id'])
    return groups


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(tool, arguments=None, error=None):
                arguments = {'preset':'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                data = response.structuredContent
                record({'tool':tool, 'arguments':arguments, 'result':data})
                assert data == json.loads(response.content[0].text), response
                assert response.isError == bool(error), data
                assert data.get('error', {}).get('code') == error, data
                return data
            if args.scenario == 'act_entry':
                await call('inspect_rewards')
                receipt = await call('proceed')
                returned = time.monotonic()
                # No other game request between proceed and the first public observation.
                immediate = await call('get_observation')
                record({'timing':'immediate', 'seconds_after_proceed':time.monotonic()-returned,
                    'scene':immediate['scene'], 'screen':immediate['screen']})
                assert receipt['transition']['complete'] and receipt['scene'] == 'map', receipt
                assert immediate['scene'] == 'map', immediate
                assert immediate['map']['act'] == 2 and immediate['map']['can_travel'], immediate
                for delay in (.25, 1.0):
                    await asyncio.sleep(delay)
                    observed = await call('get_observation')
                    record({'timing':'delayed', 'seconds_after_proceed':time.monotonic()-returned,
                        'scene':observed['scene'], 'screen':observed['screen']})
                    assert observed['scene'] == immediate['scene'], observed
                    assert observed['map'] == immediate['map'], observed
                await call('inspect_map', {'preset':'summary', 'max_steps':1})
                for tool in ('inspect_ui', 'inspect_potions', 'inspect_relics', 'inspect_map'):
                    details = await call(tool)
                    assert details['scene'] == 'map', details
                deck = await call('inspect_deck')
                assert deck['scene'] == 'map' and deck['screen']['view'] == 'deck', deck
                closed = await call('close_card_view')
                assert closed['scene'] == 'map' and closed['screen']['view'] == 'map', closed
                # Confirm the map is already actionable; entering its offered ancient resolves a room scene.
                await call('travel_to_node', {'node_id':immediate['map']['selectable_nodes'][0]})
                entered = await call('get_observation')
                assert entered['scene'] == 'ancient', entered
                print('PASS act entry investigation:', immediate['scene'], flush=True)
                return
            if args.scenario == 'selection':
                rejected = await call('inspect_map', error='illegal_action')
                assert 'card selection' in rejected['error']['message'], rejected
                assert rejected['error']['recovery'] == 'get_observation', rejected
                candidates = await call('inspect_selection')
                assert 'inspect_map' not in (await call('get_observation'))['available_actions']
                rejected = await call('inspect_map', error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                # Native preflight rejection must permit a legal selection without a new read.
                await call('select_card', {'card_id': candidates['selection']['cards'][0]['id']})
                return
            full = await call('inspect_map')
            summary = await call('inspect_map', {'preset':'summary'})
            assert summary['nodes_by_type'] == grouped(full['nodes']), summary
            assert not {'nodes', 'visited_path', 'next', 'node_details'} & summary.keys(), summary
            for depth in (1, 2):
                limited = await call('inspect_map', {'max_steps':depth})
                compact = await call('inspect_map', {'preset':'summary', 'max_steps':depth})
                assert compact['nodes_by_type'] == grouped(limited['nodes']), compact
                assert compact['selectable_nodes'] == full['selectable_nodes'], compact
            for preset in ('full', 'default', 'summary'):
                observed = await call('get_observation', {'preset':preset})
                assert observed['map']['nodes_by_type'] == summary['nodes_by_type'], observed
                assert observed['notes']['map'] == 'Map connections omitted; use inspect_map for details.', observed
                assert not {'nodes', 'visited_path'} & observed['map'].keys(), observed
            for preset in ('actions_only', 'top_bar'):
                observed = await call('get_observation', {'preset':preset})
                assert 'map' not in observed and 'map' not in observed.get('notes', {}), observed
            # Covering the map must remove its body and the associated note.
            await call('inspect_deck')
            covered = await call('get_observation')
            assert covered['map'] is None and 'map' not in covered.get('notes', {}), covered
            await call('close_card_view')
            restored = await call('get_observation')
            assert restored['map']['nodes_by_type'] == summary['nodes_by_type'], restored
            # A limited detail read must not constrain a subsequent basic observation.
            await call('inspect_map', {'preset':'summary', 'max_steps':1})
            observed = await call('get_observation')
            assert observed['map']['nodes_by_type'] == summary['nodes_by_type'], observed
            await call('close_map')
            closed = await call('get_observation')
            assert closed['map'] is None and 'map' not in closed.get('notes', {}), closed
            # Finish the reward fixture's pending native task before suite reset.
            if closed['scene'] == 'rewards' and 'proceed' in closed['available_actions']:
                await call('proceed')
                if full['selectable_nodes']:
                    await call('travel_to_node', {'node_id': full['selectable_nodes'][0]})
    print('PASS grouped maps:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('map', 'selection', 'act_entry'), default='map')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
