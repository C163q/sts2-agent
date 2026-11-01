"""Exercise same-action combat replacement through real MCP."""
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
    raw = Client(ipc_directory(), timeout=90)
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
            if args.scenario == 'checks':
                reply = await asyncio.to_thread(raw.call, 'check_test_combat_handoff')
                record({'native_checks': reply})
                assert reply['ok'] and reply['state']['passed'], reply
                return
            if args.scenario == 'turn':
                receipt = await call('end_turn')
            else:
                name = 'Armaments' if args.scenario == 'selection' else 'Defend'
                card = next(c for c in state['player']['hand'] if c['name'] == name)
                receipt = await call('play_card', {'card_id': card['id']})
                if args.scenario == 'selection':
                    assert receipt['transition']['stop_reason'] == 'choice_required', receipt
                    selection = (await call('inspect_selection', {'preset': 'summary'}))['selection']
                    receipt = await call('select_card', {'card_id': selection['cards'][0]['id']})
                    if receipt['transition']['stop_reason'] == 'choice_required':
                        receipt = await call('selection_option', {'option_id': 'confirm'})
            transition = receipt['transition']
            assert transition['complete'] and transition['stop_reason'] == (
                'choice_required' if args.scenario == 'choice' else 'player_ready'), receipt
            assert receipt['scene'] == 'combat', receipt
            events = transition['events']
            assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), events
            starts = [i for i, e in enumerate(events) if e['type'] == 'combat_started']
            assert len(starts) == 1, events
            split = starts[0]
            assert set(events[split]) == {'sequence', 'type'}, events
            if args.scenario == 'choice':
                selection = (await call('inspect_selection', {'preset': 'summary'}))['selection']
                receipt = await call('select_card', {'card_id': selection['cards'][0]['id']})
                if receipt['transition']['stop_reason'] == 'choice_required':
                    receipt = await call('selection_option', {'option_id': 'confirm'})
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
                assert not any(e['type'] == 'combat_started' for e in receipt['transition']['events']), receipt
            else:
                assert len([e for e in events[split + 1:] if e['type'] == 'card_drawn']) == 5, events
            if args.scenario == 'play':
                assert sum(e['type'] == 'card_played' for e in events[:split]) == 1, events
                assert any(e['type'] == 'block_changed' and e['after'] == 5 for e in events[:split]), events
            # Continue directly from the receipt into the new combat.
            result = await call('end_turn')
            assert result['transition']['complete'] and result['transition']['stop_reason'] == 'player_ready', result
            assert not any(e['type'] == 'combat_started' for e in result['transition']['events']), result
            state = await call('get_observation')
            assert state['turn'] == 2, state
    print(f'PASS combat handoff: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['play', 'turn', 'selection', 'choice', 'checks'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
