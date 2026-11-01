"""Verify hand presets against native visible cards and real actions over stdio MCP."""
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
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(args.report.parent / 'screenshots')}}))

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {tool.name: tool for tool in (await session.list_tools()).tools}
            assert set(tools['inspect_hand'].inputSchema['properties']) == {'preset', 'card_ids'}

            async def call(name, arguments=None, error=None):
                result = await session.call_tool(name, arguments or {})
                data = result.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert data == json.loads(result.content[0].text), result
                if error:
                    assert result.isError and data['error']['code'] == error, data
                else:
                    assert not result.isError and 'error' not in data, data
                return data

            before = await asyncio.to_thread(raw.call, 'get_state')
            assert before['ok'], before
            if args.scenario == 'enchantments':
                checks = await asyncio.to_thread(raw.call, 'check_test_enchantments')
                record({'enchantment_checks': checks})
                assert checks['ok'] and checks['state']['passed'], checks
                observed = await call('get_observation')
                assert [card.get('enchantment') for card in observed['player']['hand']] == [
                    {'name': 'Sharp', 'amount': 3, 'dimmed': False},
                    {'name': 'Swift', 'amount': 2, 'dimmed': True},
                    {'name': 'Clone', 'dimmed': False}, None], observed
                assert all('description' not in card for card in observed['player']['hand'])
            full = await call('inspect_hand')
            assert full == await call('inspect_hand', {'preset': 'full'})
            assert [card['id'] for card in full['hand']] == [card['id'] for card in before['state']['player']['hand']]
            summary = await call('inspect_hand', {'preset': 'summary'})
            allowed = {'id', 'name', 'type', 'energy_cost', 'star_cost', 'energy_cost_color',
                       'star_cost_color', 'unplayable_markers', 'outline', 'enchantment'}
            assert set(summary) == {'hand'}, summary
            for brief, card in zip(summary['hand'], full['hand'], strict=True):
                assert set(brief) <= allowed
                assert all(brief[key] == card[key] for key in brief)
                assert {'id', 'name', 'type', 'energy_cost', 'unplayable_markers', 'outline'} <= brief.keys()
                assert ('star_cost' in brief) == (card['star_cost'] is not None), brief
                if args.scenario == 'enchantments':
                    basic = next(c for c in observed['player']['hand'] if c['id'] == brief['id'])
                    assert brief.get('enchantment') == card.get('enchantment') == basic.get('enchantment')
            if args.scenario == 'stars':
                assert any(card.get('star_cost') == '2' and card.get('star_cost_color') == 'red'
                           and card['outline'] == 'none' for card in summary['hand']), summary
            elif args.scenario == 'x_cost':
                assert any(card['name'] == 'Whirlwind' and card['energy_cost'] == 'X' for card in summary['hand']), summary
            elif args.scenario == 'card_names':
                assert any(card['name'] == 'True Grit+' for card in summary['hand']), summary
            ids = [card['id'] for card in full['hand']]
            missing = max(ids) + 100000
            requested = [ids[-1], ids[0], ids[0], missing, missing]
            for preset in ('full', 'summary'):
                selected = await call('inspect_hand', {'preset': preset, 'card_ids': requested})
                assert [card['id'] for card in selected['hand']] == [i for i in ids if i in requested]
                assert selected['errors'] == [{'code': 'cards_not_in_hand', 'card_ids': [missing]}], selected
                if preset == 'full':
                    selected_ids = {ids[0], ids[-1]}
                    expected_links = {(i, tip['title'], tip['description']) for tip in full['hover_tips']
                                      for i in tip['card_ids'] if i in selected_ids}
                    links = {(i, tip['title'], tip['description']) for tip in selected['hover_tips'] for i in tip['card_ids']}
                    assert links == expected_links, selected
                assert (await call('inspect_hand', {'preset': preset, 'card_ids': []})) == {
                    'hand': [], **({'hover_tips': []} if preset == 'full' else {})}
            await call('capture_screenshot', {'filename': f'{args.scenario}-hand.png'})
            after = await asyncio.to_thread(raw.call, 'get_state')
            record({'before': before, 'after': after})
            assert after['ok'] and before['state']['snapshot_id'] == after['state']['snapshot_id'], after
            if args.scenario == 'selection':
                armaments = next(card for card in full['hand'] if card['name'] == 'Armaments')
                await call('inspect_hand', {'preset': 'summary', 'card_ids': [armaments['id']]})
                receipt = await call('play_card', {'card_id': armaments['id']})
                assert receipt['transition']['stop_reason'] == 'choice_required', receipt
                await call('set_selection_view', {'view': 'battlefield'})
                detail = await call('inspect_hand', {'preset': 'summary', 'card_ids': [armaments['id']]})
                assert detail['hand'] == [] and detail['errors'][0]['card_ids'] == [armaments['id']], detail
                assert set(detail['notes']) == {'selection'}, detail
                assert 'view="selection"' in detail['notes']['selection'], detail
                await call('set_selection_view', {'view': 'selection'})
            else:
                defend = next(card for card in full['hand'] if card['name'].startswith('Defend'))
                await call('inspect_hand', {'preset': 'summary', 'card_ids': [defend['id'], missing]})
                played = await call('play_card', {'card_id': defend['id']})
                assert played['transition']['stop_reason'] == 'player_ready' and played['transition']['complete'], played
                remaining = next(i for i in ids if i != defend['id'])
                detail = await call('inspect_hand', {'card_ids': [defend['id'], remaining]})
                assert [card['id'] for card in detail['hand']] == [remaining], detail
                assert detail['errors'] == [{'code': 'cards_not_in_hand', 'card_ids': [defend['id']]}], detail
                empty = await call('inspect_hand', {'preset': 'summary', 'card_ids': [defend['id']]})
                assert empty['hand'] == [] and empty['errors'][0]['card_ids'] == [defend['id']], empty
                ended = await call('end_turn')
                assert ended['transition']['stop_reason'] == 'player_ready' and ended['transition']['complete'], ended
    print('PASS hand presets:', args.scenario, 'projection, ID filtering, UI unchanged and direct continuation', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证手牌摘要、筛选和合并错误。')
    parser.add_argument('--scenario', choices=('basic', 'stars', 'x_cost', 'card_names', 'selection', 'enchantments'), default='basic')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
