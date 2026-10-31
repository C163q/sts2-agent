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
    if report.exists() or report.with_suffix('').exists(): raise RuntimeError('Evidence paths must be new.')
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.with_suffix(''))}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    deadline = time.monotonic() + 45
    while True:
        start = await asyncio.to_thread(raw.call, 'get_state')
        if start['state']['scene'] == 'main_menu' or time.monotonic() >= deadline: break
        await asyncio.sleep(.2)
    assert start['state']['scene'] == 'main_menu', 'Requires a fresh isolated instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', start['state']['snapshot_id'])
    assert created['ok'], created
    evidence = [{'created': created}]
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
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
                else: assert 'error' not in data, data
                return data

            async def fixture():
                result = await asyncio.to_thread(raw.call, 'check_test_shop')
                assert result['ok'], result
                evidence.append({'fixture': result['state']})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                return result['state']

            def done(result):
                assert result['transition']['complete'] and result['transition']['stop_reason'] == 'action_completed', result

            async def remove(result, cancel=False):
                assert result['transition']['stop_reason'] == 'choice_required', result
                assert result['shop']['status'] == 'covered' and result['selection']['type'] == 'deck', result
                if cancel:
                    return await call('selection_option', {'option_id': 'cancel'})
                details = await call('inspect_selection')
                selected = await call('select_card', {'card_id': details['selection']['cards'][0]['id']})
                assert selected['selection']['options'], selected
                await call('capture_screenshot', {'filename': 'removal-preview.png'})
                return await call('selection_option', {'option_id': 'confirm'})

            await call('open_shop', error='observation_required')
            result = await call('get_observation')
            before = await fixture()
            assert result['scene'] == 'shop', result
            if args.scenario == 'hidden_price':
                assert result['shop']['view'] == 'inventory', result
                item = next(i for i in result['shop']['items'] if i['position'] == 'character_card:0')
                assert item['price'] is None and item['affordable'] is None and not item['enabled'], item
                await call('capture_screenshot', {'filename': 'hidden-price.png'})
                await call('buy_item', {'item_id': item['id']}, error='illegal_action')
                assert (await fixture()) == before
                await call('get_observation')
                result = await call('close_shop'); done(result)
                result = await call('proceed'); done(result)
                print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}'); return
            if args.scenario == 'targeting':
                assert before['targeting'] and before['targeting_pending'], before
                await call('capture_screenshot', {'filename': 'targeting.png'})
                await call('open_shop', error='illegal_action')
                result = await call('get_observation')
                assert 'open_shop' not in result['available_actions'] and 'proceed' not in result['available_actions'], result
                await call('proceed', error='illegal_action')
                assert (await fixture()) == before
                canceled = await asyncio.to_thread(raw.call, 'cancel_test_shop_targeting')
                assert canceled['ok'], canceled
                evidence.append({'cancel_targeting': canceled})
                await call('get_observation')
                result = await call('open_shop'); done(result)
                result = await call('close_shop'); done(result)
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}'); return
            if args.scenario == 'sozu':
                relics = await call('inspect_relics')
                sozu = next(r for r in relics['relics'] if r['name'] == 'Sozu')
                assert 'potion' in sozu['description'].lower(), sozu
            if args.scenario.startswith('parasol'):
                assert result['selection'] and result['selection']['type'] == 'deck', result
                assert not any(o['id'] == 'cancel' and o['enabled'] for o in result['selection']['options']), result
                await call('capture_screenshot', {'filename': 'parasol-selection.png'})
                result['transition'] = {'stop_reason': 'choice_required'}
                result = await remove(result); done(result)
                after = await fixture()
                assert after['gold'] == 2099 and after['deck_count'] == 16, after
                assert after['removal_used'] and not after['pending'] and not after['obtaining'], after
                assert all(name in after['relics'] for name in ['ANCHOR', 'LANTERN', 'PEN_NIB']), after
                if args.scenario == 'parasol_courier':
                    assert len(result['shop']['items']) == 14, result
                    assert all(i['enabled'] for i in result['shop']['items'] if i['kind'] != 'card_removal'), result
                elif args.scenario == 'parasol_sozu':
                    assert [i['kind'] for i in result['shop']['items']] == ['potion', 'potion', 'potion', 'card_removal'], result
                    assert after['potions'] == [None, None, None], after
                else:
                    assert [i['kind'] for i in result['shop']['items']] == ['card_removal'], result
            else:
                assert result['shop']['view'] == 'merchant' and result['shop']['items'] is None, result
                await call('inspect_shop', error='illegal_action')
                await call('get_observation')
                if args.scenario in {'foul', 'fake'}:
                    foul = next(i for i, p in enumerate(result['top_bar']['potion_slots']) if p and p['name'] == 'Foul Potion')
                    assert result['top_bar']['potion_slots'][foul]['usable_here'], result
                result = await call('open_shop'); done(result)
                assert result['shop']['view'] == 'inventory', result
                items = result['shop']['items']
                assert len(items) == (6 if args.scenario == 'fake' else 14), result
                if args.scenario == 'fake':
                    assert all(i['kind'] == 'relic' for i in items), result
                    assert [i['price'] for i in items] == before['base_prices'], result
                details = await call('inspect_shop')
                for item in details['shop']['items']:
                    assert 'description' in (item.get('card') or item), item
                unchanged = await fixture()
                assert unchanged == before, (before, unchanged)
                await call('capture_screenshot', {'filename': 'inventory.png'})
                if args.scenario == 'basic':
                    await call('inspect_map')
                    covered = await call('get_observation')
                    assert covered['shop'] == dict.fromkeys(('view', 'items', 'open', 'back', 'proceed')) | {'status': 'covered'}, covered
                    await call('inspect_shop', error='illegal_action')
                    await call('close_map'); await call('get_observation')
                    result = await call('close_shop'); done(result)
                    result = await call('open_shop'); done(result)
                    for kind in ('card', 'relic', 'potion'):
                        item = next(i for i in result['shop']['items'] if i['kind'] == kind)
                        gold = result['top_bar']['gold']; count = result['top_bar']['deck_count']
                        result = await call('buy_item', {'item_id': item['id']}); done(result)
                        assert result['purchase_result'] == {'item_id': item['id'], 'status': 'success'}, result
                        assert all(i['id'] != item['id'] for i in result['shop']['items']), result
                        assert result['top_bar']['gold'] == gold - item['price'], result
                        if kind == 'card': assert result['top_bar']['deck_count'] == count + 1, result
                    await call('buy_item', {'item_id': item['id']}, error='illegal_action')
                    result = await call('get_observation')
                elif args.scenario == 'remove':
                    item = next(i for i in items if i['kind'] == 'card_removal')
                    result = await call('buy_item', {'item_id': item['id']})
                    result = await remove(result, cancel=True); done(result)
                    assert (await fixture())['gold'] == before['gold'], result
                    assert not next(i for i in result['shop']['items'] if i['kind'] == 'card_removal')['used'], result
                    result = await call('buy_item', {'item_id': item['id']})
                    result = await remove(result); done(result)
                    after = await fixture()
                    assert after['deck_count'] == before['deck_count'] - 1 and after['gold'] == before['gold'] - item['price'], after
                    removal = next(i for i in result['shop']['items'] if i['kind'] == 'card_removal')
                    assert removal['used'] and removal['price'] is None and not removal['enabled'], removal
                elif args.scenario == 'courier':
                    item = next(i for i in items if i['kind'] == 'card' and i['on_sale'])
                    result = await call('buy_item', {'item_id': item['id']}); done(result)
                    replacement = next(i for i in result['shop']['items'] if i['position'] == item['position'])
                    assert replacement['id'] != item['id'] and not replacement['on_sale'], result
                    assert len(result['shop']['items']) == 14, result
                    await call('buy_item', {'item_id': item['id']}, error='illegal_action')
                    result = await call('get_observation')
                    result = await call('buy_item', {'item_id': replacement['id']}); done(result)
                elif args.scenario in {'full', 'sozu'}:
                    item = next(i for i in items if i['kind'] == 'potion')
                    result = await call('buy_item', {'item_id': item['id']}); done(result)
                    assert result['purchase_result']['status'] == ('failure_forbidden' if args.scenario == 'sozu' else 'failure_space'), result
                    after = await fixture()
                    assert after == before, (before, after)
                elif args.scenario in {'foul', 'fake'}:
                    assert not result['top_bar']['potion_slots'][foul]['usable_here'], result
                    query = await call('inspect_targets', {'potion_slot': foul})
                    assert not query['usable'] and not query['targets'], query
                    if args.scenario == 'fake':
                        item = items[0]
                        result = await call('buy_item', {'item_id': item['id']}); done(result)
                        assert len(result['shop']['items']) == 5, result
                    result = await call('close_shop'); done(result)
                    if args.scenario == 'foul':
                        await call('inspect_map'); await call('get_observation')
                        hidden_target = await call('inspect_targets', {'potion_slot': foul})
                        assert not hidden_target['usable'] and hidden_target['targets'] == [], hidden_target
                        await call('close_map'); await call('get_observation')
                    query = await call('inspect_targets', {'potion_slot': foul})
                    assert query['usable'] and query['targets'] == [{'id': 'merchant', 'kind': 'merchant', 'name': 'Merchant'}], query
                    result = await call('use_potion', {'potion_slot': foul, 'target_id': 'merchant'})
                    if args.scenario == 'fake':
                        assert result['scene'] == 'combat' and result['transition']['stop_reason'] == 'player_ready', result
                        assert result['player']['hand'] and result['available_actions'], result
                        await call('capture_screenshot', {'filename': 'fake-combat.png'})
                        report.write_text(json.dumps(evidence, indent=2) + '\n')
                        print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}'); return
                    done(result)
                    assert result['top_bar']['gold'] == before['gold'] + 100, result
                    result = await call('open_shop'); done(result)
                elif args.scenario in {'nested', 'choice', 'cauldron', 'cauldron_sozu'}:
                    item = next(i for i in items if i['kind'] == 'relic')
                    result = await call('buy_item', {'item_id': item['id']})
                    if args.scenario == 'choice':
                        result = await confirm_transform(call, result)
                        assert result['scene'] == 'shop' and all(i['id'] != item['id'] for i in result['shop']['items']), result
                        await call('capture_screenshot', {'filename': 'transformed.png'})
                        result = await call('close_shop'); done(result)
                        result = await call('proceed'); done(result)
                        report.write_text(json.dumps(evidence, indent=2) + '\n')
                        print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}'); return
                    done(result)
                    assert result['scene'] == 'rewards' and result['shop']['status'] == 'covered', result
                    if args.scenario == 'cauldron_sozu':
                        assert result['top_bar']['potion_slots'] == [None, None, None], result
                        reward = next(i for i in result['rewards']['items'] if i['type'] == 'potion')
                        result = await call('claim_reward', {'reward_id': reward['id']}); done(result)
                        assert result['reward_result'] == {'reward_id': reward['id'], 'status': 'not_obtained'}, result
                        assert result['top_bar']['potion_slots'] == [None, None, None], result
                        assert all(i['id'] != reward['id'] for i in result['rewards']['items']), result
                    if args.scenario == 'cauldron':
                        result = await call('discard_potion', {'potion_slot': 0}); done(result)
                        assert result['scene'] == 'rewards' and result['top_bar']['potion_slots'][0] is None, result
                        reward = next(i for i in result['rewards']['items'] if i['type'] == 'potion')
                        result = await call('claim_reward', {'reward_id': reward['id']}); done(result)
                        assert result['reward_result']['status'] == 'claimed', result
                        assert result['top_bar']['potion_slots'][0] is not None, result
                    result = await call('proceed'); done(result)
                    assert result['scene'] == 'shop', result
                    assert all(i['id'] != item['id'] for i in result['shop']['items']), result
            await call('capture_screenshot', {'filename': 'settled.png'})
            stable = await call('get_observation')
            assert stable['top_bar'] == result['top_bar'] and stable['shop'] == result['shop'], stable
            result = await call('close_shop'); done(result)
            result = await call('proceed'); done(result)
            assert result['screen']['view'] == 'map' and result['shop']['status'] == 'covered', result
    report.write_text(json.dumps(evidence, indent=2) + '\n')
    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks; {report}')


def main():
    parser = argparse.ArgumentParser(description='通过真实 MCP 验证隔离图形实例的商店。')
    parser.add_argument('--scenario', required=True, choices=('basic', 'remove', 'courier', 'full', 'foul', 'fake', 'parasol', 'parasol_courier', 'nested', 'choice', 'cauldron', 'sozu', 'parasol_sozu', 'cauldron_sozu', 'hidden_price', 'targeting'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__': main()
