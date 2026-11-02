"""Verify complete native candidates and compact cards through real stdio MCP."""
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
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                started = time.perf_counter()
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data, 'seconds': time.perf_counter() - started})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert not reply.isError and 'error' not in data, data
                assert json.loads(reply.content[0].text) == data
                return data

            checks = await asyncio.to_thread(raw.call, 'check_test_selection_observation')
            evidence.append({'native_checks': checks})
            args.report.write_text(json.dumps(evidence, indent=2) + '\n')
            assert checks['ok'], checks
            if args.scenario == 'grid':
                assert checks['state']['passed'], checks
            before = await asyncio.to_thread(raw.call, 'get_state')
            full = await call('get_observation', {'preset': 'full'})
            details = await call('inspect_selection', {'preset': 'full'})
            issues = []
            if len(full['selection']['cards']) != 40:
                issues.append('Basic observation must return all 40 candidates.')
            expected = [{'name': 'Sharp', 'amount': 3, 'dimmed': False},
                        {'name': 'Swift', 'amount': 2, 'dimmed': True},
                        {'name': 'Clone', 'dimmed': False}, {'name': 'Spiral', 'dimmed': False}]
            if args.scenario == 'grid':
                for offset in (0, 36):
                    for index, enchantment in enumerate(expected):
                        card = details['selection']['cards'][offset + index]
                        if card.get('enchantment') != enchantment:
                            issues.append(f'Missing native enchantment at candidate {offset + index}: {card.get("enchantment")}')
            else:
                for enchantment in expected:
                    assert sum(c.get('enchantment') == enchantment for c in details['selection']['cards']) == 2
            assert not issues, issues
            assert [c['id'] for c in full['selection']['cards']] == [c['id'] for c in details['selection']['cards']]
            summary = await call('get_observation', {'preset': 'summary'})
            brief = await call('inspect_selection', {'preset': 'summary'})
            assert summary['selection'] == brief['selection']
            assert all('description' not in c and c.get('outline') != 'none'
                       and c.get('unplayable_markers') != [] for c in brief['selection']['cards'])
            after = await asyncio.to_thread(raw.call, 'get_state')
            if args.scenario == 'grid':
                assert checks['state']['passed'], checks
            assert before['state'] == after['state'], 'Read-only selection calls changed UI or game state.'
            if args.scenario == 'upgrades':
                await call('inspect_selection', {'view_upgrades': True, 'preset': 'summary'})
                upgrade_checks = await asyncio.to_thread(raw.call, 'check_test_selection_observation')
                evidence.append({'upgrade_native_checks': upgrade_checks})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert upgrade_checks['ok'] and upgrade_checks['state']['passed'], upgrade_checks
                upgraded = await call('get_observation', {'preset': 'full'})
                assert len(upgraded['selection']['cards']) == 40
                assert upgraded['selection']['view_upgrades'] is True
                original = {c['id']: c for c in full['selection']['cards']}
                assert any(c['name'] != original[c['id']]['name'] for c in upgraded['selection']['cards'])
                for card in upgraded['selection']['cards']:
                    assert card.get('enchantment') == original[card['id']].get('enchantment')
                body_slam = next(c for c in upgraded['selection']['cards'] if c['name'] == 'Body Slam+')
                assert body_slam['energy_cost'] == '0' and body_slam['energy_cost_color'] == 'green', body_slam
                target = await call('inspect_selection', {'preset': 'summary', 'card_ids': [body_slam['id'], 1000000]})
                assert target['errors'] == [{'code': 'cards_not_in_selection', 'card_ids': [1000000]}]
                await call('select_card', {'card_id': body_slam['id']})
                preview = await call('get_observation', {'preset': 'summary'})
                assert preview['selection']['cards'] == []
                assert len(preview['selection']['upgrade_previews']) == 1
                assert not preview['selection']['can_view_upgrades']
                preview_checks = await asyncio.to_thread(raw.call, 'check_test_selection_observation')
                evidence.append({'preview_native_checks': preview_checks})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert preview_checks['ok'] and preview_checks['state']['passed'], preview_checks
                assert checks['state']['passed'], checks
                await call('selection_option', {'option_id': 'confirm'})
                print('PASS full upgrade candidates, enchantments, green zero cost and direct preview')
                return
            # Select the last card directly; the native click scrolls it into view.
            last = brief['selection']['cards'][-1]
            await call('select_card', {'card_id': last['id']})
            selected = await call('get_observation', {'preset': 'full'})
            assert selected['selection']['selected_ids'] == [last['id']]
            assert len(selected['selection']['cards']) == 40
            for before_card, after_card in zip(full['selection']['cards'], selected['selection']['cards'], strict=True):
                for field in ('id', 'name', 'type', 'energy_cost', 'star_cost', 'enchantment'):
                    assert before_card.get(field) == after_card.get(field), (field, before_card, after_card)
            assert selected['selection']['cards'][-1]['enchantment'] == expected[-1]
            await call('set_selection_view', {'view': 'battlefield'})
            hidden = await call('get_observation', {'preset': 'summary'})
            assert hidden['selection']['status'] == 'battlefield' and 'cards' not in hidden['selection']
            await call('inspect_deck')
            covered = await call('get_observation', {'preset': 'summary'})
            assert covered['selection']['status'] == 'covered' and 'cards' not in covered['selection']
            await call('close_card_view')
            await call('set_selection_view', {'view': 'selection'})
            await call('select_card', {'card_id': last['id']})
            returned = await call('get_observation', {'preset': 'summary'})
            assert returned['selection']['selected_ids'] == []
            assert len(returned['selection']['cards']) == 40
            await call('inspect_selection', {'preset': 'summary', 'card_ids': [last['id'], 1000000]})
            await call('select_card', {'card_id': last['id']})
            # A second different card completes this two-card choice.
            first_id = brief['selection']['cards'][0]['id']
            await call('select_card', {'card_id': first_id})
            print('PASS complete grid, native enchantments, summaries, hidden selection and direct scrolling')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=['grid', 'upgrades'], required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
