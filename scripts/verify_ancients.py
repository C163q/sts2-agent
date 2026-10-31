import argparse
import asyncio
import json
import re
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    if report.exists() or report.with_suffix('').exists(): raise RuntimeError('Evidence paths must be new.')
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.with_suffix(''))}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    deadline = time.monotonic() + 45
    while True:
        start = await asyncio.to_thread(raw.call, 'get_state')
        if start['state']['scene'] == 'main_menu' or time.monotonic() >= deadline: break
        await asyncio.sleep(.2)
    assert start['state']['scene'] == 'main_menu', 'Requires fresh isolated instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', start['state']['snapshot_id'])
    assert created['ok'], created
    evidence = [{'created': created}]
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                assert data == json.loads(response.content[0].text)
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert data.get('error', {}).get('code') == error, data
                else: assert 'error' not in data, data
                return data

            async def fixture():
                data = await asyncio.to_thread(raw.call, 'check_test_ancient')
                assert data['ok'], data
                evidence.append({'fixture': data['state']})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                return data['state']

            def done(result):
                assert result['transition']['complete'] and result['transition']['stop_reason'] == 'action_completed', result

            await call('choose_ancient_option', {'option_id': 0}, error='observation_required')
            result = await call('get_observation')
            assert result['scene'] == 'ancient', result
            first = await fixture()
            await call('capture_screenshot', {'filename': 'arrival.png'})
            advances = 0
            for _ in range(30):
                if 'advance_dialogue' not in result['available_actions']: break
                assert not any(o['enabled'] for o in result['ancient']['options']), result
                result = await call('advance_dialogue'); done(result)
                advances += 1
            if args.scenario == 'dialogue': assert advances > 0, result
            assert 'choose_ancient_option' in result['available_actions'], result
            await call('capture_screenshot', {'filename': 'choices.png'})
            details = await call('inspect_ancient')
            assert not re.search('[\u4e00-\u9fff]', str(details)), details
            assert all('hover_tips' in o for o in details['ancient']['options']), details
            assert await fixture() == first
            if args.scenario == 'basic':
                await call('inspect_map'); covered = await call('get_observation')
                assert covered['ancient']['status'] == 'covered' and covered['ancient']['options'] is None, covered
                await call('inspect_ancient', error='illegal_action')
                await call('close_map'); result = await call('get_observation')
            option = result['ancient']['options'][0]
            assert option['enabled'], result
            result = await call('choose_ancient_option', {'option_id': option['id']})
            if args.scenario in {'tooth', 'shrymp', 'multi', 'transform', 'bundle'}:
                assert result['transition']['stop_reason'] == 'choice_required', result
                assert result['ancient']['status'] == 'covered', result
                expected = {'tooth': 'deck', 'shrymp': 'deck_enchant', 'multi': 'deck_enchant', 'transform': 'deck_transform', 'bundle': 'bundle'}[args.scenario]
                assert result['selection']['type'] == expected, result
                await call('capture_screenshot', {'filename': 'selection.png'})
                if args.scenario == 'bundle':
                    result = await call('selection_option', {'option_id': 'bundle:0'})
                    assert result['selection']['cards'], result
                    await call('selection_option', {'option_id': 'cancel_preview'})
                    result = await call('selection_option', {'option_id': 'bundle:1'})
                else:
                    count = 5 if args.scenario == 'tooth' else 3 if args.scenario == 'multi' else 1
                    for attempt in range(2):
                        details = await call('inspect_selection')
                        chosen = details['selection']['cards'][:count]
                        assert len(chosen) == count, details
                        for card in chosen:
                            result = await call('select_card', {'card_id': card['id']})
                            assert result['transition']['stop_reason'] == 'choice_required', result
                        assert any(o['id'] == 'confirm' and o['enabled'] for o in result['selection']['options']), result
                        if attempt == 0:
                            result = await call('selection_option', {'option_id': 'cancel_preview'})
                            assert not result['selection']['selected_ids'], result
                    if args.scenario in {'shrymp', 'multi'}:
                        assert len(result['selection']['enchant_previews']) == count, result
                        assert result['selection']['enchantment']['description'], result
                    if args.scenario == 'transform':
                        assert result['selection']['transform_previews'][0]['random'], result
                await call('capture_screenshot', {'filename': 'preview.png'})
                result = await call('selection_option', {'option_id': 'confirm'}); done(result)
            elif args.scenario == 'nested':
                done(result); assert result['scene'] == 'rewards', result
                assert result['ancient']['status'] == 'covered', result
                await call('inspect_rewards')
                result = await call('proceed'); done(result)
            elif args.scenario == 'pandora':
                assert result['selection']['type'] == 'view_cards', result
                result = await call('selection_option', {'option_id': 'confirm'}); done(result)
            else: done(result)
            after = await fixture()
            assert not after['pending'] and not after['previews'], after
            if args.scenario == 'basic': assert after['max_hp'] == first['max_hp'] + 11, after
            if args.scenario == 'touch':
                assert 'BURNING_BLOOD' not in after['relics'] and 'BLACK_BLOOD' in after['relics'], after
            if args.scenario == 'tooth': assert len(after['deck']) == len(first['deck']) - 5 and after['tooth_count'] == 5, after
            if args.scenario == 'shrymp': assert sum(c['enchantment'] == 'IMBUED' for c in after['deck']) == 1, after
            if args.scenario == 'multi': assert sum(c['enchantment'] == 'INSTINCT' for c in after['deck']) == 3, after
            if args.scenario == 'bundle': assert len(after['deck']) > len(first['deck']), after
            await call('capture_screenshot', {'filename': 'obtained.png'})
            await call('choose_ancient_option', {'option_id': option['id']}, error='illegal_action')
            result = await call('get_observation')
            if args.scenario in {'tooth', 'eye', 'earring', 'shrymp'}:
                start_combat = await asyncio.to_thread(raw.call, 'start_test_ancient_combat')
                assert start_combat['ok'], start_combat
                evidence.append({'start_combat': start_combat})
                result = await call('get_observation')
                battle = await fixture()
                assert result['scene'] == 'combat' and 'end_turn' in result['available_actions'], result
                if args.scenario == 'earring': assert battle['history_plays'] > 0 and battle['energy'] < 4, battle
                if args.scenario == 'shrymp': assert battle['history_plays'] >= 1, battle
                if args.scenario == 'eye':
                    result = await call('end_turn')
                    assert result['transition']['stop_reason'] == 'player_ready', result
                    assert result['turn'] == 2 and result['player']['exhaust_count'] == 5, result
                    assert not any(e['type'] == 'damage' for e in result['transition']['events']), result
                if args.scenario == 'tooth':
                    hand = await call('inspect_hand')
                    attack = next(c for c in hand['hand'] if c['name'] == 'Thunderclap')
                    result = await call('play_card', {'card_id': attack['id']})
                    assert result['transition']['stop_reason'] == 'combat_won', result
                    assert any(e['type'] == 'card_added' and e['card']['name'].endswith('+') for e in result['transition']['events']), result
                    final = await fixture()
                    assert len(final['deck']) == len(first['deck']) - 4 and final['tooth_count'] == 4, final
                    assert sum(c['upgrades'] > 0 for c in final['deck']) == 1, final
                    assert result['top_bar']['deck_count'] == len(final['deck']), (result, final)
                await call('capture_screenshot', {'filename': 'combat-result.png'})
            else:
                result = await call('proceed'); done(result)
                assert result['screen']['view'] == 'map' and result['ancient']['status'] == 'covered', result
    report.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='通过真实 MCP 验证隔离图形实例的先古之民和遗物。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
