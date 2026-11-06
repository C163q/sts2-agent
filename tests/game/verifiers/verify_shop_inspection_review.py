"""Audit displayed merchant details and current pure-read rejection behavior."""
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
from tests.game.support.verification_runtime import ensure_run, ipc_directory

SCENARIOS = ('no_shop', 'basic', 'remove', 'courier', 'hidden_price', 'fake', 'full', 'nested', 'parasol', 'display')


async def verify(args):
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
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
                    native = json.loads(added.pop().read_text())
                    row.update(native_error=native.get('error'), execution=native.get('execution'))
                record(row)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def fixture():
                reply = await asyncio.to_thread(raw.call, 'check_test_shop')
                record({'native_operation': 'check_test_shop', 'result': reply})
                assert reply['ok'], reply
                return reply['state']

            async def reject(label, recovery='choose_legal_action'):
                result = await call('inspect_shop', error='illegal_action', label=label)
                hint = ('open_shop' if label.startswith('closed') else 'close_map' if label == 'map_covered'
                    else 'close_card_view' if label == 'deck_covered' else 'inspect_selection' if 'selection' in label
                    else 'inspect_rewards' if label == 'reward_covered' else 'shop')
                assert hint in result['error']['message'], result
                assert result['error']['recovery'] == recovery, result
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                return result

            async def details(label, preset='full'):
                result = await call('inspect_shop', {'preset': preset}, label=label)
                assert result['scene'] == 'shop' and result['screen'] == {'status': 'visible'}, result
                assert result['shop']['status'] == 'visible' and result['shop']['view'] == 'inventory', result
                assert set(result['top_bar']) == {'gold', 'potion_slots', 'deck_count', 'relic_count'}, result
                assert 'available_actions' not in result, result
                for item in result['shop']['items']:
                    content = item.get('card') or item
                    if item.get('used'): assert 'description' not in content and 'hover_tips' not in content, item
                    else: assert content['description'] and 'hover_tips' in content, item
                assert evidence[-1]['execution']['ui_interaction_started'] is False and evidence[-1]['image_count'] == 0, evidence[-1]
                return result

            scenario = args.scenario
            if scenario == 'no_shop':
                await reject('no_shop_first_read', 'get_observation')
                await call('end_turn', error='observation_required', label='failed_first_read_has_no_permission')
                await call('get_observation')
                await reject('no_shop_existing_permission')
                await call('end_turn', label='end_turn_after_read_rejection')
                return

            if scenario == 'parasol':
                initial = await call('get_observation', label='parasol_selection')
                assert initial['selection']['type'] == 'deck', initial
                await reject('parasol_selection_covered')
                selected = await call('inspect_selection')
                await call('select_card', {'card_id': selected['selection']['cards'][0]['id']})
                await call('selection_option', {'option_id': 'confirm'})
                await details('parasol_complete')
                await call('close_shop', label='close_after_parasol_details')
                return

            if scenario != 'hidden_price':
                await reject('closed_first_read', 'get_observation')
                await call('open_shop', error='observation_required', label='failed_closed_read_has_no_permission')
            initial = await call('get_observation', label='initial_observation')
            if scenario != 'hidden_price':
                await reject('closed_existing_permission')
                await call('open_shop', label='open_after_read_rejection')
            before = await fixture()
            inventory = await details(scenario + '_inventory')
            assert await details('repeated_unchanged') == inventory
            assert await fixture() == before, 'Read-only details changed inventory, resources or shop RNG.'
            await call('inspect_shop', {'unexpected': True}, error='invalid_request', label='local_invalid')
            summary = await call('inspect_shop', {'preset': 'summary'}, label='summary')
            observed = await call('get_observation', {'preset': 'summary'}, label='summary_observation')
            assert summary['shop'] == observed['shop'] and summary['top_bar'] == observed['top_bar'], (summary, observed)
            filtered = await call('inspect_shop', {'preset': 'summary', 'item_ids': [9999, inventory['shop']['items'][0]['id']]}, label='id_filter')
            assert len(filtered['shop']['items']) == 1 and filtered['errors'] == [{'code': 'item_ids_not_found', 'item_ids': [9999]}], filtered
            empty = await call('inspect_shop', {'item_ids': [], 'kinds': []}, label='empty_filter')
            assert empty['shop']['items'] == [] and empty['top_bar']['gold'] == inventory['top_bar']['gold'], empty
            relics = await call('inspect_shop', {'kinds': ['relic']}, label='kind_filter')
            assert all(item['kind'] == 'relic' for item in relics['shop']['items']), relics
            assert await details('after_local_errors') == inventory
            items = inventory['shop']['items']

            if scenario == 'display':
                async def native(operation, arguments=None):
                    reply = await asyncio.to_thread(raw.call, operation, arguments=arguments)
                    record({'native_operation': operation, 'arguments': arguments, 'result': reply})
                    assert reply['ok'], reply
                    return reply['state']
                modes = [(mode, 'card') for mode in ('offscreen', 'price_offscreen', 'hidden', 'transparent', 'visual_hidden', 'clipped',
                    'controller_only', 'mouse_only', 'click_disabled', 'blocked', 'gold_hidden', 'top_bar_hidden')]
                modes += [('no_hover', kind) for kind in ('card', 'relic', 'potion', 'card_removal')]
                for mode, kind in modes:
                    target = next(item for item in items if item['kind'] == kind)
                    try:
                        configured = await native('set_test_shop_display', {'mode': mode, 'kind': kind})
                        if mode == 'controller_only': assert configured['effective_focus'] == 'All', configured
                        # Native Back slides when input is blocked; compare settled snapshots.
                        deadline = time.monotonic() + 3
                        while True:
                            state = await native('get_state')
                            expected_back = None if mode == 'blocked' else {'enabled': True}
                            if state['shop']['back'] == expected_back: break
                            assert time.monotonic() < deadline, state['shop']
                            await asyncio.sleep(.05)
                        value = await call('inspect_shop', label=mode + '_' + kind + '_full')
                        rows = {item['id']: item for item in value['shop']['items']}
                        if mode in {'hidden', 'transparent', 'visual_hidden', 'clipped'}:
                            assert target['id'] not in rows, value
                        else:
                            row = rows[target['id']]
                            assert row['price'] == target['price'], row
                            content = row.get('card') or row
                            if mode in {'no_hover', 'blocked'}:
                                if kind == 'card': assert content['description'] and content['hover_tips'] is None, row
                                else: assert content['description'] is None and content['hover_tips'] == [], row
                                assert 'shop.items.' + str(target['id']) in value['notes']['hover_tips_unavailable']['sources'], value
                            else:
                                assert content['description'] and content['hover_tips'] is not None, row
                                assert 'hover_tips_unavailable' not in value.get('notes', {}), value
                            if mode == 'gold_hidden': assert value['top_bar']['gold'] is None, value
                            if mode == 'top_bar_hidden': assert value['top_bar'] is None, value
                        compact = await call('inspect_shop', {'preset': 'summary'}, label=mode + '_' + kind + '_summary')
                        observed = await call('get_observation', {'preset': 'summary'}, label=mode + '_' + kind + '_observation')
                        assert compact['shop'] == observed['shop'] and compact.get('top_bar') == observed.get('top_bar'), (compact, observed)
                        assert 'hover_tips_unavailable' not in compact.get('notes', {}), compact
                        subset = await call('inspect_shop', {'item_ids': [target['id']]}, label=mode + '_' + kind + '_filtered')
                        assert len(subset['shop']['items']) == int(target['id'] in rows), subset
                    finally: await native('set_test_shop_display', {'mode': 'normal', 'kind': kind})
                guards = await native('check_test_dispatch')
                assert all(count == 81 for count in guards.values()), guards
                return

            if scenario == 'basic':
                await details('basic_default', 'default')
                await call('inspect_map'); await reject('map_covered')
                await call('close_map', label='close_map_after_read_rejection')
                await call('inspect_deck'); await reject('deck_covered')
                await call('close_card_view', label='close_deck_after_read_rejection')
                card = next(item for item in items if item['kind'] == 'card')
                await call('buy_item', {'item_id': card['id']}, label='buy_after_read_rejections')
                after = await details('after_card_purchase')
                assert card['id'] not in [item['id'] for item in after['shop']['items']], after
                await call('close_shop'); await reject('closed_after_purchase')
                await call('open_shop', label='reopen_after_read_rejection')
            elif scenario == 'remove':
                removal = next(item for item in items if item['kind'] == 'card_removal')
                await call('buy_item', {'item_id': removal['id']})
                await reject('selection_covered')
                await call('selection_option', {'option_id': 'cancel'}, label='cancel_after_read_rejection')
                await details('after_removal_cancel')
                await call('buy_item', {'item_id': removal['id']})
                selected = await call('inspect_selection')
                await call('select_card', {'card_id': selected['selection']['cards'][0]['id']})
                await call('selection_option', {'option_id': 'confirm'})
                after = await details('used_removal')
                used = next(item for item in after['shop']['items'] if item['kind'] == 'card_removal')
                assert used['used'] and used['price'] is None and used['affordable'] is None and not used['enabled'], used
            elif scenario == 'courier':
                card = next(item for item in items if item['kind'] == 'card' and item['on_sale'])
                await call('buy_item', {'item_id': card['id']})
                after = await details('courier_restocked')
                replacement = next(item for item in after['shop']['items'] if item['position'] == card['position'])
                assert replacement['id'] != card['id'] and not replacement['on_sale'], after
            elif scenario == 'hidden_price':
                card = next(item for item in items if item['position'] == 'character_card:0')
                assert card['price'] is None and card['affordable'] is None and not card['enabled'], card
            elif scenario == 'fake':
                assert all(item['kind'] == 'relic' for item in items), inventory
            elif scenario == 'full':
                potion = next(item for item in items if item['kind'] == 'potion')
                receipt = await call('buy_item', {'item_id': potion['id']})
                assert receipt['purchase_result']['status'] == 'failure_space', receipt
                assert await details('after_full_potion_refusal') == inventory
            elif scenario == 'nested':
                relic = next(item for item in items if item['kind'] == 'relic' and item['position'] == 'relic:0')
                await call('buy_item', {'item_id': relic['id']})
                await reject('reward_covered')
                await call('proceed', label='proceed_after_read_rejection')
                await details('after_nested_reward')
    print(f'PASS: {args.scenario}; {len(evidence)} recorded calls; {args.report}')


def main():
    parser = argparse.ArgumentParser(description='审阅商店详情、已展示商品和只读失败恢复。')
    parser.add_argument('--scenario', required=True, choices=SCENARIOS)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__': main()
