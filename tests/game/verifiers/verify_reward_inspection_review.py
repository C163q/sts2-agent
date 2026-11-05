"""Capture reward inspection content, stable identities and pure-read refusals."""
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

    async def native_state():
        reply = await asyncio.to_thread(raw.call, 'get_state')
        assert reply['ok'], reply
        return reply['state']

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT/'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                arguments = {'preset':'full', **(arguments or {})}
                files = set((raw.directory/'responses').glob('*.json'))
                reply = await session.call_tool(tool, arguments)
                result = reply.structuredContent
                row = {'tool':tool, 'arguments':arguments, 'result':result, 'label':label,
                    'image_count':sum(item.type == 'image' for item in reply.content)}
                if tool == 'inspect_rewards':
                    added = set((raw.directory/'responses').glob('*.json'))-files
                    if added:
                        assert len(added) == 1, added
                        native = json.loads(added.pop().read_text())
                        row.update(native_error=native.get('error'), execution=native.get('execution'))
                record(row)
                assert result == json.loads(reply.content[0].text), reply
                assert reply.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            if args.scenario == 'no_rewards':
                rejected = await call('inspect_rewards', error='illegal_action', label='no_initial_permission')
                assert rejected['error']['recovery'] == 'get_observation', rejected
                await call('end_turn', error='observation_required')
                await call('get_observation')
                rejected = await call('inspect_rewards', error='illegal_action', label='with_permission')
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('end_turn', label='direct_after_refusal')
                return

            before = await native_state()
            initial = await call('inspect_rewards', label='initial_full')
            assert initial['scene'] == 'rewards' and initial['screen'] == {'status':'visible'}, initial
            assert set(initial) == {'scene','screen','rewards'}, initial
            assert initial['rewards']['status'] == 'visible', initial
            repeated = await call('inspect_rewards', label='repeat_full')
            after = await native_state()
            assert repeated == initial and before['snapshot_id'] == after['snapshot_id'], (before, after)
            observed = await call('get_observation')
            rows = initial['rewards']['items']
            assert observed['rewards']['items'] == [{k:v for k,v in r.items() if k!='hover_tips'} for r in rows]
            assert all('hover_tips' in r and 'cards' not in r for r in rows), rows
            compact = await call('inspect_rewards', {'preset':'default'}, label='initial_default')
            assert [r['id'] for r in compact['rewards']['items']] == [r['id'] for r in rows]
            assert all('linked_group' not in r for r in compact['rewards']['items'] if next(v for v in rows if v['id']==r['id'])['linked_group'] is None)
            assert (await call('inspect_rewards', {'reward_ids':[]}, 'invalid_request', 'local_arguments'))['error']['recovery'] == 'correct_request'

            if args.scenario == 'basic':
                gold = next(r for r in rows if r['type']=='gold')
                await call('claim_reward', {'reward_id':gold['id']}, label='direct_after_local_error')
                remaining = await call('inspect_rewards', label='after_claim')
                assert [r['id'] for r in remaining['rewards']['items']] == [r['id'] for r in rows if r['id']!=gold['id']]
                card = next(r for r in rows if r['type']=='card')
                await call('claim_reward', {'reward_id':card['id']})
                selected = await call('inspect_selection')
                rejected = await call('inspect_rewards', error='illegal_action', label='selection_covered')
                assert rejected['error']['recovery']=='choose_legal_action', rejected
                skip = next(o for o in selected['selection']['options'] if o['id']=='skip')
                await call('selection_option', {'option_id':skip['id']}, label='direct_selection_after_refusal')
            elif args.scenario == 'linked':
                assert len(rows)==2 and rows[0]['linked_group']==rows[1]['linked_group'] is not None, rows
                assert all(r['hover_tips'] for r in rows), rows
                await call('claim_reward', {'reward_id':rows[0]['id']})
                assert not (await call('inspect_rewards', label='linked_claimed'))['rewards']['items']
            elif args.scenario == 'empty':
                assert rows==[] and initial['rewards']['proceed']['skips_remaining'] is False, initial
            elif args.scenario == 'nested':
                await call('claim_reward', {'reward_id':rows[0]['id']})
                nested = await call('inspect_rewards', label='nested_full')
                assert len(nested['rewards']['items'])==3, nested
                await call('proceed')
                assert not (await call('inspect_rewards', label='parent_restored'))['rewards']['items']
            elif args.scenario == 'returned':
                assert any(r['type']=='special_card' for r in rows), rows
            elif args.scenario == 'escaped':
                assert not any(r['type']=='special_card' for r in rows), rows

            # Leave through native travel so the fixture's parent reward task can finish.
            if args.scenario != 'basic':
                await call('proceed')
            graph = await call('inspect_map')
            rejected = await call('inspect_rewards', error='illegal_action', label='map_covered')
            assert rejected['error']['recovery']=='choose_legal_action', rejected
            assert graph['selectable_nodes'], graph
            await call('travel_to_node', {'node_id':graph['selectable_nodes'][0]}, label='direct_map_after_refusal')
    print('PASS reward inspection review:', args.scenario, flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('no_rewards','basic','linked','empty','nested','returned','escaped'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
