import argparse
import asyncio
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client
from verification_actions import confirm_transform


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    start = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while start['state']['scene'] != 'main_menu' and time.monotonic() < deadline:
        await asyncio.sleep(.2)
        start = await asyncio.to_thread(raw.call, 'get_state')
    assert start['state']['scene'] == 'main_menu', 'Requires a fresh isolated instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', start['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.version == '0.22.0'
            assert len((await session.list_tools()).tools) == 37

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                assert data == json.loads(response.content[0].text)
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert 'snapshot_id' not in data
                if error:
                    assert data.get('error', {}).get('code') == error, data
                else:
                    assert 'error' not in data, data
                return data

            async def fixture():
                result = await asyncio.to_thread(raw.call, 'check_test_rewards')
                assert result['ok'], result
                evidence.append({'fixture': result['state']})
                return result['state']

            await call('claim_reward', {'reward_id': 0}, error='observation_required')
            initial = await call('get_observation')
            assert initial['scene'] == 'rewards', initial
            assert initial['rewards']['status'] == 'visible', initial
            await call('capture_screenshot', {'filename': 'initial.png'})
            details = await call('inspect_rewards')
            rows = details['rewards']['items']
            assert all('hover_tips' in row for row in rows)
            assert not any('cards' in row for row in rows), rows
            before = await fixture()
            by_type = lambda kind: next(r for r in rows if r['type'] == kind)

            if args.scenario == 'basic':
                ids = {r['id'] for r in rows}
                assert len(rows) == 6 and len(ids) == 6, rows
                opened = await call('inspect_map')
                assert opened['nodes'], opened
                covered = await call('get_observation')
                assert covered['rewards'] == {'status': 'covered', 'title': None, 'items': None, 'proceed': None}, covered
                assert 'claim_reward' not in covered['available_actions']
                await call('claim_reward', {'reward_id': by_type('gold')['id']}, error='illegal_action')
                await call('inspect_rewards', error='illegal_action')
                await call('close_map')
                await call('claim_reward', {'reward_id': by_type('card')['id']}, error='observation_required')
                await call('get_observation')
                check = await call('inspect_rewards')
                assert {r['id'] for r in check['rewards']['items']} == ids
                choice = await call('claim_reward', {'reward_id': by_type('card')['id']})
                assert choice['transition']['stop_reason'] == 'choice_required', choice
                assert 'select_card' in choice['available_actions'], choice
                assert choice['selection']['type'] == 'reward' and choice['rewards']['items'] is None, choice
                await call('capture_screenshot', {'filename': 'card-choice.png'})
                skipped = await call('selection_option', {'option_id': 'skip'})
                assert skipped['transition']['stop_reason'] == 'action_completed', skipped
                assert any(r['id'] == by_type('card')['id'] for r in (await call('inspect_rewards'))['rewards']['items'])
                await call('claim_reward', {'reward_id': by_type('card')['id']})
                selection = await call('inspect_selection')
                anger = next(c for c in selection['selection']['cards'] if c['name'] == 'Anger')
                chosen = await call('select_card', {'card_id': anger['id']})
                assert chosen['transition']['stop_reason'] == 'action_completed', chosen
                await call('claim_reward', {'reward_id': by_type('special_card')['id']})
                for row in [r for r in rows if r['type'] == 'gold']:
                    await call('claim_reward', {'reward_id': row['id']})
                await call('claim_reward', {'reward_id': by_type('potion')['id']})
                emptied = await call('claim_reward', {'reward_id': by_type('relic')['id']})
                assert emptied['rewards']['items'] == [], emptied
                assert emptied['rewards']['proceed']['text'] == 'Proceed', emptied
                assert not emptied['rewards']['proceed']['skips_remaining'], emptied
                await call('capture_screenshot', {'filename': 'empty.png'})
                after = await fixture()
                assert after['gold'] == before['gold'] + 40, after
                assert len(after['deck']) == len(before['deck']) + 2, after
                assert any(c['name'].startswith('Strike') and c['upgrades'] == 1 for c in after['deck']), after
                assert 'WHETSTONE' in after['relics'] and after['potions'][0] == 'BLOCK_POTION', after
                proceeded = await call('proceed')
                assert proceeded['transition']['stop_reason'] == 'action_completed', proceeded
                assert proceeded['screen']['view'] == 'map', proceeded
                await call('inspect_map')
            elif args.scenario == 'full':
                blocked = await call('claim_reward', {'reward_id': by_type('potion')['id']})
                assert blocked['transition']['stop_reason'] == 'action_completed', blocked
                assert blocked['reward_result']['status'] == 'not_claimed', blocked
                assert (await fixture())['potions'] == before['potions']
                assert len((await call('inspect_rewards'))['rewards']['items']) == 6
                await call('discard_potion', {'potion_slot': 0})
                await call('claim_reward', {'reward_id': by_type('potion')['id']})
                assert len((await call('inspect_rewards'))['rewards']['items']) == 5
                assert (await fixture())['potions'][0] == 'BLOCK_POTION'
            elif args.scenario in {'card_first', 'relic_first'}:
                if args.scenario == 'relic_first':
                    await call('claim_reward', {'reward_id': by_type('relic')['id']})
                await call('claim_reward', {'reward_id': by_type('card')['id']})
                selection = await call('inspect_selection')
                anger = next(c for c in selection['selection']['cards'] if c['name'] == 'Anger')
                await call('select_card', {'card_id': anger['id']})
                if args.scenario == 'card_first':
                    await call('claim_reward', {'reward_id': by_type('relic')['id']})
                after = await fixture()
                picked = next(c for c in after['deck'] if c['name'].startswith('Anger'))
                assert picked['upgrades'] == (1 if args.scenario == 'card_first' else 0), after
                await call('capture_screenshot', {'filename': 'final.png'})
            elif args.scenario == 'linked':
                assert len(rows) == 2 and rows[0]['linked_group'] == rows[1]['linked_group'] is not None, rows
                result = await call('claim_reward', {'reward_id': by_type('gold')['id']})
                assert result['rewards']['items'] == [], result
                after = await fixture()
                assert after['gold'] == before['gold'] + 17 and after['potions'] == before['potions'], after
            elif args.scenario in {'skip', 'empty'}:
                assert initial['rewards']['proceed']['skips_remaining'] == (args.scenario == 'skip'), initial
                result = await call('proceed')
                assert result['screen']['view'] == 'map' and result['transition']['stop_reason'] == 'action_completed', result
                await call('inspect_map')
                after = await fixture()
                assert before['gold'] == after['gold'] and before['deck'] == after['deck'], after
            elif args.scenario == 'nested':
                result = await call('claim_reward', {'reward_id': by_type('relic')['id']})
                assert result['transition']['stop_reason'] == 'action_completed', result
                assert (await fixture())['preview_cards'] == 0, 'A native card preview still obscures reward rows.'
                nested = await call('inspect_rewards')
                assert len(nested['rewards']['items']) == 3, nested
                await call('capture_screenshot', {'filename': 'nested.png'})
                result = await call('proceed')
                assert result['rewards']['items'] == [] and result['rewards']['proceed']['text'] == 'Proceed', result
                assert 'CALLING_BELL' in (await fixture())['relics']
            elif args.scenario == 'unsupported':
                result = await call('claim_reward', {'reward_id': by_type('relic')['id']})
                result = await confirm_transform(call, result)
                assert result['scene'] == 'rewards', result
                result = await call('proceed')
                assert result['transition']['stop_reason'] == 'action_completed', result
            elif args.scenario == 'returned':
                special = by_type('special_card')
                assert special['hover_tips'] and special['text'] == 'Take your stolen card back.', special
                await call('claim_reward', {'reward_id': special['id']})
                stolen_gold = next(r for r in rows if r['type'] == 'gold' and 'stolen back' in r['text'])
                await call('claim_reward', {'reward_id': stolen_gold['id']})
                after = await fixture()
                assert len(after['deck']) == len(before['deck']) + 1 and after['gold'] == before['gold'] + 23, after
            elif args.scenario == 'escaped':
                assert not any(r['type'] == 'special_card' or r['type'] == 'gold' and 'stolen back' in r['text'] for r in rows), rows
                assert before['gold_proportion'] == 0 and before['escaped_count'] == 3, before
                assert by_type('card') and initial['rewards']['title'] != 'Loot!', initial
                await call('proceed')
            report.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: {args.scenario}; {len(evidence)} checks/calls; real graphical MCP rewards flow.')


def main():
    parser = argparse.ArgumentParser(description='验证独立 --reward-scenario 图形实例的搜刮、选牌与地图流程。')
    parser.add_argument('--scenario', required=True, choices=('basic', 'full', 'skip', 'empty', 'linked', 'card_first', 'relic_first', 'nested', 'returned', 'escaped', 'unsupported'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
