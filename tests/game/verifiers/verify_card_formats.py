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


async def verify_browse(call, raw, record):
    before = await call('get_observation', {'preset': 'full'})
    full = await call('inspect_deck', {'preset': 'full'})
    assert full['deck'] and 'detail_level' not in full, full
    assert all('description' in card and 'enchantment' in card and 'affliction' in card for card in full['deck'])
    default = await call('inspect_deck', {})
    assert all('description' in card for card in default['deck']) and 'hover_tips' in default
    summary = await call('inspect_deck', {'preset': 'summary'})
    assert [card['id'] for card in summary['deck']] == [card['id'] for card in full['deck']]
    assert all(not {'description', 'hover_tips', 'rarity', 'visual_card_pool'} & card.keys() for card in summary['deck'])
    assert 'hover_tips' not in summary
    token = await asyncio.to_thread(raw.call, 'get_state')
    invalid = await asyncio.to_thread(raw.call, 'inspect_deck', arguments={'detail_level': 'full'})
    current = await asyncio.to_thread(raw.call, 'get_state')
    record({'native_old_option': invalid, 'before': token, 'after': current})
    assert not invalid['ok'] and invalid['error']['code'] == 'invalid_request'
    assert token['state'] == current['state']
    upgraded = await call('inspect_deck', {'preset': 'full', 'view_upgrades': True})
    assert upgraded['view_upgrades'] and any(a['name'] != b['name'] for a, b in zip(full['deck'], upgraded['deck'], strict=True))
    sorted_view = await call('inspect_deck', {'preset': 'summary', 'sort_by': 'cost', 'descending': True})
    assert sorted_view['view_upgrades'] and sorted_view['sort'] == {'by': 'cost', 'descending': True}
    assert set(card['id'] for card in sorted_view['deck']) == set(card['id'] for card in full['deck'])
    await call('close_card_view', {})
    for pile in ('draw', 'discard', 'exhaust'):
        full = await call('inspect_pile', {'pile': pile, 'preset': 'full'})
        default = await call('inspect_pile', {'pile': pile})
        summary = await call('inspect_pile', {'pile': pile, 'preset': 'summary'})
        assert 'detail_level' not in full and summary['status'] == full['status']
        if full['status'] == 'opened':
            assert full['cards'] and all('description' in card for card in default['cards'])
            assert [card['id'] for card in full['cards']] == [card['id'] for card in summary['cards']]
            assert all(not {'description', 'hover_tips', 'rarity', 'visual_card_pool'} & card.keys() for card in summary['cards'])
            await call('close_card_view', {})
        elif full['status'] == 'empty':
            assert full['cards'] == default['cards'] == summary['cards'] == []
        else:
            assert full['cards'] is None and 'cards' not in default and 'cards' not in summary
    after = await call('get_observation', {'preset': 'full'})
    assert before == after, 'Browsing changed gameplay.'


async def verify_resources(call, raw, record):
    before = await asyncio.to_thread(raw.call, 'get_state')
    checks = await asyncio.to_thread(raw.call, 'check_test_hand_resources')
    record({'native_resource_checks': checks})
    assert checks['ok'] and checks['state']['passed'], checks
    observation = await call('get_observation', {'preset': 'full'})
    values = {key: observation['player'][key] for key in (
        'energy', 'max_energy', 'stars', 'draw_count', 'discard_count', 'exhaust_count')}
    assert values['energy'] == 20 and values['max_energy'] == 3, values
    compact = {'energy': '20/3'}
    compact.update({key: value for key, value in values.items()
                    if key not in ('energy', 'max_energy') and value is not None})
    for preset in ('full', 'default', 'summary'):
        for ids in ([], [2147483647]):
            hand = await call('inspect_hand', {'preset': preset, 'card_ids': ids})
            assert hand['hand'] == []
            expected = compact if preset == 'summary' else {key: value for key, value in values.items()
                                                            if preset == 'full' or value is not None}
            assert {key: value for key, value in hand.items() if key in values} == expected, hand
            if ids: assert hand['errors'] == [{'code': 'cards_not_in_hand', 'card_ids': ids}]
    after = await asyncio.to_thread(raw.call, 'get_state')
    record({'before': before, 'after': after})
    assert before['state'] == after['state'], 'Resource checks changed game or UI.'


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

            if args.scenario == 'browse':
                await verify_browse(call, raw, record)
                print('PASS shared browse formats, options and native old-option rejection', flush=True)
                return
            if args.scenario == 'resources':
                await verify_resources(call, raw, record)
                print('PASS hand HUD resources, hidden-body independence and empty filters', flush=True)
                return
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
    parser.add_argument('--scenario', choices=('afflictions', 'browse', 'resources'), default='afflictions')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
