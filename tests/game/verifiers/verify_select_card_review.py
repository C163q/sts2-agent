"""Record native card selection outcomes, boundaries and rejection recovery."""
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
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                data = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'label': label, 'result': data})
                assert data == json.loads(response.content[0].text), response
                assert response.isError == bool(error), data
                assert data.get('error', {}).get('code') == error, data
                return data

            async def click(card_id, label):
                result = await call('select_card', {'card_id': card_id}, label=label)
                assert result['transition']['complete'], result
                # Read the exact response without granting a new MCP permission.
                state = completed_action_state(raw.directory, result)
                record({'label': label, 'native_action_state': state})
                return result, state

            if args.scenario == 'no_selection':
                await call('select_card', {'card_id': 0}, error='observation_required', label='no_permission')
            state = await call('get_observation')
            if args.scenario in {'bundle', 'view_cards', 'enchant_multi', 'transform'}:
                deadline = time.monotonic() + 15
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline, state
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                option = next(o for o in state['ancient']['options'] if o['enabled'])
                await call('choose_ancient_option', {'option_id': option['id']})
            elif args.scenario in {'choose_one', 'hand_upgrade'}:
                name = 'Discovery' if args.scenario == 'choose_one' else 'Armaments'
                card = next(c for c in state['player']['hand'] if c['name'] == name)
                await call('play_card', {'card_id': card['id']})
            elif args.scenario == 'smith':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario == 'enchant_single':
                option = next(o for o in state['event']['options'] if o['enabled'])
                await call('choose_event_option', {'option_id': option['id']})
            elif args.scenario in {'hand', 'death', 'victory'}:
                await call('end_turn')

            if args.scenario == 'no_selection':
                # Local malformed requests retain permission and never reach the adapter.
                await call('select_card', {'card_id': True}, error='invalid_request', label='malformed')
                await call('end_turn', label='after_malformed')
                await call('get_observation')
                await call('select_card', {'card_id': 0}, error='illegal_action', label='no_selection')
                await call('end_turn', error='observation_required', label='after_unsubmitted_rejection')
                return

            choice = (await call('inspect_selection'))['selection']
            cards = choice['cards']
            if args.scenario in {'bundle', 'view_cards'}:
                if args.scenario == 'bundle':
                    target = choice['bundles'][0]['cards'][0]['id']
                else:
                    target = cards[0]['id']
                await call('select_card', {'card_id': target}, error='illegal_action', label='not_individually_selectable')
                option = choice['bundles'][0]['id'] if args.scenario == 'bundle' else 'confirm'
                await call('selection_option', {'option_id': option}, error='observation_required', label='valid_button_after_rejection')
                return
            if args.scenario == 'invalid_candidate':
                before = await asyncio.to_thread(raw.call, 'get_state')
                await call('select_card', {'card_id': 2147483647}, error='illegal_action', label='unknown_id')
                after = await asyncio.to_thread(raw.call, 'get_state')
                record({'label': 'unchanged_rejection', 'before': before, 'after': after})
                assert before['state'] == after['state'], (before, after)
                await call('select_card', {'card_id': cards[0]['id']}, error='observation_required', label='valid_card_after_rejection')
                return
            if args.scenario == 'covered':
                await call('set_selection_view', {'view': 'battlefield'})
                await call('select_card', {'card_id': cards[0]['id']}, error='illegal_action', label='battlefield')
                await call('set_selection_view', {'view': 'selection'})
                await call('set_selection_view', {'view': 'battlefield'})
                await call('inspect_deck')
                await call('select_card', {'card_id': cards[0]['id']}, error='illegal_action', label='covered')
                return
            if args.scenario == 'scroll_race':
                result = await asyncio.to_thread(raw.call, 'check_test_selection_race')
                record({'native_scroll_race': result})
                assert result['ok'] and result['state']['passed'], result
                return

            if args.scenario == 'chain':
                before = await asyncio.to_thread(raw.call, 'get_state')
                first, after = await click(cards[0]['id'], 'first_choice')
                assert first['transition']['stop_reason'] == 'choice_required', first
                assert before['state']['selection_generation'] != after['selection_generation']
                stale = await asyncio.to_thread(raw.call, 'select_card', before['state']['snapshot_id'],
                                                arguments={'card_id': cards[0]['id']})
                record({'native_stale_rejection': stale})
                assert not stale['ok'] and stale['error']['code'] == 'stale_state', stale
                result, _ = await click(cards[0]['id'], 'second_choice_without_read')
                assert result['transition']['stop_reason'] == 'player_ready', result
                return

            count = max(1, choice['min_select'])
            if args.scenario in {'grid', 'hand', 'hand_upgrade', 'multi_upgrade', 'enchant_multi'} or (
                    args.scenario == 'transform' and choice['max_select'] > 1):
                first, selected = await click(cards[0]['id'], 'select_first')
                assert selected['selection']['selected_ids'] == [cards[0]['id']], selected
                if args.scenario == 'hand_upgrade':
                    assert selected['selection']['upgrade_preview'] is not None, selected
                _, cleared = await click(cards[0]['id'], 'deselect_without_read')
                assert cleared['selection']['selected_ids'] == [], cleared
                if args.scenario == 'hand_upgrade':
                    assert cleared['selection']['upgrade_preview'] is None, cleared
            selected_cards = cards[-count:]
            if args.scenario == 'scroll':
                selected_cards = cards[-1:]
            for card in selected_cards:
                result, after = await click(card['id'], 'choose_candidate')
            current = after.get('selection')
            if current and current['status'] == 'visible':
                assert result['transition']['stop_reason'] == 'choice_required', result
                assert set(current['selected_ids']) == {c['id'] for c in selected_cards}, current
                preview = args.scenario in {'deck', 'smith', 'multi_upgrade', 'enchant_single', 'enchant_multi', 'transform'}
                if preview:
                    # Re-clicking a card in a confirmation preview is a preflight rejection.
                    await call('select_card', {'card_id': selected_cards[0]['id']}, error='illegal_action', label='preview_rejection')
                    await call('selection_option', {'option_id': 'confirm'}, error='observation_required', label='confirm_after_preview_rejection')
                    await call('inspect_selection')
                result = await call('selection_option', {'option_id': 'confirm'}, label='confirm')
            expected = {'death': 'combat_lost', 'victory': 'combat_won', 'combat_entry': 'player_ready'}.get(args.scenario)
            assert result['transition']['complete'], result
            if expected:
                assert result['transition']['stop_reason'] == expected, result
            assert (await call('get_observation')).get('selection') is None
    print(f'PASS select_card review: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
