"""Keep browsable rows complete while preserving hidden-page boundaries."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.output.presets import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
        'directory': str(args.report.parent / 'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            def record(entry):
                evidence.append(entry)
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')

            async def call(tool, arguments=None):
                arguments = arguments or {}
                if tool != 'capture_screenshot':
                    arguments = {'preset': 'full', **arguments}
                reply = await session.call_tool(tool, arguments)
                result = reply.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert result == json.loads(reply.content[0].text)
                assert not reply.isError and 'error' not in result, (tool, result)
                return result

            async def native(operation):
                result = await asyncio.to_thread(raw.call, operation)
                record({'native': operation, 'result': result})
                assert result['ok'], result
                return result['state']

            async def capture(label):
                result = await call('get_observation')
                evidence[-1]['label'] = label
                await call('capture_screenshot', {'filename': label + '.png'})
                return result

            if args.scenario == 'audit':
                state = await capture('initial')
                await native('inspect_test_browsing_containers')
                if 'open_shop' in state['available_actions']:
                    await call('open_shop')
                    await capture('inventory')
                    await native('inspect_test_browsing_containers')
                elif state['scene'] == 'combat' and 'inspect_map' in state['available_actions']:
                    await call('inspect_map')
                    await capture('map')
                    await native('inspect_test_browsing_containers')
                    await call('inspect_deck')
                    await capture('deck')
                    await native('inspect_test_browsing_containers')
                    await call('close_card_view')
                    await call('close_map')
            elif args.scenario == 'rewards':
                first = await capture('complete-list')
                rows = first['rewards']['items']
                assert len(rows) == 6, rows
                assert [row['type'] for row in rows] == ['gold', 'gold', 'potion', 'relic', 'special_card', 'card']
                details = await call('inspect_rewards')
                assert rows == [{k: v for k, v in row.items() if k != 'hover_tips'}
                                for row in details['rewards']['items']]
                for preset in ('default', 'summary'):
                    compact = await call('get_observation', {'preset': preset})
                    assert compact['rewards'] == apply_preset(first, 'default')['rewards']
                checks = await native('check_test_browsable_content')
                assert checks['passed'], checks
                card = rows[-1]
                await call('claim_reward', {'reward_id': card['id']})
                choice = await capture('card-selection')
                assert choice['selection']['type'] == 'reward'
                assert choice['rewards'] == {'status': 'covered', 'title': None, 'items': None, 'proceed': None}
                await call('select_card', {'card_id': choice['selection']['cards'][0]['id']})
                returned = await capture('after-card')
                assert [r['id'] for r in returned['rewards']['items']] == [r['id'] for r in rows[:-1]]
                await call('inspect_map')
                covered = await capture('map')
                assert covered['rewards']['status'] == 'covered' and covered['rewards']['items'] is None
                await call('close_map')
                while True:
                    current = (await call('inspect_rewards'))['rewards']['items']
                    if not current:
                        break
                    await call('claim_reward', {'reward_id': current[0]['id']})
                assert (await capture('empty'))['rewards']['items'] == []
                await call('proceed')
            else:
                await call('get_observation')
                await call('proceed')
                for _ in range(12):
                    state = await call('get_observation')
                    if state['scene'] == 'run_result':
                        break
                    assert state['scene'] == 'epilogue', state
                    await call('advance_dialogue' if 'advance_dialogue' in state['available_actions'] else 'proceed')
                else:
                    raise AssertionError('The epilogue did not finish.')
                await native('prepare_test_browsable_result')
                await call('get_observation')
                await call('run_result_option', {'option_id': 'continue'})
                assert (await call('get_observation'))['run_result']['phase'] == 'summary'
                await native('prepare_test_browsable_history')
                first = await capture('history')
                assert first['run_result']['phase'] == 'history'
                checks = await native('check_test_browsable_content')
                assert checks['passed'], checks
                details = await call('inspect_run_result')
                assert details['run_result']['texts'] == first['run_result']['texts']
                assert len(details['run_result']['potions']) == 3
                assert len(details['run_result']['relics']) >= 1
                for preset in ('default', 'summary'):
                    compact = await call('get_observation', {'preset': preset})
                    assert compact['run_result'] == apply_preset(first, 'default')['run_result']
                assert (await call('get_observation')) == first
    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('rewards', 'history', 'audit'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
