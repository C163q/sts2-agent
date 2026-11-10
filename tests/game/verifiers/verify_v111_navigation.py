"""Verify combat victory receipts can continue through native reward transitions."""
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
    assert (await asyncio.to_thread(ensure_run, raw))['ok']
    rows = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        rows.append(row)
        args.report.write_text(json.dumps(rows, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, *, error=None, **arguments):
                before = set((raw.directory / 'responses').glob('*.json'))
                reply = await session.call_tool(tool, {'preset': 'full', **arguments})
                result = reply.structuredContent
                paths = set((raw.directory / 'responses').glob('*.json')) - before
                packet = json.loads(paths.pop().read_text()) if len(paths) == 1 else None
                record({'tool': tool, 'arguments': arguments, 'result': result, 'native': packet})
                assert reply.isError == bool(error) and result == json.loads(reply.content[0].text), result
                assert result.get('error', {}).get('code') == error, result
                if 'transition' in result:
                    assert result['transition']['complete'], result
                return result, packet

            await call('get_observation')
            won, packet = await call('end_turn')
            assert won['transition']['stop_reason'] == 'combat_won', won
            assert any(e['type'] == 'died' and e.get('source', {}).get('name') == 'Doom'
                       for e in won['transition']['events']), won
            assert won['scene'] == 'rewards' and 'inspect_rewards' in won['available_actions'], won
            assert packet['state']['rewards']['status'] == 'visible', packet
            token = packet['state']['snapshot_id']
            # Victory revokes action permission; raw diagnostics do not grant it.
            for _ in range(12):
                sample = await asyncio.to_thread(raw.call, 'get_state')
                record({'sample': sample})
                assert sample['ok'] and sample['state']['snapshot_id'] == token, sample
                await asyncio.sleep(.15)
            await call('proceed', error='observation_required')
            rewards, _ = await call('inspect_rewards')
            assert rewards['rewards']['status'] == 'visible', rewards
            result, _ = await call('proceed')
            assert result['screen']['view'] == 'map', result
            graph, _ = await call('inspect_map')
            assert graph['selectable_nodes'], graph
            traveled, _ = await call('travel_to_node', node_id=graph['selectable_nodes'][0])
            assert traveled['transition']['stop_reason'] in {'action_completed', 'player_ready', 'choice_required'}, traveled
    print('PASS v0.111 Doom victory -> rewards -> map -> next room', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
