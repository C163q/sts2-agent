"""Verify selection button outcomes, public diagnostics and safe preflight recovery."""
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
from tests.game.support.verification_actions import completed_action_state
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'label': label, 'result': result})
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                if 'transition' in result:
                    assert result['transition']['complete'], result
                    state = completed_action_state(raw.directory, result)
                    record({'label': label or tool, 'native_action_state': state})
                return result

            async def option(value, label):
                return await call('selection_option', {'option_id': value}, label=label)

            async def inspect(label='selection'):
                return (await call('inspect_selection', label=label))['selection']

            async def rejected(value, label, message):
                result = await call('selection_option', {'option_id': value}, error='illegal_action', label=label)
                assert message in result['error']['message'], result
                assert result['error']['recovery'] == 'choose_legal_action', result

            if args.scenario == 'no_selection':
                await call('selection_option', {'option_id': 'confirm'}, error='observation_required', label='no_permission')
            state = await call('get_observation', label='initial')
            if args.scenario == 'no_selection':
                for value in ('', ' ', 1, None, 'x' * 129):
                    await call('selection_option', {'option_id': value}, error='invalid_request', label='malformed')
                await call('end_turn', label='after_local_rejection')
                await call('get_observation')
                await rejected('confirm', 'no_selection', 'No card selection')
                await call('end_turn', label='after_unsubmitted_rejection')
                return

            if args.scenario in {'bundle', 'view_cards', 'enchant_multi', 'transform'}:
                deadline = time.monotonic() + 15
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline, state
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                chosen = next(o for o in state['ancient']['options'] if o['enabled'])
                await call('choose_ancient_option', {'option_id': chosen['id']})
            elif args.scenario in {'choose_skip', 'hand_upgrade'}:
                name = 'Discovery' if args.scenario == 'choose_skip' else 'Armaments'
                card = next(c for c in state['player']['hand'] if c['name'] == name)
                await call('play_card', {'card_id': card['id']})
            elif args.scenario == 'smith':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario == 'enchant_single':
                chosen = next(o for o in state['event']['options'] if o['enabled'])
                await call('choose_event_option', {'option_id': chosen['id']})
            elif args.scenario in {'hand_zero', 'hand_one', 'death', 'victory'}:
                await call('end_turn')
            elif args.scenario == 'shop_remove':
                await call('open_shop')
                shop = (await call('inspect_shop'))['shop']
                removal = next(item for item in shop['items'] if item['kind'] == 'card_removal')
                await call('buy_item', {'item_id': removal['id']})

            selection = await inspect()
            if args.scenario in {'invalid_option', 'disabled', 'battlefield', 'covered'}:
                if args.scenario in {'battlefield', 'covered'}:
                    await call('set_selection_view', {'view': 'battlefield'})
                    if args.scenario == 'covered':
                        await call('inspect_deck')
                if args.scenario == 'disabled':
                    assert not any(o['id'] == 'confirm' and o['enabled'] for o in selection['options']), selection
                message = 'not offered' if args.scenario in {'invalid_option', 'disabled'} else (
                    'battlefield' if args.scenario == 'battlefield' else 'covered')
                await rejected('not_offered' if args.scenario == 'invalid_option' else 'confirm', args.scenario, message)
                if args.scenario == 'covered':
                    await call('close_card_view')
                if args.scenario in {'battlefield', 'covered'}:
                    await call('set_selection_view', {'view': 'selection'})
                if args.scenario == 'invalid_option':
                    await call('select_card', {'card_id': selection['cards'][0]['id']}, label='valid_card_after_rejection')
                elif args.scenario == 'disabled':
                    for card in selection['cards'][:selection['min_select']]:
                        await call('select_card', {'card_id': card['id']}, label='select_after_rejection')
                    await option('confirm', 'confirm_after_rejection')
                else:
                    await inspect('after_rejection')
                return

            if args.scenario in {'choose_skip', 'reward_skip'}:
                assert any(o['id'] == 'skip' and o['enabled'] for o in selection['options']), selection
                result = await option('skip', 'skip')
            elif args.scenario == 'view_cards':
                result = await option('confirm', 'confirm_results')
            elif args.scenario == 'bundle':
                bundles = [o for o in selection['options'] if o['id'].startswith('bundle:') and o['enabled']]
                assert len(bundles) > 1, selection
                result = await option(bundles[0]['id'], 'select_bundle')
                preview = await inspect('bundle_preview')
                assert preview['selected_ids'], preview
                result = await option('cancel_preview', 'cancel_bundle')
                assert (await inspect('bundles_again'))['selected_ids'] == []
                await option(bundles[1]['id'], 'reselect_bundle_without_read')
                result = await option('confirm', 'confirm_bundle')
                assert any(e['type'] == 'card_added' and e['pile'] == 'deck' for e in result['transition']['events']), result
            elif args.scenario == 'deck_cancel':
                assert any(o['id'] == 'cancel' and o['enabled'] for o in selection['options']), selection
                result = await option('cancel', 'cancel_selection')
            elif args.scenario == 'hand_zero':
                assert selection['min_select'] == 0 and selection['selected_ids'] == [], selection
                result = await option('confirm', 'confirm_zero_cards')
            else:
                count = max(1, selection['min_select'])
                selected = selection['cards'][-count:]
                for card in selected:
                    await call('select_card', {'card_id': card['id']}, label='choose_candidate')
                if args.scenario in {'deck_preview', 'shop_remove', 'smith', 'multi_upgrade', 'enchant_single', 'enchant_multi', 'transform'}:
                    await inspect('preview')
                    canceled = await option('cancel_preview', 'cancel_preview')
                    assert len([e for e in canceled['transition']['events'] if e['type'] == 'card_deselected']) == count, canceled
                    assert (await inspect('candidates_again'))['selected_ids'] == []
                    for card in selected:
                        await call('select_card', {'card_id': card['id']}, label='reselect')
                if args.scenario == 'grid_manual':
                    checks = await asyncio.to_thread(raw.call, 'check_test_selection_options')
                    record({'native_option_checks': checks})
                    assert checks['ok'] and checks['state']['passed'], checks
                result = await option('confirm', 'confirm')
                assert not any(e['type'] == 'card_deselected' for e in result['transition']['events']), result
                if args.scenario == 'shop_remove':
                    kinds = {e['type'] for e in result['transition']['events']}
                    assert {'card_removed', 'gold_changed'} <= kinds, result

            expected = {'death': 'combat_lost', 'victory': 'combat_won'}.get(args.scenario)
            if expected:
                assert result['transition']['stop_reason'] == expected, result
            state = await call('get_observation', label='after')
            assert state.get('selection') is None, state
            if args.scenario == 'reward_skip':
                # Skipping candidates returns to the still-pending reward set.
                assert state['scene'] == 'rewards' and 'proceed' in state['available_actions'], state
                await call('proceed', label='leave_skipped_reward')
            if args.scenario == 'victory':
                deadline = time.monotonic() + 15
                while state['scene'] != 'rewards' or 'proceed' not in state['available_actions']:
                    assert time.monotonic() < deadline, state
                    await asyncio.sleep(.1)
                    state = await call('get_observation')

    print(json.dumps({'scenario': args.scenario, 'records': len(evidence)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
