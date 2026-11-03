"""Verify shared card appearance through native UI and real stdio MCP."""
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

    def record(value):
        evidence.append(value)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(args.report.parent / 'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
                                  '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments):
                response = await session.call_tool(tool, arguments)
                value = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': value})
                assert not response.isError and 'error' not in value, value
                return value

            before = await asyncio.to_thread(raw.call, 'get_state')
            checks = await asyncio.to_thread(raw.call, 'check_test_afflictions')
            record({'native_checks': checks})
            assert checks['ok'] and checks['state']['passed'], checks
            for preset in ('full', 'default', 'summary'):
                observation = await call('get_observation', {'preset': preset})
                hand = await call('inspect_hand', {'preset': preset})
                for cards in (observation['player']['hand'], hand['hand']):
                    assert [card.get('affliction') for card in cards] == [{'name': 'Bound'}, {'name': 'Smog'}, None], cards
                    assert cards[0]['enchantment'] == {'name': 'Sharp', 'amount': 3, 'dimmed': False}, cards
                    for key in ('enchantment', 'affliction'):
                        assert (key in cards[2]) == (preset == 'full'), cards[2]
                assert all('description' not in card for card in observation['player']['hand'])
                if preset == 'full':
                    assert any(tip['title'] == 'Bound' for tip in hand['hover_tips']), hand
                    assert any(tip['title'] == 'Smog' for tip in hand['hover_tips']), hand
            await call('capture_screenshot', {'filename': 'afflictions.png'})
            after = await asyncio.to_thread(raw.call, 'get_state')
            record({'before': before, 'after': after})
            assert before['ok'] and after['ok'] and before['state'] == after['state']
    print('PASS shared card appearance:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证共用卡牌格式与可见外观。')
    parser.add_argument('--scenario', choices=('afflictions',), default='afflictions')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
