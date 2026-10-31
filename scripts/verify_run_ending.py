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
    if report.exists(): raise RuntimeError('Use a fresh evidence path.')
    report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(root / '.tmp/roundtrip/ipc', timeout=70)
    initial = await asyncio.to_thread(raw.call, 'get_state')
    until = time.monotonic() + 30
    while initial['state']['scene'] != 'main_menu' and time.monotonic() < until:
        await asyncio.sleep(.1); initial = await asyncio.to_thread(raw.call, 'get_state')
    assert initial['state']['scene'] == 'main_menu', initial
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
                result = await session.call_tool(name, arguments or {})
                data = result.structuredContent
                assert data == json.loads(result.content[0].text)
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert data.get('error', {}).get('code') == error, data
                else: assert 'error' not in data, data
                return data
            async def capture(name): return await call('capture_screenshot', {'filename': name + '.png'})
            async def ready():
                deadline = time.monotonic() + 30
                while True:
                    data = await call('get_observation')
                    if set(data['available_actions']) & GAME_ACTIONS or data['scene'] == 'main_menu': return data
                    assert time.monotonic() < deadline, data
                    await asyncio.sleep(.25)
            def complete(data):
                assert data['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, data
            data = await ready()
            if args.scenario.startswith('victory'):
                assert data['scene'] == 'rewards', data
                data = await observe_after_action(call, await call('proceed')); complete(data)
                for index in range(10):
                    assert data['scene'] == 'epilogue', data
                    assert data['epilogue']['dialogue'], data
                    await capture(f'01-dialogue-{index}')
                    if 'advance_dialogue' in data['available_actions']:
                        previous = data['epilogue']['dialogue']
                        data = await observe_after_action(call, await call('advance_dialogue')); complete(data)
                        assert data['epilogue']['dialogue'] != previous, data
                    else:
                        assert set(data['available_actions']) & GAME_ACTIONS == {'proceed'}, data
                        data = await observe_after_action(call, await call('proceed')); complete(data)
                        break
                else: raise AssertionError('Dialogue failed to terminate.')
            elif args.scenario == 'event_death':
                assert data['scene'] == 'event', data
                option = next(o for o in data['event']['options'] if o['enabled'])
                data = await observe_after_action(call, await call('choose_event_option', {'option_id': option['id']}))
                assert data['transition']['complete'] and data['transition']['stop_reason'] == 'run_lost', data
                data = await ready()
            assert data['scene'] == 'run_result', data
            assert data['run_result']['phase'] == 'outcome', data
            assert bool('?' in (data['run_result']['title'] or '')) == args.scenario.startswith('victory'), data
            assert data['run_result']['score_lines'] == [] and data['run_result']['discoveries'] == [], data
            await capture('02-outcome')
            await call('inspect_run_result')
            await call('run_result_option', {'option_id': 'not_a_button'}, error='illegal_action')
            await call('get_observation')
            data = await observe_after_action(call, await call('run_result_option', {'option_id': 'continue'})); complete(data)
            assert data['run_result']['phase'] == 'summary', data
            assert data['run_result']['score_lines'], data
            assert any(t.startswith('[') and '/' in t and t.endswith(']') for t in data['run_result']['texts']), data
            await capture('03-summary')
            stable = await call('get_observation')
            assert data['run_result'] == stable['run_result'], (data, stable)
            details = await call('inspect_run_result')
            assert details['run_result']['hover_tips'] is not None, details
            if args.scenario.startswith('victory'):
                tip = next(t for t in details['run_result']['hover_tips'] if t['source'] == 'discovery:cards')
                assert tip['description'].endswith('....') and len(tip['description'].split('\n\n')[1].splitlines()) == 11, tip
                assert not any('\u4e00' <= c <= '\u9fff' for c in tip['description']), tip
            # Details retain the latest complete action observation.
            if any(o['id'] == 'view_run' and o['enabled'] for o in data['run_result']['options']):
                data = await observe_after_action(call, await call('run_result_option', {'option_id': 'view_run'})); complete(data)
                assert data['run_result']['phase'] == 'history', data
                await capture('04-history')
                data = await observe_after_action(call, await call('run_result_option', {'option_id': 'back'})); complete(data)
            data = await observe_after_action(call, await call('run_result_option', {'option_id': 'main_menu'})); complete(data)
            phases = []
            for index in range(35):
                if data['scene'] == 'main_menu': break
                assert data['scene'] == 'run_result', data
                phase = data['run_result']['phase']; phases.append(phase)
                await capture(f'05-unlock-{index}-{phase}')
                details = await call('inspect_run_result')
                assert not any('\u4e00' <= c <= '\u9fff' for c in json.dumps(details, ensure_ascii=False)), details
                enabled = [o for o in data['run_result']['options'] if o['enabled']]
                assert enabled, data
                if 'Cards Unlocked!' in data['run_result']['texts']:
                    assert len(data['run_result']['cards']) == 3, data
                    assert all(c.get('name') and c.get('description') for c in data['run_result']['cards']), data
                if phase == 'timeline':
                    expected = {o['id'] for o in data['run_result']['options'] if o['id'].startswith('epoch:')}
                    actual = {t['source'] for t in details['run_result']['hover_tips'] if t['source'].startswith('epoch:')}
                    assert expected <= actual, details
                option = next((o for o in enabled if o['id'] in {'continue', 'confirm', 'back'}), enabled[0])
                if args.external_back and option['id'] == 'back':
                    response = await asyncio.to_thread(raw.call, 'external_back_test_result')
                    assert response['ok'], response
                    assert (await call('get_observation'))['scene'] == 'main_menu'
                    response = await asyncio.to_thread(raw.call, 'reopen_test_timeline')
                    assert response['ok'], response
                    reopened = await call('get_observation')
                    assert reopened['scene'] == 'main_menu' and reopened.get('run_result') is None, reopened
                    await call('run_result_option', {'option_id': 'back'}, error='illegal_action')
                    response = await asyncio.to_thread(raw.call, 'close_test_timeline')
                    assert response['ok'], response
                    data = await call('get_observation')
                    break
                data = await observe_after_action(call, await call('run_result_option', {'option_id': option['id']})); complete(data)
            assert data['scene'] == 'main_menu' and data['available_actions'] == [], data
            await capture('06-main-menu')
            await call('run_result_option', {'option_id': 'continue'}, error='illegal_action' if args.external_back else 'observation_required')
            print(json.dumps({'scenario': args.scenario, 'calls': len(evidence), 'unlock_phases': phases, 'returned_to_menu': True}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--external-back', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
