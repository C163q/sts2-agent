from verification_actions import observe_after_action
from available_tools import GAME_ACTIONS
import argparse
import asyncio
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    if report.exists():
        raise RuntimeError('Use a new report path for each isolated run.')
    report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(root / '.tmp/roundtrip/ipc')
    initial = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while initial['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        initial = await asyncio.to_thread(raw.call, 'get_state')
    assert initial['state']['scene'] == 'main_menu', 'Requires a fresh isolated navigation instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', initial['state']['snapshot_id'])
    assert created['ok'], created
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                assert data == json.loads(response.content[0].text), response
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error:
                    assert data.get('error', {}).get('code') == error, data
                else:
                    assert 'error' not in data, data
                return data

            async def native(operation, arguments=None, token=None, error=None):
                response = await asyncio.to_thread(raw.call, operation, token, arguments=arguments)
                evidence.append({'native_test': operation, 'result': response})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error:
                    assert response.get('error', {}).get('code') == error, response
                else:
                    assert response['ok'], response
                return response.get('state')

            async def capture(name):
                return await call('capture_screenshot', {'filename': name + '.png'})

            def completed(data, reason='action_completed'):
                assert data['transition']['complete'] and data['transition']['stop_reason'] == reason, data

            data = await call('get_observation')
            await capture('01-before')
            assert data['scene'] == 'rewards', data
            old_token = (await native('get_state'))['snapshot_id']
            if args.scenario in {'boss1', 'boss2', 'boss3', 'double'}:
                data = await observe_after_action(call, await call('proceed'))
                if args.scenario == 'boss3':
                    completed(data)
                    assert data['scene'] == 'epilogue' and data['available_actions'] and data.get('map') is None, data
                    assert (await native('check_test_navigation'))['event'] == 'THE_ARCHITECT'
                    await capture('02-architect')
                    print('PASS boss3 terminal boundary'); return
                completed(data)
                await capture('02-after-proceed')
                expected = 1 if args.scenario == 'double' else int(args.scenario[-1]) + 1
                assert data['map']['act'] == expected, data
                assert set(data['available_actions']) & GAME_ACTIONS == {'travel_to_node'}, data
                await native('travel_to_node', {'node_id': data['map']['selectable_nodes'][0]}, old_token, 'stale_state')
                target = data['map']['selectable_nodes'][0]
                if args.scenario != 'double':
                    await call('travel_to_node', {'node_id': 'map:1:1:2'}, error='illegal_action')
                    await call('get_observation')
                data = await observe_after_action(call, await call('travel_to_node', {'node_id': target}))
                if args.scenario == 'double':
                    completed(data, 'player_ready')
                    assert data['scene'] == 'combat', data
                    await native('finish_test_navigation_boss')
                    await call('get_observation')
                    data = await observe_after_action(call, await call('proceed'))
                    completed(data)
                    assert data['map']['act'] == 2, data
                else:
                    completed(data)
                    assert data['scene'] == 'ancient', data
                await capture('03-destination')
                print('PASS', args.scenario); return

            inspected = await call('inspect_map')
            await call('travel_to_node', {'node_id': inspected['selectable_nodes'][0]}, error='observation_required')
            data = await call('get_observation')
            assert data.get('map') is not None, 'Missing get_observation map summary.'
            assert data['screen'] == {'status': 'visible', 'view': 'map'}, data
            assert data['map']['selectable_nodes'] == inspected['selectable_nodes'], data
            assert data['rewards']['status'] == 'covered', data
            assert set(data['available_actions']) & GAME_ACTIONS == {'travel_to_node'}, data
            state = await native('check_test_navigation')
            source = next(n for n in inspected['nodes'] if n['id'] == inspected['current_node'])
            connected = source['next']
            target = next((n for n in inspected['selectable_nodes'] if n not in connected), None) if args.scenario == 'flight' else connected[0]
            assert target, inspected
            token = (await native('get_state'))['snapshot_id']
            for arguments in ({}, [], False, {'node_id': True}, {'node_id': 'map:01:2:1'}, {'node_id': target, 'force': True}):
                await native('travel_to_node', arguments, token, 'invalid_request')
            await call('travel_to_node', {'node_id': inspected['current_node']}, error='illegal_action')
            await call('get_observation')
            if args.scenario == 'basic':
                await native('set_test_navigation_drawing')
                await call('travel_to_node', {'node_id': target}, error='stale_state')
                data = await call('get_observation')
                assert data['map']['selectable_nodes'] == [] and 'travel_to_node' not in data['available_actions'], data
                await call('travel_to_node', {'node_id': target}, error='illegal_action')
                await native('clear_test_navigation_drawing')
                await call('get_observation')
                await call('close_map')
                await call('travel_to_node', {'node_id': target}, error='observation_required')
                await call('get_observation')
                await call('travel_to_node', {'node_id': target}, error='illegal_action')
                await call('inspect_map')
                await call('get_observation')
                await native('scroll_test_navigation')
            await capture('02-map')
            data = await observe_after_action(call, await call('travel_to_node', {'node_id': target}))
            if args.scenario == 'choice':
                completed(data, 'choice_required')
                assert data['selection']['status'] == 'visible', data
                await capture('03-selection')
                data = await observe_after_action(call, await call('select_card', {'card_id': data['selection']['cards'][0]['id']}))
                if data.get('selection'):
                    button = next(o for o in data['selection']['options'] if o['enabled'])
                    data = await observe_after_action(call, await call('selection_option', {'option_id': button['id']}))
                completed(data, 'player_ready')
            elif args.scenario == 'combat':
                completed(data, 'player_ready')
                assert data['scene'] == 'combat' and data['turn'] == 1, data
            else:
                completed(data)
                assert data['scene'] in {'rest_site', 'treasure', 'shop', 'event'}, data
            await capture('04-destination')
            after = await native('check_test_navigation')
            assert after['current_node'] == target and after['gold'] == state['gold'], (state, after)
            assert after['rewards'] is False, after
            assert after['boots_used'] == (3 if args.scenario == 'flight' else state['boots_used']), after
            if args.scenario in {'basic', 'flight'}:
                data = await observe_after_action(call, await call('choose_rest_option', {'option_id': 'HEAL'}))
                completed(data)
                data = await observe_after_action(call, await call('proceed'))
                completed(data)
                assert data['map']['current_node'] == target, data
                if args.scenario == 'flight':
                    graph = await call('inspect_map')
                    current = next(n for n in graph['nodes'] if n['id'] == target)
                    assert graph['selectable_nodes'] == current['next'], graph
                    forbidden = next(n['id'] for n in graph['nodes'] if n['row'] == current['row'] + 1 and n['id'] not in current['next'])
                    await call('get_observation')
                    await call('travel_to_node', {'node_id': forbidden}, error='illegal_action')
            print('PASS', args.scenario, len(evidence), 'calls')


def main():
    parser = argparse.ArgumentParser(description='隔离实例原生选路与跨幕图形验证')
    parser.add_argument('--scenario', required=True, choices=['basic', 'flight', 'combat', 'choice', 'shop', 'treasure', 'unknown', 'boss1', 'boss2', 'boss3', 'double'])
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
