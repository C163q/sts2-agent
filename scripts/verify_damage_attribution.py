"""Verify direct damage and native death cleanup through real MCP."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client
from verification_runtime import ensure_run, ipc_directory


async def verify_fog(call, native_call, scenario):
    state = await call('get_observation')
    leader = next(enemy for enemy in state['enemies'] if enemy['name'] == 'Living Fog')
    if scenario in {'fog_natural', 'fog_thorns'}:
        for _ in range(2):
            receipt = await call('end_turn')
            assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'player_ready', receipt
        state = await call('get_observation')
    bomb = next(enemy for enemy in state['enemies'] if enemy['id'] != leader['id'])
    assert bomb['intents'] == [{'category': 'death_blow', 'value': '8'}], bomb
    details = await call('inspect_combatants')
    index = next(i for i, enemy in enumerate(details['enemies']) if enemy['id'] == bomb['id'])
    tips = [tip for tip in details['hover_tips'] if f'enemies.{index}.intents.0' in tip['sources']]
    assert len(tips) == 1 and '8' in tips[0]['description'], tips
    native = await native_call('capture_test_gas_bomb_intent')
    english = next(item for item in native['results'] if item['locale'] == 'eng')
    assert english['tip'] == {key: tips[0][key] for key in ('title', 'description')}, native
    assert english['intent'] == bomb['intents'][0], native
    # Native hover and locale changes are read-only diagnostics; refresh permission after restoring them.
    await call('inspect_combatants')
    await call('capture_screenshot', {'filename': 'bomb-intent.png'})
    if scenario in {'fog_card', 'fog_cleanup'}:
        strike = next(card for card in state['player']['hand'] if card['name'] == 'Strike')
        target = bomb if scenario == 'fog_card' else leader
        receipt = await call('play_card', {'card_id': strike['id'], 'target_id': target['id']})
    else:
        receipt = await call('end_turn')
    transition = receipt['transition']
    assert transition['complete'] and transition['stop_reason'] == (
        'combat_won' if scenario == 'fog_cleanup' else 'player_ready'), receipt
    events = transition['events']
    deaths = [event for event in events if event['type'] == 'died' and event['target']['id'] == bomb['id']]
    assert len(deaths) == 1, events
    source = ({'kind': 'card', 'name': 'Strike'} if scenario == 'fog_card' else
              {'kind': 'power', 'name': 'Thorns'} if scenario == 'fog_thorns' else None)
    assert deaths[0].get('source') == source, deaths
    hits = [event for event in events if event['type'] == 'damage' and event['target']['id'] == bomb['id']]
    if source:
        assert len(hits) == 1 and hits[0].get('source') == source, hits
    else:
        assert not hits, hits
    if scenario in {'fog_natural', 'fog_thorns'}:
        attacks = [event for event in events if event['type'] == 'damage' and event.get('actor', {}).get('id') == bomb['id']]
        assert len(attacks) == 1 and attacks[0]['target']['kind'] == 'player' and attacks[0]['hp_loss'] == 8, events
        assert attacks[0].get('source') is None, attacks
    await call('capture_screenshot', {'filename': 'bomb-after.png'})
    state = await call('get_observation')
    if scenario == 'fog_cleanup':
        assert state['scene'] == 'rewards' and state['enemies'] is None, state
    else:
        assert all(enemy['id'] != bomb['id'] for enemy in state['enemies']), state


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
        'directory': str(args.report.with_suffix(''))}}))
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name('mcp_server.py')),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert not reply.isError and 'error' not in data, data
                assert data == json.loads(reply.content[0].text), reply
                return data

            async def native_call(name):
                reply = await asyncio.to_thread(raw.call, name)
                evidence.append({'native_check': name, 'result': reply})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert reply['ok'], reply
                return reply['state']

            if args.scenario == 'revival':
                checks = await native_call('check_test_death_notifications')
                assert checks['passed'], checks
                print('PASS repeated death notifications, native revival and journal renewal')
                return
            if args.scenario.startswith('fog_'):
                await verify_fog(call, native_call, args.scenario)
                print(f'PASS gas bomb intent, damage and death attribution: {args.scenario}')
                return
            state = await call('get_observation')
            leader = next(enemy for enemy in state['enemies'] if enemy['name'] == 'The Obscura')
            minion = next(enemy for enemy in state['enemies'] if enemy['name'] == 'Parafright')
            await call('inspect_combatants')
            await call('capture_screenshot', {'filename': 'before.png'})
            if args.scenario == 'doom':
                receipt = await call('end_turn')
                source = {'kind': 'power', 'name': 'Doom'}
            elif args.scenario == 'potion':
                receipt = await call('use_potion', {'potion_slot': 0, 'target_id': leader['id']})
                source = {'kind': 'potion', 'name': 'Fire Potion'}
            else:
                name = 'Anger+' if args.scenario == 'card' else 'Thunderclap'
                card = next(card for card in state['player']['hand'] if card['name'] == name)
                await call('inspect_hand', {'card_ids': [card['id']]})
                arguments = {'card_id': card['id']}
                if args.scenario == 'card':
                    arguments['target_id'] = leader['id']
                receipt = await call('play_card', arguments)
                source = {'kind': 'card', 'name': name}
            transition = receipt['transition']
            assert transition['complete'] and transition['stop_reason'] == 'combat_won', receipt
            events = transition['events']
            for victim in (leader, minion):
                deaths = [event for event in events if event['type'] == 'died'
                          and event['target']['id'] == victim['id']]
                assert len(deaths) == 1, events
                expected = source if victim is leader or args.scenario == 'aoe_lethal' else None
                assert deaths[0].get('source') == expected, deaths
            damage = [event for event in events if event['type'] == 'damage' and event['target']['kind'] == 'enemy']
            assert all(event.get('source') == source for event in damage), damage
            if args.scenario == 'doom':
                assert not damage, damage
                assert all(event.get('source') is None for event in events if event['type'] == 'died'
                           and event['target']['id'] != leader['id']), events
            else:
                hits = [event for event in damage if event['target']['id'] == leader['id']]
                assert len(hits) == 1 and hits[0]['hp_loss'] == 3, damage
                hits = [event for event in damage if event['target']['id'] == minion['id']]
                if args.scenario.startswith('aoe'):
                    assert len(hits) == 1 and hits[0]['hp_loss'] == (3 if args.scenario == 'aoe_lethal' else 4), damage
                else:
                    assert not hits, damage
            await call('capture_screenshot', {'filename': 'after.png'})
            state = await call('get_observation')
            assert state['scene'] == 'rewards', state
    print(f'PASS direct damage and minion cleanup attribution: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['card', 'aoe', 'aoe_lethal', 'doom', 'potion',
        'fog_natural', 'fog_card', 'fog_cleanup', 'fog_thorns', 'revival'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
