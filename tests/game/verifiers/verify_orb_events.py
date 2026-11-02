"""Verify native orb events through real MCP and gated boundary checks."""
from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
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
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = reply.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert not reply.isError and 'error' not in data, data
                assert data == json.loads(reply.content[0].text), reply
                if 'transition' in data:
                    transition = data['transition']
                    assert transition['complete'] and transition['stop_reason'] == 'player_ready', data
                    events = transition['events']
                    assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), data
                return data

            state = await call('get_observation')
            if args.scenario == 'checks':
                checks = await asyncio.to_thread(raw.call, 'check_test_orb_events')
                record({'native_checks': checks})
                assert checks['ok'] and checks['state']['passed'], checks
                await call('get_observation')
                await call('end_turn')
            elif args.scenario == 'chain':
                card = next(c for c in state['player']['hand'] if c['name'] == 'Tempest')
                assert state['player']['orb_slots'] == [None, None] and state['player']['energy'] == 3, state
                receipt = await call('play_card', {'card_id': card['id']})
                events = [e for e in receipt['transition']['events'] if e['type'].startswith('orb_')]
                assert [e['type'] for e in events] == [
                    'orb_channeled', 'orb_channeled', 'orb_evoked', 'orb_removed', 'orb_channeled'], events
                assert events[0]['slot_index'] == 0 and events[-1]['slot_index'] == 1, events
                # The middle orb may first become visible after the front orb has departed.
                assert events[1]['slot_index'] in (0, 1), events
                assert [e['slot_index'] for e in events[2:4]] == [0, 0], events
                assert all(e['orb'] == {'name': 'Lightning'} for e in events), events
                state = await call('get_observation')
                assert [s['name'] for s in state['player']['orb_slots']] == ['Lightning', 'Lightning'], state
            else:
                cards = {c['name']: c['id'] for c in state['player']['hand']}
                receipt = await call('play_card', {'card_id': cards['Dualcast']})
                events = receipt['transition']['events']
                evoked = [e for e in events if e['type'] == 'orb_evoked']
                removed = [e for e in events if e['type'] == 'orb_removed']
                assert [e['orb']['name'] for e in evoked] == ['Lightning', 'Lightning'], events
                assert [e['slot_index'] for e in evoked] == [0, 0], events
                assert [e['orb']['name'] for e in removed] == ['Lightning'], events
                assert evoked[0]['sequence'] < evoked[1]['sequence'] < removed[0]['sequence'], events
                # Continue from the validated receipt without an extra observation.
                receipt = await call('play_card', {'card_id': cards['Capacitor']})
                slots = [e for e in receipt['transition']['events'] if e['type'] == 'orb_slots_changed']
                assert [(e['before'], e['after']) for e in slots] == [(5, 7)], receipt
                receipt = await call('play_card', {'card_id': cards['Zap']})
                channels = [e for e in receipt['transition']['events'] if e['type'] == 'orb_channeled']
                assert [(e['orb']['name'], e['slot_index']) for e in channels] == [('Lightning', 3)], receipt
                for e in evoked + removed + channels:
                    assert set(e) == {'sequence', 'type', 'target', 'orb', 'slot_index'}, e
                    assert set(e['orb']) == {'name'}, e
                await call('end_turn')
                state = await call('get_observation')
                assert [s['name'] if s else None for s in state['player']['orb_slots']] == [
                    'Frost', 'Dark', 'Plasma', 'Lightning', None, None, None], state
    print(f'PASS orb events: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['play', 'checks', 'chain'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
