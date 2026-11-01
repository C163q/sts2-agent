"""Exercise public orb observations, hover routing and native capacity/melting checks."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client
from verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name('mcp_server.py')),
                                  '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert not reply.isError and 'error' not in data, data
                assert data == json.loads(reply.content[0].text), reply
                return data

            state = await call('get_observation')
            if args.scenario == 'resources':
                result = await asyncio.to_thread(raw.call, 'check_test_capacity')
                record({'native_checks': result})
                assert result['ok'] and result['state']['passed'], result
                await call('get_observation')
                await call('end_turn')
            elif args.scenario == 'wax_melt':
                assert state['player']['max_energy'] == 4, state
                card = next(c for c in state['player']['hand'] if c['name'] == 'Defend')
                receipt = await call('play_card', {'card_id': card['id']})
                events = receipt['transition']['events']
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
                assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), events
                assert [e['relic']['name'] for e in events if e['type'] == 'relic_melted'] == ["Wax Philosopher's Stone"], events
                assert not any(e['type'] == 'relic_removed' for e in events), events
                assert [(e['before'], e['after']) for e in events if e['type'] == 'max_energy_changed'] == [(4, 3)], events
                await call('end_turn')
                after = await call('get_observation')
                assert after['player']['max_energy'] == 3, after
                assert any(r['name'] == "Wax Philosopher's Stone" and r['melted'] for r in after['top_bar']['relics']), after
                relics = await call('inspect_relics')
                melted = next(r for r in relics['relics'] if r['name'] == "Wax Philosopher's Stone")
                assert melted['melted'] and 'melt' in melted['description'].lower(), melted
            elif args.scenario == 'orbs':
                assert state['player']['character'] == 'DEFECT', state
                slots = state['player'].get('orb_slots')
                assert slots == [
                    {'name': 'Lightning', 'passive': 3, 'evoke': None},
                    {'name': 'Frost', 'passive': 2, 'evoke': None},
                    {'name': 'Dark', 'passive': 6, 'evoke': 6},
                    {'name': 'Plasma', 'passive': None, 'evoke': None}, None], state
                details = await call('inspect_combatants')
                assert details['player']['orb_slots'] == slots, details
                assert not any('\u4e00' <= c <= '\u9fff' for c in json.dumps(details, ensure_ascii=False)), details
                sources = {source for tip in details['hover_tips'] for source in tip['sources']}
                assert {f'player.orb_slots.{i}' for i in range(4)} <= sources, details
                assert 'player.orb_slots.4' not in sources, details
                ui = await call('inspect_ui')
                assert not any('\u4e00' <= c <= '\u9fff' for c in json.dumps(ui, ensure_ascii=False)), ui
                assert any('player.orb_slots.4' in tip['sources'] for tip in ui['hover_tips']), ui
                assert not any(f'player.orb_slots.{i}' in tip['sources'] for tip in ui['hover_tips'] for i in range(4)), ui
                assert await call('inspect_combatants') == details
                for name in ('Dualcast', 'Capacitor', 'Zap'):
                    card = next(c for c in state['player']['hand'] if c['name'] == name)
                    receipt = await call('play_card', {'card_id': card['id']})
                    assert receipt['transition']['complete'], receipt
                    state = await call('get_observation')
                    current = state['player']['orb_slots']
                    if name == 'Dualcast':
                        assert [c['name'] if c else None for c in current] == ['Frost', 'Dark', 'Plasma', None, None], current
                    elif name == 'Capacitor':
                        assert len(current) == 7 and current[-4:] == [None] * 4, current
                    else:
                        assert [c['name'] if c else None for c in current] == ['Frost', 'Dark', 'Plasma', 'Lightning', None, None, None], current
                await call('end_turn')
                state = await call('get_observation')
                assert next(c for c in state['player']['orb_slots'] if c and c['name'] == 'Dark')['evoke'] == 12, state
            else:
                result = await asyncio.to_thread(raw.call, 'check_test_orb_visibility')
                record({'native_checks': result})
                assert result['ok'] and result['state']['passed'], result
    print(f'PASS capacity: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['resources', 'orbs', 'orb_visibility', 'wax_melt'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
