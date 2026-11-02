"""Exercise native selection upgrade checkboxes without changing owned cards."""
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
from tests.game.verifiers.verify_selection_presets import compare_summary


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
        'directory': str(args.report.parent / 'screenshots')}}))
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert data == json.loads(reply.content[0].text), reply
                if error:
                    assert reply.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not reply.isError and 'error' not in data, data
                return data

            state = await call('get_observation')
            if args.scenario.startswith('ancient_'):
                deadline = time.monotonic() + 15
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline, state
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                option = next(o for o in state['ancient']['options'] if o['enabled'])
                await call('choose_ancient_option', {'option_id': option['id']})
            elif args.scenario == 'smith':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario == 'event_upgrade':
                await call('choose_event_option', {'option_id': state['event']['options'][1]['id']})

            original = await call('inspect_selection')
            supported = args.scenario in {'smith', 'event_upgrade', 'ancient_transform', 'ancient_pandora', 'multi_upgrade'}
            assert original['selection']['can_view_upgrades'] == supported, original
            assert original['selection']['view_upgrades'] is False, original
            check = {'smith': 'check_test_rest_site', 'event_upgrade': 'check_test_event',
                     'ancient_transform': 'check_test_ancient', 'ancient_pandora': 'check_test_ancient'}.get(args.scenario)
            before = await asyncio.to_thread(raw.call, check) if check else None

            for invalid in (None, 1, 'true'):
                response = await asyncio.to_thread(raw.call, 'inspect_selection',
                                                  arguments={'view_upgrades': invalid})
                assert response.get('error', {}).get('code') == 'invalid_request', response
            upgraded = await call('inspect_selection', {'view_upgrades': True})
            if supported:
                assert 'errors' not in upgraded, upgraded
                assert upgraded['selection']['view_upgrades'] is True, upgraded
                first = {c['id']: c for c in original['selection']['cards']}
                after = {c['id']: c for c in upgraded['selection']['cards']}
                assert set(first) == set(after), (first, after)
                assert any(first[i]['name'] != after[i]['name'] for i in first), (first, after)
                assert original['selection']['selected_ids'] == upgraded['selection']['selected_ids'], upgraded
                assert original['selection']['options'] == upgraded['selection']['options'], upgraded
                assert await call('inspect_selection') == upgraded
                summary = await call('inspect_selection', {'preset': 'summary'})
                compare_summary(upgraded, summary)
                missing = max(first) + 100000
                filtered = await call('inspect_selection', {'preset': 'summary', 'view_upgrades': True,
                                                          'card_ids': [next(iter(first)), missing]})
                assert filtered['errors'] == [{'code': 'cards_not_in_selection', 'card_ids': [missing]}], filtered
                assert len(filtered['selection']['cards']) == 1, filtered
                observed = await call('get_observation')
                assert observed['selection']['view_upgrades'] is True, observed
                assert all(card['id'] in after and card['name'] == after[card['id']]['name']
                           and card['energy_cost'] == after[card['id']]['energy_cost']
                           for card in observed['selection']['cards']), (observed, after)
                await call('capture_screenshot', {'filename': 'upgrades.png'})
                normal = await call('inspect_selection', {'view_upgrades': False})
                assert normal == original, (original, normal)
                await call('capture_screenshot', {'filename': 'normal.png'})
                if before:
                    after_model = await asyncio.to_thread(raw.call, check)
                    assert before['ok'] and after_model['ok'] and before['state'] == after_model['state'], (before, after_model)
                    evidence.append({'before_model': before, 'after_model': after_model})
                await call('inspect_selection', {'view_upgrades': True})
                if args.scenario == 'ancient_pandora':
                    await call('selection_option', {'option_id': 'confirm'})
                else:
                    targets = [c['id'] for c in original['selection']['cards'][:original['selection']['max_select']]]
                    for target in targets:
                        await call('select_card', {'card_id': target})
                    preview = await call('inspect_selection', {'view_upgrades': True})
                    assert preview['errors'] == [{'code': 'upgrade_view_unavailable'}], preview
                    assert set(preview['selection']['selected_ids']) == set(targets), preview
                    assert not preview['selection']['can_view_upgrades'], preview
                    if args.scenario == 'multi_upgrade':
                        assert len(preview['selection']['upgrade_previews']) == 2, preview
                        assert all(pair['before']['name'] is None
                                   for pair in preview['selection']['upgrade_previews']), preview
                    await call('capture_screenshot', {'filename': 'selected-preview.png'})
                    await call('selection_option', {'option_id': 'cancel_preview'})
                    retained = await call('inspect_selection')
                    assert retained['selection']['view_upgrades'] is True, retained
                    if retained['selection']['can_view_battlefield']:
                        await call('set_selection_view', {'view': 'battlefield'})
                        hidden = await call('get_observation')
                        assert hidden['selection']['view_upgrades'] is None, hidden
                        await call('inspect_selection', {'view_upgrades': True}, error='illegal_action')
                        await call('set_selection_view', {'view': 'selection'})
                    await call('inspect_selection', {'view_upgrades': False})
                    for target in targets:
                        await call('select_card', {'card_id': target})
                    await call('selection_option', {'option_id': 'confirm'})
            else:
                assert upgraded['selection'] == original['selection'], (original, upgraded)
                assert upgraded['errors'] == [{'code': 'upgrade_view_unavailable'}], upgraded
                ids = [c['id'] for c in original['selection']['cards']]
                missing = max(ids) + 100000
                filtered = await call('inspect_selection', {'view_upgrades': True, 'preset': 'summary',
                                                          'card_ids': [ids[0], missing]})
                assert filtered['errors'] == [{'code': 'upgrade_view_unavailable'},
                                             {'code': 'cards_not_in_selection', 'card_ids': [missing]}], filtered
                assert len(filtered['selection']['cards']) == 1, filtered
                assert not filtered['selection']['view_upgrades'], filtered
                await call('capture_screenshot', {'filename': 'unsupported.png'})
                await call('inspect_selection')
                await call('select_card', {'card_id': ids[0]})
                chosen = await call('get_observation')
                if (chosen.get('selection') or {}).get('options'):
                    confirm = next((o for o in chosen['selection']['options'] if o['id'] == 'confirm' and o['enabled']), None)
                    if confirm:
                        await call('selection_option', {'option_id': 'confirm'})
            args.report.write_text(json.dumps(evidence, indent=2) + '\n')
            print(json.dumps({'scenario': args.scenario, 'calls': len(evidence), 'supported': supported}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
