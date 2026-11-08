"""Check native relic display, generated-card visibility and card-play sources."""
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

            async def call(tool, arguments=None):
                reply = await session.call_tool(tool, {'preset': 'full', **(arguments or {})})
                data = reply.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': data})
                assert data == json.loads(reply.content[0].text), reply
                assert not reply.isError, data
                return data

            before = await call('get_observation')
            target = max(before['enemies'], key=lambda e: e['hp'])['id']
            hand = before['player']['hand']
            if args.scenario == 'pen_nib':
                assert next(r['counter'] for r in before['top_bar']['relics'] if r['name'] == 'Pen Nib') == 9
                strike = next(c for c in hand if c['name'] == 'Strike')
                receipt = await call('play_card', {'card_id': strike['id'], 'target_id': target})
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
                returned = completed_action_state(raw.directory, receipt)
                record({'returned_state': returned})
                samples = []
                started = time.monotonic()
                for delay in (0, .3, .8, 1.6):
                    await asyncio.sleep(max(0, started + delay - time.monotonic()))
                    response = await asyncio.to_thread(raw.call, 'get_state')
                    assert response['ok'], response
                    samples.append(response['state'])
                    record({'delay': delay, 'sample': response['state']})
                defend = next(c for c in hand if c['name'] == 'Defend')
                await call('play_card', {'card_id': defend['id']})
                assert all(s['snapshot_id'] == returned['snapshot_id'] for s in samples), 'Pen Nib changed the returned token.'
                counters = [e for e in receipt['transition']['events'] if e['type'] == 'relic_counter_changed']
                assert [(e['before'], e['after']) for e in counters] == [(9, 0), (0, 10), (10, 0)], counters
                hits = [e for e in receipt['transition']['events'] if e['type'] == 'damage']
                assert len(hits) == 1 and hits[0]['hp_loss'] == 12, hits
            elif args.scenario == 'soul':
                reaves = [c for c in hand if c['name'] == 'Reave']
                fetches = [c for c in hand if c['name'] == 'Fetch']
                first = await call('play_card', {'card_id': reaves[0]['id'], 'target_id': target})
                added = [e for e in first['transition']['events'] if e['type'] == 'card_added']
                assert len(added) == 1 and added[0]['pile'] == 'draw', added
                await call('play_card', {'card_id': fetches[0]['id'], 'target_id': target})
                batch = await call('play_cards', {'cards': [
                    {'card_id': reaves[1]['id'], 'target_id': target},
                    {'card_id': fetches[1]['id'], 'target_id': target}]})
                added = [e for e in batch['transition']['events'] if e['type'] == 'card_added']
                drawn = [e for e in batch['transition']['events'] if e['type'] == 'card_drawn']
                assert len(added) == 1 and added[0]['pile'] is None, added
                assert any(e['card']['id'] == added[0]['card']['id'] for e in drawn), (added, drawn)
                state = await call('get_observation')
                assert any(c['id'] == added[0]['card']['id'] for c in state['player']['hand']), state
            else:
                cards = [c for c in hand if c['energy_cost'] == '1'][:2]
                assert len(cards) == 2, hand
                for card, preset in zip(cards, ('full', 'default')):
                    query = await call('inspect_targets', {'card_id': card['id']})
                    receipt = await call('play_card', {'card_id': card['id'], 'preset': preset,
                        **({'target_id': target} if query['requires_target'] else {})})
                    played = [e for e in receipt['transition']['events'] if e['type'] == 'card_played']
                    assert played and all('source' not in e for e in played), played
                receipt = await call('end_turn')
                automatic = [e for e in receipt['transition']['events'] if e['type'] == 'card_played' and e['autoplay']]
                assert automatic and all(e['source'] == {'kind': 'power', 'name': 'Hellraiser'} for e in automatic), automatic
    print('PASS necrobinder feedback:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('pen_nib', 'soul', 'manual_sources'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
