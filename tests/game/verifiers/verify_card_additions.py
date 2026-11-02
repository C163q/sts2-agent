"""Verify visible card-add destinations through native actions and public MCP receipts."""
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
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
                                  '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert data == json.loads(reply.content[0].text), reply
                assert not reply.isError and 'error' not in data, data
                return data

            before = await call('get_observation')
            if args.scenario == 'checks':
                result = await asyncio.to_thread(raw.call, 'check_test_card_additions')
                record({'checks': result})
                assert result['ok'] and result['state']['passed'], result
                return
            if args.scenario == 'reward':
                selection = await call('inspect_selection', {'preset': 'summary'})
                chosen = selection['selection']['cards'][0]
                result = await call('select_card', {'card_id': chosen['id']})
                expected = [(chosen['name'], 'deck')]
            elif args.scenario == 'enemy':
                result = await call('end_turn')
                expected = [('Slimed', 'discard')] * 2
            else:
                name = {'hand': 'Blade Dance', 'overflow': 'Blade Dance', 'discard': 'Anger',
                        'normal': 'Strike'}[args.scenario]
                card = next(c for c in before['player']['hand'] if c['name'] == name)
                arguments = {'card_id': card['id']}
                if args.scenario in ('discard', 'normal'):
                    arguments['target_id'] = max(before['enemies'], key=lambda e: e['hp'])['id']
                result = await call('play_card', arguments)
                expected = {'hand': [('Shiv', 'hand')] * 3,
                            'overflow': [('Shiv', 'hand'), ('Shiv', 'discard'), ('Shiv', 'discard')],
                            'discard': [('Anger', 'discard')],
                            'normal': []}[args.scenario]
            transition = result['transition']
            assert transition['complete'], result
            events = transition['events']
            assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), events
            added = [e for e in events if e['type'] == 'card_added']
            assert [(e['card']['name'], e['pile']) for e in added] == expected, added
            assert all(set(e) == {'sequence', 'type', 'card', 'pile'} for e in added), added
            assert len({e['card']['id'] for e in added}) == len(added), added
            if args.scenario in ('hand', 'overflow'):
                after = await call('get_observation')
                visible = {c['id']: c['name'] for c in after['player']['hand']}
                assert all(visible[e['card']['id']] == e['card']['name'] for e in added if e['pile'] == 'hand')
                assert after['top_bar']['deck_count'] == before['top_bar']['deck_count'], after
                assert len(after['player']['hand']) == (5 if args.scenario == 'hand' else 10), after
    print(f'PASS card-add destinations: {args.scenario}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True,
                        choices=['hand', 'overflow', 'discard', 'normal', 'enemy', 'reward', 'checks'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
