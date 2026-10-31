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
    report = args.report.resolve(); report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    initial = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while initial['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1); initial = await asyncio.to_thread(raw.call, 'get_state')
    assert initial['state']['scene'] == 'main_menu', 'Requires a fresh isolated Trial instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', initial['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.version == '0.25.0'

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                assert data == json.loads(response.content[0].text), response
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert data.get('error', {}).get('code') == error, data
                else: assert 'error' not in data, data
                return data

            async def native(operation, *, error=None, token=None, arguments=None):
                result = await asyncio.to_thread(raw.call, operation, token, arguments=arguments)
                evidence.append({'native_test': operation, 'arguments': arguments, 'result': result})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert result.get('error', {}).get('code') == error, result
                else: assert result['ok'], result
                return result

            async def capture(filename):
                await call('capture_screenshot', {'filename': filename + '.png'})

            async def open_dialog(data):
                refusal = next(o for o in data['event']['options'] if o['lethal_warning'])
                data = await call('choose_event_option', {'option_id': refusal['id']})
                assert data['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, data
                assert data['screen'] == {'status': 'visible', 'view': 'confirmation'}, data
                assert data['confirmation']['type'] == 'abandon_run', data
                assert data['available_actions'] == ['respond_to_confirmation'], data
                assert data['event'] == {'status': 'covered', 'name': None, 'description': None, 'options': None, 'proceed': None}, data
                assert data['top_bar'] is None, data
                assert all(o['enabled'] for o in data['confirmation']['options']), data
                assert 'interaction' not in data.get('notes', {}), data
                return data

            data = await call('get_observation')
            assert data['scene'] == 'event' and data['confirmation'] is None, data
            # The fixture starts at the native initial Trial page; option 1 is its first refusal.
            data = await call('choose_event_option', {'option_id': data['event']['options'][1]['id']})
            assert any(o['lethal_warning'] for o in data['event']['options']), data
            await capture('01-event-refusal')
            data = await open_dialog(data)
            await capture('02-confirmation')

            if args.scenario == 'cancel':
                for name, arguments in [('inspect_event', {}), ('inspect_map', {}),
                                        ('use_potion', {'potion_slot': 0}), ('choose_event_option', {'option_id': 0})]:
                    await call(name, arguments, error='illegal_action')
                    data = await call('get_observation')
                token = (await native('get_state'))['state']['snapshot_id']
                for arguments in ({'option': True}, {'option': 'yes'}, {'option': 'cancel', 'extra': 1}, {}):
                    await native('respond_to_confirmation', token=token, arguments=arguments, error='invalid_request')
                before = await native('check_test_event')
                data = await call('respond_to_confirmation', {'option': 'cancel'})
                assert data['confirmation'] is None and data['event']['status'] == 'visible', data
                assert data['available_actions'] == ['choose_event_option'], data
                after = await native('check_test_event')
                assert before['state'] == after['state'], (before, after)
                await capture('03-cancelled')
                data = await open_dialog(data)
                old = (await native('get_state'))['state']['snapshot_id']
                await native('reopen_test_confirmation')
                fresh = (await native('get_state'))['state']['snapshot_id']
                assert old != fresh, 'External replacement must invalidate an otherwise identical popup.'
                await native('respond_to_confirmation', token=old, arguments={'option': 'confirm'}, error='stale_state')
                await call('respond_to_confirmation', {'option': 'cancel'}, error='stale_state')
                await call('get_observation')
                data = await call('respond_to_confirmation', {'option': 'cancel'})
                assert data['event']['status'] == 'visible', data
                # The same class opened outside Trial.DoubleDown must remain unsupported.
                await native('open_test_unowned_confirmation')
                data = await call('get_observation')
                assert data['confirmation'] is None and data['available_actions'] == [], data
                assert data['screen'] == {'status': 'covered', 'view': 'confirmation'}, data
                await capture('04-unowned')
                await call('respond_to_confirmation', {'option': 'confirm'}, error='illegal_action')
                await native('cancel_test_confirmation')
                data = await call('get_observation')
                assert data['confirmation'] is None and data['event']['status'] == 'visible', data
            elif args.scenario == 'confirm':
                await asyncio.sleep(4)
                data = await call('respond_to_confirmation', {'option': 'confirm'})
                assert data['transition']['complete'] and data['transition']['stop_reason'] == 'run_lost', data
                assert data['available_actions'] == [] and data['confirmation'] is None, data
                await capture('03-run-ended')
                truth = await native('check_test_confirmation')
                assert truth['state']['abandoned'] and truth['state']['ended'] and truth['state']['hp'] == 0, truth
                await call('respond_to_confirmation', {'option': 'confirm'}, error='observation_required')
    print('PASS: event confirmation ' + args.scenario)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('cancel', 'confirm'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
