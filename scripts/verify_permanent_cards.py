"""Verify permanent card mutations with native play and real MCP receipts."""
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
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

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
                if 'transition' in data:
                    assert data['transition']['complete'], data
                    events = data['transition']['events']
                    assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), events
                return data

            if args.scenario == 'checks':
                result = await asyncio.to_thread(raw.call, 'check_test_permanent_cards')
                record({'native_checks': result})
                assert result['ok'] and result['state']['passed'], result
                return
            state = await call('get_observation')
            hand = await call('inspect_hand')
            name = 'Genetic Algorithm' if args.scenario == 'genetic' else 'Defend'
            card = next(c for c in hand['hand'] if c['name'] == name)
            if args.scenario == 'genetic':
                assert '1' in card['description'] and '3' in card['description'], card
            receipt = await call('play_card', {'card_id': card['id']})
            kind = {'genetic': 'card_stats_changed', 'cost': 'card_energy_cost_changed',
                    'enchant': 'card_enchantment_changed'}[args.scenario]
            changes = [e for e in receipt['transition']['events'] if e['type'] == kind]
            assert len(changes) == 1, receipt
            assert set(changes[0]) == {'sequence', 'type', 'card', 'pile'} and changes[0]['pile'] == 'deck', changes
            assert changes[0]['card']['name'] == ('Genetic Algorithm' if args.scenario == 'genetic' else 'Strike'), changes
            # A successful mutation receipt must support the next action without a compulsory observation.
            await call('end_turn')
            deck = await call('inspect_deck', {'detail_level': 'full'})
            if args.scenario == 'genetic':
                grown = next(c for c in deck['deck'] if c['name'] == 'Genetic Algorithm')
                assert '4' in grown['description'], grown
            elif args.scenario == 'cost':
                assert any(c['name'] == 'Strike' and c['energy_cost'] == '0' for c in deck['deck']), deck
            await call('close_card_view')
    print(f'PASS permanent cards: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['genetic', 'cost', 'enchant', 'checks'], required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
