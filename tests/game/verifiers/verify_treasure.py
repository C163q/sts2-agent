from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from tests.game.support.verification_runtime import ensure_run, ipc_directory
from tests.game.support.verification_actions import observe_after_action
from sts2_mcp.output.available_tools import GAME_ACTIONS
import argparse
import sys
import asyncio
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_actions import confirm_transform


async def verify(args):
    root = ROOT
    report = args.report.resolve()
    if report.exists() or report.with_suffix('').exists(): raise RuntimeError('Evidence paths must be new.')
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.with_suffix(''))}}))
    raw = Client(ipc_directory())
    created = await asyncio.to_thread(ensure_run, raw)
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(ipc_directory()), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = response.structuredContent
                assert data == json.loads(response.content[0].text)
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error: assert data.get('error', {}).get('code') == error, data
                else: assert 'error' not in data, data
                return data

            async def fixture():
                result = await asyncio.to_thread(raw.call, 'check_test_treasure')
                assert result['ok'], result
                evidence.append({'fixture': result['state']})
                return result['state']

            def done(result):
                transition = result['transition']
                assert transition['stop_reason'] == 'action_completed' and transition['complete'], result
                assert [event['sequence'] for event in transition['events']] == list(range(1, len(transition['events']) + 1)), result

            await call('loot_treasure', error='observation_required')
            initial = await call('get_observation')
            assert initial['scene'] == 'treasure' and initial['treasure']['chest'] == 'closed', initial
            assert initial['treasure']['relic'] is None and set(initial['available_actions']) & GAME_ACTIONS == {'loot_treasure'}, initial
            details = await call('inspect_treasure')
            assert details['treasure']['relic'] is None, details
            await call('capture_screenshot', {'filename': 'initial.png'})
            before = await fixture()
            await call('proceed', error='illegal_action')
            await call('get_observation')
            if args.scenario == 'basic':
                await call('inspect_map')
                covered = await call('get_observation')
                assert covered['treasure'] == {'status': 'covered', 'chest': None, 'relic': None, 'proceed': None}, covered
                rejected = await call('inspect_treasure', error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('loot_treasure', error='illegal_action')
                await call('close_map')
                result = await observe_after_action(call, await call('loot_treasure')); done(result)
                assert any(event['type'] == 'relic_obtained' for event in result['transition']['events']), result
            elif args.scenario in {'open', 'skip'}:
                result = await observe_after_action(call, await call('loot_treasure', {'open_only': True})); done(result)
                assert result['treasure']['relic'] == {'name': 'Anchor', 'enabled': True}, result
                assert result['treasure']['proceed']['skips_remaining'], result
                opened = await fixture()
                assert opened['relics'] == before['relics'] and opened['gold'] > before['gold'], opened
                details = await call('inspect_treasure')
                assert '10' in details['treasure']['relic']['description'], details
                await call('capture_screenshot', {'filename': 'open.png'})
                if args.scenario == 'skip':
                    result = await observe_after_action(call, await call('proceed')); done(result)
                    assert result['screen']['view'] == 'map', result
                    assert (await fixture())['relics'] == before['relics']
                    report.write_text(json.dumps(evidence, indent=2) + '\n')
                    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')
                    return
                await call('loot_treasure', {'open_only': True}, error='illegal_action')
                await call('get_observation')
                result = await observe_after_action(call, await call('loot_treasure')); done(result)
            else:
                result = await observe_after_action(call, await call('loot_treasure'))
                if args.scenario == 'choice':
                    result = await confirm_transform(call, result)
                    assert result['scene'] == 'treasure' and result['treasure']['relic'] is None, result
                    await call('capture_screenshot', {'filename': 'transformed.png'})
                    result = await observe_after_action(call, await call('proceed')); done(result)
                    report.write_text(json.dumps(evidence, indent=2) + '\n')
                    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')
                    return
                done(result)
                if args.scenario == 'extra':
                    assert result['scene'] == 'rewards' and result['treasure']['status'] == 'covered', result
                    assert (await fixture())['relics'] == before['relics'], 'Claimed a relic behind extra rewards.'
                    await call('capture_screenshot', {'filename': 'extra.png'})
                    rewards = (await call('inspect_rewards'))['rewards']['items']
                    result = await observe_after_action(call, await call('claim_reward', {'reward_id': rewards[0]['id']}))
                    if result['scene'] == 'rewards': result = await observe_after_action(call, await call('proceed'))
                    done(result)
                    assert result['treasure']['relic']['name'] == 'Anchor', result
                    result = await observe_after_action(call, await call('loot_treasure')); done(result)
                if args.scenario == 'nested':
                    assert result['scene'] == 'rewards' and result['treasure']['status'] == 'covered', result
                    await call('capture_screenshot', {'filename': 'nested.png'})
                    assert (await call('inspect_rewards'))['rewards']['items'], result
                    result = await observe_after_action(call, await call('proceed')); done(result)
            after = await fixture()
            if args.scenario == 'map_pending':
                assert result['screen']['view'] == 'map', result
                assert after['delayed_done'] and not after['obtaining'], after
                await call('capture_screenshot', {'filename': 'map-settled.png'})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')
                return
            assert result['scene'] == 'treasure' and result['treasure']['chest'] == 'open', result
            assert result['treasure']['relic'] is None and set(result['available_actions']) & GAME_ACTIONS == {'proceed'}, result
            assert result['treasure']['proceed']['enabled'] and not result['treasure']['proceed']['skips_remaining'], result
            assert not after['obtaining'] and not after['preview_cards'], after
            if args.scenario == 'empty':
                assert after['relics'] == before['relics'] and after['gold'] == before['gold'], after
                assert after['crucible_rooms'] == 1, after
            else:
                assert after['gold'] > before['gold'], after
                assert ('CALLING_BELL' if args.scenario == 'nested' else 'ANCHOR') in after['relics'], after
            await call('capture_screenshot', {'filename': 'collected.png'})
            stable = await call('get_observation')
            assert stable['top_bar'] == result['top_bar'] and stable['treasure'] == result['treasure'], stable
            await call('loot_treasure', error='illegal_action')
            await call('get_observation')
            result = await observe_after_action(call, await call('proceed')); done(result)
            assert result['screen']['view'] == 'map' and result['treasure']['status'] == 'covered', result
    report.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')


def main():
    parser = argparse.ArgumentParser(description='通过真实 MCP 验证隔离图形实例的宝箱房。')
    parser.add_argument('--scenario', required=True, choices=('basic', 'open', 'skip', 'empty', 'nested', 'choice', 'extra', 'map_pending'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__': main()
