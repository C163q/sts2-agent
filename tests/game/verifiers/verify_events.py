from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from tests.game.support.verification_actions import observe_after_action
import argparse
import asyncio
import json
import re
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client


async def verify(args):
    root = ROOT
    report = args.report.resolve(); report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    initial = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while initial['state']['scene'] == 'unrecognized' and time.monotonic() < deadline:
        await asyncio.sleep(.1); initial = await asyncio.to_thread(raw.call, 'get_state')
    assert initial['state']['scene'] == 'main_menu', 'Requires a fresh isolated instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', initial['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = response.structuredContent
                assert data == json.loads(response.content[0].text), response
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert data.get('error', {}).get('code') == error, data
                else: assert 'error' not in data, data
                return data

            async def check():
                result = await asyncio.to_thread(raw.call, 'check_test_event')
                assert result['ok'], result
                return result['state']

            async def capture(name):
                await call('capture_screenshot', {'filename': name + '.png'})

            async def choose(data, index):
                result = await observe_after_action(call, await call('choose_event_option', {'option_id': data['event']['options'][index]['id']}))
                assert result['transition']['complete'] and result['transition']['stop_reason'] != 'timeout', result
                return result

            async def finish_selection(data):
                seen = 0
                while (data.get('selection') or {}).get('status') == 'visible':
                    seen += 1; assert seen < 12, data
                    choice = data['selection']
                    if len(choice['selected_ids']) < choice['min_select']:
                        card = next(c for c in choice['cards'] if c['id'] not in choice['selected_ids'])
                        data = await observe_after_action(call, await call('select_card', {'card_id': card['id']}))
                    else:
                        option = next(o for o in choice['options'] if o['enabled'] and o['id'] == 'confirm')
                        data = await observe_after_action(call, await call('selection_option', {'option_id': option['id']}))
                    assert data['transition']['complete'], data
                return data

            async def finish_event(data):
                assert data['scene'] == 'event' and data['event']['proceed']['enabled'], data
                current = await check()
                assert not current['pending'] and not current['previews'], current
                await capture('finished')
                result = await observe_after_action(call, await call('proceed'))
                assert result['transition']['stop_reason'] == 'action_completed', result
                assert (await call('inspect_map'))['can_travel'], result

            data = await call('get_observation')
            assert data['scene'] == 'event' and data['event']['status'] == 'visible', data
            assert 'description' not in data['event'] and data['event']['options'], data
            assert 'choose_event_option' in data['available_actions'], data
            before = await check()
            text_checks = await asyncio.to_thread(raw.call, 'check_test_event_english')
            assert text_checks['ok'], text_checks
            inspected = await call('inspect_event')
            assert all('hover_tips' in o for o in inspected['event']['options']), inspected
            assert not re.search('[\u4e00-\u9fff]', json.dumps(inspected, ensure_ascii=False)), inspected
            assert await check() == before, 'Inspection changed the event, RNG or run.'
            await capture('initial')
            scenario = args.scenario
            if scenario == 'basic':
                original_ids = {o['id'] for o in data['event']['options']}
                await call('inspect_map')
                covered = await call('get_observation')
                assert covered['event'] == {'status': 'covered', 'name': None, 'description': None, 'options': None, 'proceed': None}, covered
                await call('close_map'); data = await call('get_observation')
                data = await choose(data, 0)
                assert not original_ids & {o['id'] for o in data['event']['options']}, data
                assert data['top_bar']['hp'] == before['hp'] - 1 and data['top_bar']['max_hp'] == 82, data
                await call('choose_event_option', {'option_id': min(original_ids)}, error='illegal_action')
                data = await call('get_observation'); data = await choose(data, 1)
                await finish_event(data)
            elif scenario == 'death':
                assert data['event']['options'][0]['lethal_warning'], data
                data = await choose(data, 0)
                assert data['transition']['stop_reason'] == 'run_lost' and not data['available_actions'], data
                await capture('death')
            elif scenario == 'rescue':
                assert data['event']['options'][0]['lethal_warning'], data
                data = await choose(data, 0)
                assert data['transition']['stop_reason'] == 'action_completed' and data['top_bar']['hp'] > 0, data
                assert (await check())['potions'][0] is None
                await capture('rescued')
            elif scenario in {'upgrade', 'transform', 'enchant', 'remove', 'grid', 'cheese', 'wood', 'sapphire', 'symbiote'}:
                index = 1 if scenario in {'upgrade', 'remove', 'sapphire'} else 0
                data = await choose(data, index)
                assert data['transition']['stop_reason'] == 'choice_required', data
                assert data['event']['status'] == 'covered', data
                await call('inspect_selection'); await capture('selection')
                data = await finish_selection(data)
                after = await check()
                if scenario == 'upgrade': assert after['upgrades'] == before['upgrades'] + 1, after
                if scenario == 'enchant': assert after['enchantments'] == before['enchantments'] + 1, after
                await finish_event(data)
            elif scenario == 'locked':
                locked = next(o for o in data['event']['options'] if not o['enabled'])
                await call('choose_event_option', {'option_id': locked['id']}, error='illegal_action')
            elif scenario == 'upgrade_cancel':
                data = await choose(data, 1)
                assert not any(o['id'] == 'cancel' and o['enabled'] for o in data['selection']['options']), data
                card_id = data['selection']['cards'][0]['id']
                data = await observe_after_action(call, await call('select_card', {'card_id': card_id}))
                assert any(o['id'] == 'cancel_preview' and o['enabled'] for o in data['selection']['options']), data
                data = await observe_after_action(call, await call('selection_option', {'option_id': 'cancel_preview'}))
                assert data['selection']['selected_ids'] == [] and data['selection']['upgrade_previews'] == [], data
                assert (await check())['upgrades'] == before['upgrades']
                data = await finish_selection(data)
                await finish_event(data)
            elif scenario == 'trial':
                data = await choose(data, 1)
                assert len(data['event']['options']) == 2 and data['event']['proceed'] is None, data
                assert data['event']['options'][1]['lethal_warning'], data
                data = await choose(data, 1)
                assert data['transition']['stop_reason'] == 'action_completed' and data['available_actions'] == ['respond_to_confirmation'], data
                await capture('confirmation')
                data = await observe_after_action(call, await call('respond_to_confirmation', {'option': 'cancel'}))
                assert data['event']['status'] == 'visible' and data['confirmation'] is None, data
            elif scenario == 'crystal':
                data = await choose(data, 0)
                assert data['transition']['stop_reason'] == 'action_completed' and data['event']['status'] == 'covered', data
                assert data['divination']['phase'] == 'playing' and 'divine' in data['available_actions'], data
                await capture('divination')
            elif scenario in {'dense', 'dense_choice', 'lantern', 'dummy1', 'dummy2', 'dummy3'}:
                data = await choose(data, int(scenario[-1]) - 1 if scenario.startswith('dummy') else 1)
                if scenario in {'dense', 'dense_choice', 'lantern'}:
                    assert data['scene'] == 'event' and len(data['event']['options']) == 1, data
                    data = await choose(data, 0)
                entry_events = data['transition']['events']
                if scenario == 'dense_choice':
                    assert data['scene'] == 'combat' and data['transition']['stop_reason'] == 'choice_required', data
                    await capture('first-turn-selection')
                    data = await finish_selection(data)
                assert data['scene'] == 'combat' and data['transition']['stop_reason'] == 'player_ready', data
                assert any(e['type'] == 'card_drawn' for e in entry_events), entry_events
                await capture('combat')
                prepared = await asyncio.to_thread(raw.call, 'prepare_test_event_victory'); assert prepared['ok'], prepared
                data = await call('get_observation')
                card = next(c for c in data['player']['hand'] if c['name'] == 'Thunderclap')
                data = await observe_after_action(call, await call('play_card', {'card_id': card['id']}))
                if data['transition']['stop_reason'] == 'player_ready':
                    attack = next(c for c in data['player']['hand'] if c['name'] in {'Strike', 'Bash'})
                    targets = await call('inspect_targets', {'card_id': attack['id']})
                    data = await observe_after_action(call, await call('play_card', {'card_id': attack['id'], 'target_id': targets['targets'][0]['id']}))
                assert data['transition']['stop_reason'] == 'combat_won', data
                # Some event encounters resume immediately instead of offering ordinary combat loot.
                for _ in range(100):
                    data = await call('get_observation')
                    if data['scene'] in {'rewards', 'event'} and 'proceed' in data['available_actions']: break
                    await asyncio.sleep(.1)
                if scenario.startswith('dummy'):
                    if scenario == 'dummy1':
                        assert data['scene'] == 'rewards' and data['rewards']['status'] == 'visible', data
                        pending = await check()
                        assert pending['room_count'] == 1 and pending['pending'], pending
                        assert len(data['rewards']['items']) == 1 and data['rewards']['items'][0]['type'] == 'potion', data
                        data = await observe_after_action(call, await call('claim_reward', {'reward_id': data['rewards']['items'][0]['id']}))
                        assert (await check())['potions'][0] is not None
                    if scenario == 'dummy2': assert (await check())['upgrades'] == before['upgrades'] + 2
                    if scenario == 'dummy3': assert len((await check())['relics']) == len(before['relics']) + 1
                    await finish_event(data)
                else:
                    if scenario == 'lantern':
                        details = await call('inspect_rewards')
                        key = next(i for i in details['rewards']['items'] if i['type'] == 'special_card')
                        data = await observe_after_action(call, await call('claim_reward', {'reward_id': key['id']}))
                        if data.get('selection'): data = await finish_selection(data)
                        assert (await check())['deck_count'] == before['deck_count'] + 1
                    data = await observe_after_action(call, await call('proceed'))
                    assert data['screen']['view'] == 'map' and data['transition']['stop_reason'] == 'action_completed', data
            elif scenario in {'reward', 'potions', 'future_potions'}:
                data = await choose(data, 1 if scenario == 'reward' else 0)
                assert data['scene'] == 'rewards', data
                if scenario == 'potions':
                    assert len(data['rewards']['items']) == 3 and 'discard_potion' in data['available_actions'], data
                    data = await observe_after_action(call, await call('discard_potion', {'potion_slot': 0}))
                item = data['rewards']['items'][0]
                data = await observe_after_action(call, await call('claim_reward', {'reward_id': item['id']}))
                if data.get('selection'):
                    data = await finish_selection(data)
                if data['scene'] == 'rewards' and data['rewards']['status'] == 'visible': data = await observe_after_action(call, await call('proceed'))
                await finish_event(data)
            elif scenario == 'trial_story':
                data = await choose(data, 0)
                inspected = await call('inspect_event'); assert inspected['event']['description'], inspected
                data = await choose(data, 0)
                if data.get('selection'): data = await finish_selection(data)
                if data['scene'] == 'rewards': data = await observe_after_action(call, await call('proceed'))
                detail = await call('inspect_event')
                assert not re.search('[\u4e00-\u9fff]', json.dumps(detail, ensure_ascii=False)), detail
                await finish_event(data)
            elif scenario == 'reflections':
                data = await choose(data, 1)
                assert (await check())['deck_count'] == before['deck_count'] * 2 + 1
                await finish_event(data)
            elif scenario == 'repy':
                data = await choose(data, 1)
                assert data['scene'] == 'rewards' and len(data['rewards']['items']) == 4, data
                assert (await check())['deck_count'] == before['deck_count'] - 1
                data = await observe_after_action(call, await call('proceed'))
                await finish_event(data)
            elif scenario == 'doll':
                data = await choose(data, 2)
                detail = await call('inspect_event')
                assert not re.search('[\u4e00-\u9fff]', json.dumps(detail, ensure_ascii=False)), detail
                data = await choose(data, 0); await finish_event(data)
            elif scenario in {'relic_trader', 'tea', 'conveyor', 'slippery'}:
                data = await choose(data, 0)
                detail = await call('inspect_event')
                assert not re.search('[\u4e00-\u9fff]', json.dumps(detail, ensure_ascii=False)), detail
                await capture('after-choice')
                if data['event']['proceed']: await finish_event(data)
    print('PASS: event', args.scenario)


def main():
    parser = argparse.ArgumentParser(description='验证 --event-scenario 隔离图形实例的事件工具。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
