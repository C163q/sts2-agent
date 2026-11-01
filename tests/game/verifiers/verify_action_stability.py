"""Audit returned action tokens across delayed native UI updates."""
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


CARDS = {
    'anger': 'Anger', 'turbo': 'TURBO', 'blade_dance': 'Blade Dance',
    'pommel_strike': 'Pommel Strike', 'bloodletting': 'Bloodletting', 'gather_light': 'Gather Light',
    'preview_draw': 'Defend', 'preview_messy': 'Defend',
}


def check_effect(scenario, before, after):
    player, previous = after['player'], before['player']
    if scenario in {'anger', 'turbo'}:
        assert player['discard_count'] == previous['discard_count'] + 2, after
    if scenario == 'turbo':
        assert player['energy'] == previous['energy'] + 2, after
    if scenario == 'blade_dance':
        assert sum(c['name'] == 'Shiv' for c in player['hand']) == 3, after
        assert player['exhaust_count'] == (previous['exhaust_count'] or 0) + 1, after
    if scenario == 'pommel_strike':
        assert player['draw_count'] == previous['draw_count'] - 1, after
        assert len(player['hand']) == len(previous['hand']), after
    if scenario == 'bloodletting':
        assert player['hp'] == after['top_bar']['hp'] == previous['hp'] - 3, after
        assert player['energy'] == previous['energy'] + 2, after
    if scenario == 'gather_light':
        assert player['block'] == previous['block'] + 8, after
        assert player['stars'] == (previous['stars'] or 0) + 1, after
    if scenario in {'preview_draw', 'preview_messy'}:
        assert player['draw_count'] == (7 if scenario == 'preview_messy' else 1), after


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
                                  '--ipc-dir', str(ipc_directory())])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                result = await session.call_tool(name, arguments or {})
                data = result.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert data == json.loads(result.content[0].text), result
                if error:
                    assert result.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not result.isError and 'error' not in data, data
                return data

            before = await call('get_observation')
            card = next(c for c in before['player']['hand'] if c['name'].casefold() == CARDS[args.scenario].casefold())
            strike = next(c for c in before['player']['hand'] if c['name'] == 'Strike')
            target = max(before['enemies'], key=lambda e: e['hp'])['id']
            arguments = {'card_id': card['id']}
            if args.scenario in {'anger', 'pommel_strike'}:
                arguments['target_id'] = target
            receipt = await call('play_card', arguments)
            assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
            returned = completed_action_state(raw.directory, receipt)
            record({'returned_state': returned})

            # Raw diagnostics never refresh the MCP connection's saved action permission.
            samples = []
            started = time.monotonic()
            for delay in (0, .25, .75, 1.5, 3.5):
                await asyncio.sleep(max(0, started + delay - time.monotonic()))
                response = await asyncio.to_thread(raw.call, 'get_state')
                assert response['ok'], response
                samples.append(response['state'])
                record({'sample_seconds': time.monotonic() - started, 'state': response['state']})

            # The continuation must work after the entire preview/fly window, without retry.
            following = await call('play_card', {'card_id': strike['id'], 'target_id': target})
            assert following['transition']['complete'] and following['transition']['stop_reason'] == 'player_ready', following
            assert all(s['snapshot_id'] == returned['snapshot_id'] for s in samples), 'Returned action token changed without input.'
            check_effect(args.scenario, before, returned)
            assert sum(e.get('tool') == 'get_observation' for e in evidence) == 1

            # A real external action must still invalidate the connection's saved token.
            current = await asyncio.to_thread(raw.call, 'get_state')
            external = await asyncio.to_thread(raw.call, 'end_turn', current['state']['snapshot_id'])
            record({'external_action': external})
            assert external['ok'], external
            await call('end_turn', error='stale_state')
            await call('end_turn', error='observation_required')
    print('PASS', args.scenario, 'returned token remains stable; chained input and stale-state protection verified', flush=True)


def main():
    parser = argparse.ArgumentParser(description='跨过预览及飞牌窗口核对动作令牌稳定与连续操作。')
    parser.add_argument('--scenario', choices=tuple(CARDS), default='anger')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
