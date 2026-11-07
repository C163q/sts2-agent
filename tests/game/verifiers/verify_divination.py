from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from tests.game.support.verification_actions import observe_after_action
import argparse
import asyncio
import base64
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client


async def verify(args):
    root = ROOT
    report = args.report.resolve(); report.parent.mkdir(parents=True, exist_ok=True)
    captures = report.with_suffix(''); captures.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json'); config.write_text('{"screenshots":{"enabled":false}}')
    raw = Client(root / '.tmp/roundtrip/ipc')
    initial = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while initial['state']['scene'] == 'unrecognized' and time.monotonic() < deadline:
        await asyncio.sleep(.1); initial = await asyncio.to_thread(raw.call, 'get_state')
    assert initial['state']['scene'] == 'main_menu', initial
    started = await asyncio.to_thread(raw.call, 'start_test_combat', initial['state']['snapshot_id'])
    assert started['ok'], started
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[str(root / 'scripts/mcp_server.py'),
        '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(name, arguments=None, *, error=None):
                params = {'include_image': True, **(arguments or {})} if name == 'inspect_event' else arguments or {}
                response = await session.call_tool(name, full_output_arguments(name, params))
                data = response.structuredContent
                assert data == json.loads(response.content[0].text), response
                images = [c for c in response.content if c.type == 'image']
                if name == 'inspect_event' and (data.get('divination') or {}).get('status') == 'visible':
                    assert len(images) == 1 and images[0].mimeType == 'image/png', data
                    (captures / f'{len(evidence):02}-{name}.png').write_bytes(base64.b64decode(images[0].data))
                else: assert not images, data
                assert 'png_base64' not in response.content[0].text
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert data.get('error', {}).get('code') == error, data
                else: assert 'error' not in data, data
                return data

            data = await call('get_observation')
            data = await observe_after_action(call, await call('choose_event_option', {'option_id': data['event']['options'][args.option]['id']}))
            assert data['transition']['stop_reason'] == 'action_completed', data
            assert data['divination']['remaining'] == (3 if args.option == 0 else 6), data
            assert data['divination']['tool'] == 'big' and data['divination']['phase'] == 'playing', data
            initial_rows = data['divination']['grid']['cell_rows']
            if args.scenario == 'delayed': await asyncio.sleep(4)
            if args.scenario == 'map':
                await call('inspect_map')
                covered = await call('get_observation')
                assert covered['divination']['status'] == 'covered' and covered['divination']['grid'] is None, covered
                await call('close_map'); data = await call('get_observation')
            inspected = await call('inspect_event')
            assert inspected['divination']['phase'] == data['divination']['phase']
            assert inspected['divination']['grid']['cell_rows'] == data['divination']['grid']['cell_rows']
            await call('set_divination_tool', {'tool': 'small'})
            data = await call('get_observation')
            assert data['divination']['tool'] == 'small', data
            data = await observe_after_action(call, await call('divine', {'x': 5, 'y': 5}))
            geometry = await asyncio.to_thread(raw.call, 'check_test_divination')
            (captures / 'native-check.json').write_text(json.dumps(geometry, indent=2))
            full = await asyncio.to_thread(raw.call, 'capture_screenshot')
            (captures / 'center-full.png').write_bytes(base64.b64decode(full['state']['png_base64']))
            assert geometry['state']['center_border'], geometry
            expected = [''.join('#' if c == '#' else '.' for c in row) for row in initial_rows]; expected[5] = expected[5][:5] + '.' + expected[5][6:]
            assert [''.join('#' if c == '#' else '.' for c in row) for row in data['divination']['grid']['cell_rows']] == expected, data
            assert data['divination']['remaining'] == (2 if args.option == 0 else 5), data
            await call('divine', {'x': 5, 'y': 5}, error='illegal_action')
            data = await call('get_observation')
            await call('set_divination_tool', {'tool': 'big'})
            data = await call('get_observation')
            if args.scenario in {'curse', 'rewards', 'full', 'relic'}:
                kind = {'curse': 'CrystalSphereCurse', 'rewards': 'CrystalSpherePotion', 'full': 'CrystalSpherePotion', 'relic': 'CrystalSphereRelic'}[args.scenario]
                item = next(i for i in geometry['state']['items'] if i['kind'] == kind)
                planned = [(item['x'] + item['width'] // 2, item['y'] + item['height'] // 2)]
                if args.scenario in {'rewards', 'full'}:
                    card = next(i for i in geometry['state']['items'] if i['kind'] == 'CrystalSphereCardReward')
                    planned.append((card['x'] + 1, card['y'] + 1))
                if args.scenario == 'relic':
                    planned = [(item['x'] + dx, item['y'] + dy) for dy in (1, 3) for dx in (1, 3)]
            else: planned = [(0, 5), (8, 8), (3, 3), (8, 2), (3, 8)]
            had_rewards = False
            reward_types = set()
            while data.get('divination', {}).get('phase') == 'playing':
                rows = data['divination']['grid']['cell_rows']
                while planned and (not 0 <= planned[0][0] <= 10 or not 0 <= planned[0][1] <= 10 or rows[planned[0][1]][planned[0][0]] != '#'):
                    planned.pop(0)
                x, y = planned.pop(0) if planned else next((x,y) for y,row in enumerate(rows) for x,c in enumerate(row) if c == '#')
                before_rows = rows
                data = await observe_after_action(call, await call('divine', {'x': x, 'y': y}))
                assert data['transition']['complete'], data
                if (data.get('divination') or {}).get('status') == 'visible':
                    expected_rows = [''.join('.' if abs(cx-x) <= 1 and abs(cy-y) <= 1 or c != '#' else '#' for cx,c in enumerate(row)) for cy,row in enumerate(before_rows)]
                    assert [''.join('#' if c == '#' else '.' for c in row) for row in data['divination']['grid']['cell_rows']] == expected_rows, data
                if (data.get('divination') or {}).get('phase') == 'finished': break
                while data['scene'] == 'rewards':
                    had_rewards = True
                    if args.scenario == 'full':
                        potion = next(r for r in data['rewards']['items'] if r['type'] == 'potion')
                        data = await observe_after_action(call, await call('claim_reward', {'reward_id': potion['id']}))
                        assert data['reward_result']['status'] == 'not_claimed', data
                        data = await observe_after_action(call, await call('discard_potion', {'potion_slot': 0}))
                        data = await observe_after_action(call, await call('claim_reward', {'reward_id': potion['id']}))
                        assert data['reward_result']['status'] == 'claimed', data
                        reward_types.add('potion')
                    attempted = set()
                    while args.scenario in {'rewards', 'full'} and data['scene'] == 'rewards' and data['rewards']['items']:
                        candidates = [r for r in data['rewards']['items'] if r['id'] not in attempted]
                        if not candidates: break
                        reward = candidates[0]; attempted.add(reward['id'])
                        reward_types.add(reward['type'])
                        data = await observe_after_action(call, await call('claim_reward', {'reward_id': reward['id']}))
                        if (data.get('selection') or {}).get('status') == 'visible':
                            skip = next(o for o in data['selection']['options'] if o['enabled'] and o['id'] == 'skip')
                            data = await observe_after_action(call, await call('selection_option', {'option_id': skip['id']}))
                    if data['scene'] != 'rewards': break
                    data = await observe_after_action(call, await call('proceed'))
            assert data['divination']['phase'] == 'finished' and 'proceed' in data['available_actions'], data
            if args.scenario in {'rewards', 'full', 'relic'}: assert had_rewards, data
            if args.scenario in {'rewards', 'full'}: assert {'card', 'potion'} <= reward_types, reward_types
            if args.scenario == 'curse':
                after = await asyncio.to_thread(raw.call, 'check_test_divination')
                assert after['state']['deck'].count('DOUBT') == geometry['state']['deck'].count('DOUBT') + 1, after
            if args.scenario == 'delayed': await asyncio.sleep(4)
            data = await observe_after_action(call, await call('proceed'))
            assert data['screen']['view'] == 'map', data
            assert (await call('inspect_map'))['can_travel'], data
    print(f'PASS: divination option {args.option}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--option', type=int, choices=(0, 1), default=0)
    parser.add_argument('--scenario', choices=('basic', 'map', 'curse', 'rewards', 'full', 'relic', 'delayed'), default='basic')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
