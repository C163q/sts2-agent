"""Verify purchase recovery, results and immediately usable nested input."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_actions import confirm_transform
from tests.game.support.verification_runtime import ensure_run, ipc_directory


SCENARIOS = ('no_shop', 'basic', 'remove', 'courier', 'cauldron', 'sozu', 'hidden_price', 'nested', 'choice', 'fake', 'choice_timing')


async def verify(args):
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    scenario = 'choice' if args.scenario == 'choice_timing' else args.scenario
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation):
        reply = await asyncio.to_thread(raw.call, operation)
        record({'native_operation': operation, 'result': reply})
        assert reply['ok'], reply
        return reply['state']

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, *, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                old = set((raw.directory / 'responses').glob('*.json'))
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                row = {'tool': tool, 'arguments': arguments, 'result': result, 'label': label,
                    'image_count': sum(part.type == 'image' for part in response.content)}
                added = set((raw.directory / 'responses').glob('*.json')) - old
                if added:
                    assert len(added) == 1, added
                    original = json.loads(added.pop().read_text())
                    row.update(native_error=original.get('error'), execution=original.get('execution'))
                    state = original.get('state') or {}
                    row['native_snapshot_id'] = state.get('snapshot_id')
                    if tool == 'buy_item': row['native_gold'] = (state.get('top_bar') or {}).get('gold')
                record(row)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def observe(action=None):
                deadline = time.monotonic() + 15
                while True:
                    result = await call('get_observation', label='observe_' + (action or 'screen'))
                    if action is None or action in result['available_actions']: return result
                    assert time.monotonic() < deadline, result
                    await asyncio.sleep(.1)

            async def reject(item_id, label):
                before = await native('get_state')
                await call('buy_item', {'item_id': item_id}, error='illegal_action', label=label)
                row = evidence[-1]
                hints = {'no_shop': 'No shop', 'closed_shop': 'open_shop', 'map_covered': 'close_map',
                    'deck_covered': 'close_card_view', 'insufficient_gold': 'Not enough gold', 'unreadable_price': 'price',
                    'selection_covered': 'inspect_selection', 'reward_covered': 'inspect_rewards', 'used_removal': 'already been used'}
                assert row['result']['error']['recovery'] == 'choose_legal_action', row
                assert hints.get(label, 'inspect_shop') in row['result']['error']['message'], row
                assert row['execution']['ui_interaction_started'] is False and row['execution']['action_submission_observed'] is False, row
                assert row['native_error']['action_submitted'] is False, row
                after = await native('get_state')
                assert before['snapshot_id'] == after['snapshot_id'], (before, after)

            async def purchase(item, label, status='success', preset='full'):
                result = await call('buy_item', {'item_id': item['id'], 'preset': preset}, label=label)
                assert result['purchase_result'] == {'item_id': item['id'], 'status': status}, result
                assert result['transition']['stop_reason'] == 'action_completed' and result['transition']['complete'], result
                assert not {'shop', 'player', 'top_bar', 'map'} & result.keys(), result
                return result

            await call('buy_item', {'item_id': 0}, error='observation_required', label='no_initial_permission')
            initial = await observe()
            if scenario == 'no_shop':
                await reject(0, 'no_shop')
                await call('end_turn', label='turn_after_rejection')
                return
            if scenario != 'hidden_price':
                await observe('open_shop')
                if args.scenario == 'choice_timing':
                    await call('open_shop', label='open_for_timing')
                else:
                    await reject(0, 'closed_shop')
                    await call('open_shop', label='open_after_rejection')
            inventory = await call('inspect_shop', label='inventory')
            items = inventory['shop']['items']
            if scenario == 'hidden_price':
                item = next(i for i in items if i['price'] is None)
                await reject(item['id'], 'unreadable_price')
                await call('close_shop', label='close_after_price_rejection')
                return
            if scenario == 'basic':
                await reject(2147483647, 'unknown_id')
                await call('close_shop', label='close_after_unknown_id')
                await call('open_shop')
                await call('inspect_map')
                await reject(items[0]['id'], 'map_covered')
                await call('close_map')
                await call('inspect_deck')
                await reject(items[0]['id'], 'deck_covered')
                await call('close_card_view')
                await call('buy_item', {'item_id': -1}, error='invalid_request', label='local_invalid')
                for kind in ('card', 'relic', 'potion'):
                    item = next(i for i in items if i['kind'] == kind)
                    before = await native('check_test_shop')
                    await purchase(item, 'buy_' + kind, preset='default' if kind == 'potion' else 'full')
                    after = await native('check_test_shop')
                    assert after['gold'] == before['gold'] - item['price'], (before, after)
                    assert not any(i['id'] == item['id'] for i in (await call('inspect_shop'))['shop']['items'])
                await reject(items[0]['id'], 'sold_id')
                await call('close_shop', label='close_after_sold_id')
                return
            if scenario == 'courier':
                item = next(i for i in items if i['kind'] == 'card' and i['on_sale'])
                await purchase(item, 'courier_initial')
                restocked = (await call('inspect_shop', label='courier_restocked'))['shop']['items']
                replacement = next(i for i in restocked if i['position'] == item['position'])
                assert replacement['id'] != item['id'] and not replacement['on_sale'], replacement
                await reject(item['id'], 'courier_old_id')
                await call('close_shop', label='close_after_courier_rejection')
                await call('open_shop')
                await purchase(replacement, 'courier_replacement')
                for attempt in range(24):
                    current = await call('inspect_shop')
                    too_expensive = [i for i in current['shop']['items'] if i['affordable'] is False]
                    if too_expensive:
                        await reject(too_expensive[0]['id'], 'insufficient_gold')
                        await call('close_shop', label='close_after_gold_rejection')
                        return
                    card = max((i for i in current['shop']['items'] if i['kind'] == 'card' and i['enabled']), key=lambda i: i['price'])
                    await purchase(card, 'spend_gold_' + str(attempt))
                raise AssertionError('The native purchases did not reach an unaffordable item.')
            if scenario in {'cauldron', 'sozu'}:
                potion = next(i for i in items if i['kind'] == 'potion')
                before = await native('check_test_shop')
                await purchase(potion, 'full_potion_failure' if scenario == 'cauldron' else 'forbidden_potion_failure',
                    status='failure_space' if scenario == 'cauldron' else 'failure_forbidden')
                assert await native('check_test_shop') == before
                if scenario == 'sozu':
                    await call('close_shop', label='close_after_native_failure')
                    return
            if scenario == 'remove':
                service = next(i for i in items if i['kind'] == 'card_removal')
                for confirm in (False, True):
                    started = await call('buy_item', {'item_id': service['id']}, label='removal_start_confirm' if confirm else 'removal_start_cancel')
                    assert started['transition']['stop_reason'] == 'choice_required' and started['purchase_result'] == {
                        'item_id': service['id'], 'status': 'pending'}, started
                    if not confirm:
                        await reject(service['id'], 'selection_covered')
                        ended = await call('selection_option', {'option_id': 'cancel'}, label='removal_canceled')
                    else:
                        selection = await call('inspect_selection')
                        await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
                        ended = await call('selection_option', {'option_id': 'confirm'}, label='removal_confirmed')
                    assert 'purchase_result' not in ended, ended
                    await observe('buy_item')
                await reject(service['id'], 'used_removal')
                await call('close_shop', label='close_after_used_removal')
                return
            if scenario == 'fake':
                await purchase(items[0], 'fake_purchase')
                assert len((await call('inspect_shop'))['shop']['items']) == 5
                return
            relic = next(i for i in items if i['kind'] == 'relic' and i['position'] == 'relic:0')
            started = await call('buy_item', {'item_id': relic['id']}, label='nested_start')
            assert evidence[-1]['native_gold'] == inventory['top_bar']['gold'] - relic['price'], evidence[-1]
            assert started['purchase_result'] == {'item_id': relic['id'], 'status': 'pending'}, started
            if scenario == 'choice':
                assert started['transition']['stop_reason'] == 'choice_required', started
                async def transform_call(name, arguments=None):
                    result = await call(name, arguments, label='transform_confirmed' if name == 'selection_option' else None)
                    if name == 'selection_option': assert 'purchase_result' not in result, result
                    return result
                ended = await confirm_transform(transform_call, started)
            else:
                await reject(relic['id'], 'reward_covered')
                ended = await call('proceed', label='reward_finished')
            assert 'purchase_result' not in ended, ended
            await observe('buy_item')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
