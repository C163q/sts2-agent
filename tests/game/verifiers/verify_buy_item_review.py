"""Audit purchasing, native failures, nested input and preflight recovery."""
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


SCENARIOS = ('no_shop', 'basic', 'remove', 'courier', 'cauldron', 'sozu', 'hidden_price', 'nested', 'choice', 'fake')


async def verify(args):
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    choice_before = None
    selection_snapshot = None
    stale_recovered = False

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

            async def call(tool, arguments=None, *, error=None, label=None, allow_choice_stale=False):
                nonlocal choice_before, selection_snapshot
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
                    if args.scenario == 'choice' and tool == 'buy_item' and label == 'nested_start':
                        choice_before = state
                    if tool == 'inspect_selection': selection_snapshot = state.get('snapshot_id')
                record(row)
                assert result == json.loads(response.content[0].text), response
                if allow_choice_stale and result.get('error', {}).get('code') == 'stale_state':
                    error = 'stale_state'
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
                assert row['result']['error'] == {'code': 'illegal_action', 'message': 'The requested action is unavailable.', 'recovery': 'get_observation'}, row
                assert row['execution']['ui_interaction_started'] is False and row['execution']['action_submission_observed'] is False, row
                assert 'action_submitted' not in row['native_error'], row
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
            if args.scenario == 'no_shop':
                await reject(0, 'no_shop')
                await call('end_turn', error='observation_required', label='turn_blocked_after_rejection')
                await call('inspect_hand')
                await call('end_turn', label='turn_after_read')
                return
            if args.scenario != 'hidden_price':
                await observe('open_shop')
                await reject(0, 'closed_shop')
                await call('open_shop', error='observation_required', label='open_blocked_after_rejection')
                await observe('open_shop')
                await call('open_shop')
            inventory = await call('inspect_shop', label='inventory')
            items = inventory['shop']['items']
            if args.scenario == 'hidden_price':
                item = next(i for i in items if i['price'] is None)
                await reject(item['id'], 'unreadable_price')
                await call('close_shop', error='observation_required', label='close_blocked_after_price_rejection')
                await call('inspect_shop')
                await call('close_shop')
                return
            if args.scenario == 'basic':
                await reject(2147483647, 'unknown_id')
                await call('close_shop', error='observation_required', label='close_blocked_after_unknown_id')
                await call('inspect_shop')
                await call('inspect_map')
                await reject(items[0]['id'], 'map_covered')
                await call('buy_item', {'item_id': items[0]['id']}, error='observation_required', label='map_rejection_clears_permission')
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
                await call('inspect_shop')
                return
            if args.scenario == 'courier':
                item = next(i for i in items if i['kind'] == 'card' and i['on_sale'])
                await purchase(item, 'courier_initial')
                restocked = (await call('inspect_shop', label='courier_restocked'))['shop']['items']
                replacement = next(i for i in restocked if i['position'] == item['position'])
                assert replacement['id'] != item['id'] and not replacement['on_sale'], replacement
                await reject(item['id'], 'courier_old_id')
                await call('close_shop', error='observation_required', label='courier_rejection_clears_permission')
                await call('inspect_shop')
                await purchase(replacement, 'courier_replacement')
                for attempt in range(24):
                    current = await call('inspect_shop')
                    too_expensive = [i for i in current['shop']['items'] if i['affordable'] is False]
                    if too_expensive:
                        await reject(too_expensive[0]['id'], 'insufficient_gold')
                        await call('close_shop', error='observation_required', label='close_blocked_after_gold_rejection')
                        return
                    card = max((i for i in current['shop']['items'] if i['kind'] == 'card' and i['enabled']), key=lambda i: i['price'])
                    await purchase(card, 'spend_gold_' + str(attempt))
                raise AssertionError('The native purchases did not reach an unaffordable item.')
            if args.scenario in {'cauldron', 'sozu'}:
                potion = next(i for i in items if i['kind'] == 'potion')
                before = await native('check_test_shop')
                await purchase(potion, 'full_potion_failure' if args.scenario == 'cauldron' else 'forbidden_potion_failure',
                    status='failure_space' if args.scenario == 'cauldron' else 'failure_forbidden')
                assert await native('check_test_shop') == before
                if args.scenario == 'sozu':
                    await call('close_shop', label='close_after_native_failure')
                    return
            if args.scenario == 'remove':
                service = next(i for i in items if i['kind'] == 'card_removal')
                for confirm in (False, True):
                    started = await call('buy_item', {'item_id': service['id']}, label='removal_start_confirm' if confirm else 'removal_start_cancel')
                    assert started['transition']['stop_reason'] == 'choice_required' and 'purchase_result' not in started, started
                    if not confirm:
                        await reject(service['id'], 'selection_covered')
                        await call('selection_option', {'option_id': 'cancel'}, error='observation_required', label='cancel_blocked_after_rejection')
                        await call('inspect_selection')
                        ended = await call('selection_option', {'option_id': 'cancel'}, label='removal_canceled')
                    else:
                        selection = await call('inspect_selection')
                        await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
                        ended = await call('selection_option', {'option_id': 'confirm'}, label='removal_confirmed')
                    assert 'purchase_result' not in ended, ended
                    await observe('buy_item')
                await reject(service['id'], 'used_removal')
                await call('inspect_shop')
                return
            if args.scenario == 'fake':
                await purchase(items[0], 'fake_purchase')
                assert len((await call('inspect_shop'))['shop']['items']) == 5
                return
            relic = next(i for i in items if i['kind'] == 'relic' and i['position'] == 'relic:0')
            started = await call('buy_item', {'item_id': relic['id']}, label='nested_start')
            assert 'purchase_result' not in started, started
            if args.scenario == 'choice':
                assert started['transition']['stop_reason'] == 'choice_required', started
                async def transform_call(name, arguments=None):
                    nonlocal stale_recovered
                    result = await call(name, arguments, label='transform_confirmed' if name == 'selection_option' else None,
                        allow_choice_stale=name in {'select_card', 'selection_option'} and not stale_recovered)
                    if result.get('error', {}).get('code') == 'stale_state':
                        stale_recovered = True
                        current = await native('get_state')
                        assert choice_before is not None
                        changes = [key for key in current if key not in {'snapshot_id', 'transition', 'selection_view'}
                            and current[key] != choice_before.get(key)]
                        record({'label': 'choice_stale_diagnosis', 'buy_snapshot': choice_before['snapshot_id'],
                            'inspection_snapshot': selection_snapshot, 'current_snapshot': current['snapshot_id'],
                            'changed_fields': changes, 'before_top_bar': choice_before['top_bar'], 'after_top_bar': current['top_bar']})
                        # The diagnosed UI counter is still moving; do not keep retrying the action.
                        target_gold = (await native('check_test_shop'))['gold']
                        deadline = time.monotonic() + 8
                        while current['top_bar']['gold'] != target_gold:
                            assert time.monotonic() < deadline, current['top_bar']
                            await asyncio.sleep(.05)
                            current = await native('get_state')
                        record({'label': 'choice_gold_settled', 'displayed_gold': current['top_bar']['gold'], 'target_gold': target_gold})
                        await call('get_observation', label='explicit_read_after_choice_stale')
                        result = await call(name, arguments, label='selection_after_choice_stale')
                    if name == 'selection_option': assert 'purchase_result' not in result, result
                    return result
                ended = await confirm_transform(transform_call, started)
            else:
                await reject(relic['id'], 'reward_covered')
                await call('proceed', error='observation_required', label='proceed_blocked_after_rejection')
                await call('inspect_rewards')
                ended = await call('proceed', label='reward_finished')
            assert 'purchase_result' not in ended, ended
            await observe('buy_item')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
