"""Catch delayed relic counters invalidating completed turn receipts."""
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
from tests.game.support.verification_actions import completed_action_state
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                data = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': data})
                assert data == json.loads(response.content[0].text), response
                if error:
                    assert response.isError and data['error']['code'] == error, data
                else:
                    assert not response.isError, data
                return data

            await call('get_observation')
            for turn in range(4):
                receipt = await call('end_turn')
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
                returned = completed_action_state(raw.directory, receipt)
                record({'turn': turn, 'returned_state': returned})
                counter = next(r['counter'] for r in returned['top_bar']['relics'] if r['name'] == 'Happy Flower')
                samples = []
                started = time.monotonic()
                for delay in (0, .3, .8, 1.6):
                    await asyncio.sleep(max(0, started + delay - time.monotonic()))
                    response = await asyncio.to_thread(raw.call, 'get_state')
                    assert response['ok'], response
                    samples.append(response['state'])
                    record({'turn': turn, 'delay': delay, 'sample': response['state']})
                # Raw diagnostics preserve the MCP session's original action permission.
                card = next(c for c in returned['player']['hand'] if c['name'] == 'Defend')
                await call('play_card', {'card_id': card['id']})
                assert counter == (0, 1, 2, 0)[turn], returned
                assert all(s['snapshot_id'] == returned['snapshot_id'] for s in samples), 'Turn token changed without input.'
                if turn in (0, 3):
                    changes = [e for e in receipt['transition']['events'] if e['type'] == 'relic_counter_changed'
                               and e['relic']['name'] == 'Happy Flower']
                    assert changes[-1]['before'] == 3 and changes[-1]['after'] == 0, changes

            # Genuine external input must still reject the old permission.
            current = await asyncio.to_thread(raw.call, 'get_state')
            external = await asyncio.to_thread(raw.call, 'end_turn', current['state']['snapshot_id'])
            record({'external_action': external})
            assert external['ok'], external
            await call('end_turn', error='stale_state')
            await call('end_turn', error='observation_required')
    print('PASS Happy Flower: two activations, stable turn tokens, direct continuation and stale-state protection', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
