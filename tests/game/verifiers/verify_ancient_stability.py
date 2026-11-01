"""Keep ancient inspection permission across the native arrival animation."""
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


def differences(before, after, path=''):
    if isinstance(before, dict) and isinstance(after, dict):
        return [change for key in sorted(before.keys() | after.keys())
                for change in differences(before.get(key), after.get(key), f'{path}/{key}')]
    return [] if before == after else [{'path': path, 'before': before, 'after': after}]


async def verify(args):
    root = ROOT
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(root / 'scripts/mcp_server.py'),
                                  '--ipc-dir', str(raw.directory)])
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

            arrival = None
            if args.scenario in {'travel', 'travel_action'}:
                await call('inspect_rewards')
                result = await call('proceed')
                assert result['transition']['complete'], result
                graph = await call('inspect_map')
                assert graph['act'] == 2 and graph['can_travel'], graph
                result = await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]})
                assert result['scene'] == 'ancient' and result['transition']['complete'], result
                arrival = completed_action_state(raw.directory, result)
                record({'arrival_state': arrival})
            details = arrival if args.scenario == 'travel_action' else await call('inspect_ancient')
            assert details['ancient']['name'] == 'Pael', details
            # Receipt-only continuation uses native evidence for the fixture's option ID.
            option = next(o for o in details['ancient']['options'] if o['title'] == "Pael's Blood")
            assert option['enabled'], details
            # The raw detail response retains the exact token saved by MCP.
            latest = max((raw.directory / 'responses').glob('*.json'), key=lambda p: p.stat().st_mtime_ns)
            inspected = arrival if args.scenario == 'travel_action' else json.loads(latest.read_text())['state']
            baseline = arrival or (await asyncio.to_thread(raw.call, 'get_state'))['state']
            record({'inspected_state': inspected})
            samples = []
            started = time.monotonic()
            for delay in (0, .5, 1.5, 3, 5, 7, 9):
                await asyncio.sleep(max(0, started + delay - time.monotonic()))
                response = await asyncio.to_thread(raw.call, 'get_state')
                assert response['ok'], response
                current = response['state']
                samples.append(current)
                record({'sample_seconds': time.monotonic() - started, 'state': current,
                        'changes': differences({k: v for k, v in baseline.items() if k != 'transition'}, current)})
            # Raw diagnostics never refresh this MCP connection's saved permission.
            result = await call('choose_ancient_option', {'option_id': option['id']})
            assert result['transition']['complete'], result
            assert all(s['snapshot_id'] == inspected['snapshot_id'] for s in samples), 'Arrival invalidated the inspection token.'
            if arrival:
                assert all(s['snapshot_id'] == arrival['snapshot_id'] for s in samples), 'Completed travel returned an unsettled ancient.'
            obtained = await call('inspect_relics')
            assert sum(r['name'] == "Pael's Blood" for r in obtained['relics']) == 1, obtained

            await call('inspect_ancient')
            current = await asyncio.to_thread(raw.call, 'get_state')
            external = await asyncio.to_thread(raw.call, 'proceed', current['state']['snapshot_id'])
            record({'external_action': external})
            assert external['ok'], external
            await call('choose_ancient_option', {'option_id': option['id']}, error='stale_state')
            await call('choose_ancient_option', {'option_id': option['id']}, error='observation_required')
            await call('inspect_map')
            await call('choose_ancient_option', {'option_id': option['id']}, error='illegal_action')
            await call('close_map')
            await call('choose_ancient_option', {'option_id': option['id']}, error='illegal_action')
            assert not any(e.get('tool') == 'get_observation' for e in evidence)
    print('PASS ancient inspection survives arrival without another observation', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证先古之民入场后的状态稳定和直接选择。')
    parser.add_argument('--scenario', choices=('direct', 'travel', 'travel_action'), default='direct')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
