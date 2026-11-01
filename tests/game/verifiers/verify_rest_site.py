from scripts._bootstrap import ROOT
from tests.game.support.verification_runtime import ensure_run, ipc_directory
from tests.game.support.verification_actions import observe_after_action
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
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(ipc_directory()), '--config', str(config)])
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
                else:
                    if 'error' in data:
                        diagnostic = await asyncio.to_thread(raw.call, 'get_state')
                        report.with_suffix('.diagnostic.json').write_text(json.dumps(diagnostic, indent=2) + '\n')
                    assert 'error' not in data, data
                return data

            async def fixture():
                result = await asyncio.to_thread(raw.call, 'check_test_rest_site')
                assert result['ok'], result
                evidence.append({'fixture': result['state']})
                return result['state']

            async def choose(option): return await observe_after_action(call, await call('choose_rest_option', {'option_id': option}))

            async def option(option): return await observe_after_action(call, await call('selection_option', {'option_id': option}))

            async def select(card): return await observe_after_action(call, await call('select_card', {'card_id': card['id']}))

            def done(result):
                assert result['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, result

            await call('choose_rest_option', {'option_id': 'HEAL'}, error='observation_required')
            initial = await call('get_observation')
            assert initial['scene'] == 'rest_site' and initial['rest_site']['status'] == 'visible', initial
            details = await call('inspect_rest_site')
            assert all('description' in r for r in details['rest_site']['options']), details
            await call('capture_screenshot', {'filename': 'initial.png'})
            before = await fixture()

            if args.scenario == 'basic':
                await call('inspect_map')
                covered = await call('get_observation')
                assert covered['rest_site'] == {'status': 'covered', 'prompt': None, 'description': None,
                                                'options': None, 'proceed': None}, covered
                await call('inspect_rest_site', error='illegal_action')
                await call('close_map')
                result = await choose('HEAL'); done(result)
                after = await fixture()
                assert after['hp'] == 54 and after['deck'] == before['deck'], after
                assert result['rest_site']['options'] == [] and result['rest_site']['proceed']['enabled'], result
                await call('capture_screenshot', {'filename': 'healed.png'})
                result = await observe_after_action(call, await call('proceed')); done(result)
                assert result['screen']['view'] == 'map', result
            elif args.scenario in {'smith', 'multi'}:
                result = await choose('SMITH')
                assert result['transition']['stop_reason'] == 'choice_required', result
                assert result['selection']['type'] == 'deck_upgrade', result
                assert result['rest_site']['status'] == 'covered', result
                selection = await call('inspect_selection')
                cards = selection['selection']['cards']
                count = 2 if args.scenario == 'multi' else 1
                for card in cards[:count]: result = await select(card)
                assert len(result['selection']['upgrade_previews']) == count, result
                assert (await fixture())['deck'] == before['deck'], 'Preview upgraded the owned cards.'
                for pair in result['selection']['upgrade_previews']:
                    assert pair['before']['id'] == pair['after']['id']
                    assert pair['after']['name'].endswith('+'), pair
                await call('capture_screenshot', {'filename': 'preview.png'})
                back = await option('cancel_preview')
                assert back['selection']['selected_ids'] == [] and back['selection']['upgrade_previews'] == [], back
                canceled = await option('cancel'); done(canceled)
                assert (await fixture())['deck'] == before['deck']
                assert 'choose_rest_option' in canceled['available_actions'], canceled
                await choose('SMITH')
                cards = (await call('inspect_selection'))['selection']['cards']
                for card in cards[:count]: await select(card)
                confirmed = await option('confirm'); done(confirmed)
                after = await fixture()
                assert sum(c['upgrades'] for c in after['deck']) == count, after
                assert not after['preview_cards'], after
                assert confirmed['rest_site']['proceed']['enabled'], confirmed
                await call('capture_screenshot', {'filename': 'confirmed.png'})
            elif args.scenario == 'cook':
                await choose('COOK')
                cards = (await call('inspect_selection'))['selection']['cards']
                await select(cards[0]); await select(cards[1])
                await option('cancel_preview')
                canceled = await option('cancel'); done(canceled)
                assert (await fixture())['deck'] == before['deck']
                await choose('COOK')
                cards = (await call('inspect_selection'))['selection']['cards']
                await select(cards[0]); result = await select(cards[1])
                assert 'confirm' in [o['id'] for o in result['selection']['options'] if o['enabled']], result
                await call('capture_screenshot', {'filename': 'cooking-preview.png'})
                result = await option('confirm'); done(result)
                after = await fixture()
                assert len(after['deck']) == len(before['deck']) - 2 and after['max_hp'] == 89, after
            elif args.scenario == 'tent':
                assert {r['id'] for r in details['rest_site']['options']} == {'HEAL', 'SMITH', 'COOK', 'KINDLE', 'LIFT'}, details
                for name in ['LIFT', 'KINDLE', 'HEAL']:
                    result = await choose(name); done(result)
                    assert name not in [r['id'] for r in result['rest_site']['options']], result
                after = await fixture()
                assert after['lifts'] == 1 and after['kindle'] == before['kindle'] + 5 and after['hp'] == 54, after
                assert {r['id'] for r in result['rest_site']['options']} == {'SMITH', 'COOK'}, result
                result = await observe_after_action(call, await call('proceed')); done(result)
                assert result['screen']['view'] == 'map', result
            elif args.scenario == 'disabled':
                assert all(not r['enabled'] for r in details['rest_site']['options'] if r['id'] in {'SMITH', 'COOK'}), details
                await call('choose_rest_option', {'option_id': 'SMITH'}, error='illegal_action')
                await call('get_observation')
                await call('choose_rest_option', {'option_id': 'COOK'}, error='illegal_action')
                assert (await fixture())['deck'] == before['deck']
                await call('get_observation')
                result = await choose('HEAL'); done(result)
            elif args.scenario == 'dig':
                result = await choose('DIG')
                assert result['transition']['stop_reason'] in {'action_completed', 'choice_required', 'manual_input_required'}, result
                after = await fixture()
                assert len(after['relics']) == len(before['relics']) + 1, after
                await call('capture_screenshot', {'filename': 'dug.png'})
            elif args.scenario in {'heal_rewards', 'dig_nested'}:
                result = await choose('HEAL' if args.scenario == 'heal_rewards' else 'DIG'); done(result)
                assert result['scene'] == 'rewards' and result['rest_site']['status'] == 'covered', result
                assert result['rewards']['items'], result
                await call('capture_screenshot', {'filename': 'nested.png'})
                details = await call('inspect_rewards')
                if args.scenario == 'heal_rewards':
                    reward = next(r for r in details['rewards']['items'] if r['type'] == 'card')
                    result = await observe_after_action(call, await call('claim_reward', {'reward_id': reward['id']}))
                    assert result['transition']['stop_reason'] == 'choice_required', result
                    await option('skip')
                result = await observe_after_action(call, await call('proceed')); done(result)
                assert result['scene'] == 'rest_site' and result['rest_site']['proceed']['enabled'], result
                after = await fixture()
                if args.scenario == 'heal_rewards': assert after['hp'] == 54 and after['deck'] == before['deck'], after
                else: assert 'CALLING_BELL' in after['relics'] and not after['preview_cards'], after
            elif args.scenario == 'dig_choice':
                result = await choose('DIG')
                result = await confirm_transform(call, result)
                assert result['scene'] == 'rest_site' and result['rest_site']['proceed']['enabled'], result
                assert len((await fixture())['deck']) == len(before['deck']), result
                result = await observe_after_action(call, await call('proceed')); done(result)
    report.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')


def main():
    parser = argparse.ArgumentParser(description='通过真实 MCP 验证隔离图形实例的休息处。')
    parser.add_argument('--scenario', required=True, choices=('basic', 'smith', 'multi', 'cook', 'tent', 'disabled', 'dig',
                                                            'heal_rewards', 'dig_nested', 'dig_choice'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__': main()
