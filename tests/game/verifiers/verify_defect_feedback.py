"""Verify enchanted shop removal without preview notifications in action receipts."""
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
    evidence, events = [], []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    async def native():
        response = await asyncio.to_thread(raw.call, 'check_test_shop')
        record({'native': response})
        assert response['ok'], response
        return response['state']

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, **arguments):
                response = await session.call_tool(name, {'preset': 'full', **arguments})
                result = response.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': result})
                assert not response.isError, result
                if 'transition' in result:
                    assert result['transition']['complete'], result
                    events.extend(result['transition']['events'])
                assert not any(e['type'] == 'card_enchantment_changed' for e in events), events
                return result

            state = await call('get_observation')
            before = await native()
            assert len(before['enchantments']) == 4, before
            if args.scenario == 'shop':
                await call('open_shop')
                shop = (await call('inspect_shop'))['shop']
                removal = next(item for item in shop['items'] if item['kind'] == 'card_removal')
                await call('buy_item', item_id=removal['id'])
            else:
                assert state.get('selection'), state
            selection = (await call('inspect_selection'))['selection']
            card = next(card for card in selection['cards'] if not card.get('enchantment'))
            await call('select_card', card_id=card['id'], preset='default')
            state = await call('get_observation')
            if state.get('selection'):
                await call('selection_option', option_id='confirm')
            after = await native()
            assert after['enchantments'] == before['enchantments'], (before, after)
            assert after['deck_count'] == before['deck_count'] - 1, (before, after)
            assert [e['type'] for e in events if e['type'].startswith('card_')] == ['card_selected', 'card_removed'], events
    print('PASS enchanted removal: ' + args.scenario)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['shop', 'parasol'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
