"""Verify native selection feedback, boundaries and safe rejection recovery."""
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
    card_names = {}
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

            def changes(result, expected, names=None):
                events = result['transition']['events']
                actual = [e for e in events if e['type'] in {'card_selected', 'card_deselected'}]
                assert [{k: v for k, v in e.items() if k != 'sequence'} for e in actual] == [
                    {'type': kind, 'card': {'id': i, 'name': (card_names if names is None else names)[i]}}
                    for kind, i in expected], result
                assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), result
                return actual

            async def click(card_id, label, expected=None):
                result = await call('select_card', {'card_id': card_id}, label=label)
                assert result['transition']['complete'], result
                selected = changes(result, expected if expected is not None else [('card_selected', card_id)])
                effects = [e for e in result['transition']['events'] if e['type'] not in {'card_selected', 'card_deselected'}]
                if selected and effects:
                    assert selected[-1]['sequence'] < effects[0]['sequence'], result
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
            elif args.scenario in {'choose_one', 'hand_upgrade', 'hand_replace'}:
                name = 'Discovery' if args.scenario == 'choose_one' else 'Armaments'
                card = next(c for c in state['player']['hand'] if c['name'] == name)
                await call('play_card', {'card_id': card['id']})
            elif args.scenario in {'smith', 'upgrade_view'}:
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario == 'enchant_single':
                option = next(o for o in state['event']['options'] if o['enabled'])
                await call('choose_event_option', {'option_id': option['id']})
            elif args.scenario == 'hand':
                purity = next(c for c in state['player']['hand'] if c['name'] == 'Purity')
                await call('play_card', {'card_id': purity['id']})

            if args.scenario == 'no_selection':
                # Local malformed requests retain permission and never reach the adapter.
                await call('select_card', {'card_id': True}, error='invalid_request', label='malformed')
                await call('end_turn', label='after_malformed')
                await call('get_observation')
                rejected = await call('select_card', {'card_id': 0}, error='illegal_action', label='no_selection')
                assert 'selection' in rejected['error']['message'].lower(), rejected
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('end_turn', label='after_unsubmitted_rejection')
                return

            choice = (await call('inspect_selection', {'view_upgrades': True} if args.scenario == 'upgrade_view' else None))['selection']
            cards = choice['cards']
            card_names.update({c['id']: c['name'] for c in cards})
            if args.scenario == 'hand_replace':
                await click(cards[0]['id'], 'select_first')
                _, replaced = await click(cards[1]['id'], 'replace_selected', [
                    ('card_deselected', cards[0]['id']), ('card_selected', cards[1]['id'])])
                assert replaced['selection']['selected_ids'] == [cards[1]['id']], replaced
                result = await call('selection_option', {'option_id': 'confirm'})
                changes(result, [])
                return
            if args.scenario == 'grid_manual':
                native = await asyncio.to_thread(raw.call, 'check_test_selection_input')
                record({'native_input_checks': native})
                assert native['ok'] and native['state']['passed'], native
                await call('inspect_selection')
                await click(cards[0]['id'], 'first_manual')
                _, selected = await click(cards[1]['id'], 'second_manual')
                _, unchanged = await click(cards[2]['id'], 'already_full', [])
                assert unchanged['selection']['selected_ids'] == selected['selection']['selected_ids'], unchanged
                result = await call('selection_option', {'option_id': 'confirm'})
                changes(result, [])
                return
            if args.scenario in {'bundle', 'view_cards'}:
                if args.scenario == 'bundle':
                    target = choice['bundles'][0]['cards'][0]['id']
                else:
                    target = cards[0]['id']
                rejected = await call('select_card', {'card_id': target}, error='illegal_action', label='not_individually_selectable')
                assert ('bundle' if args.scenario == 'bundle' else 'confirm') in rejected['error']['message'].lower(), rejected
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                option = choice['bundles'][0]['id'] if args.scenario == 'bundle' else 'confirm'
                result = await call('selection_option', {'option_id': option}, label='valid_button_after_rejection')
                changes(result, [])
                return
            if args.scenario == 'invalid_candidate':
                before = await asyncio.to_thread(raw.call, 'get_state')
                rejected = await call('select_card', {'card_id': 2147483647}, error='illegal_action', label='unknown_id')
                assert 'candidate' in rejected['error']['message'].lower(), rejected
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                after = await asyncio.to_thread(raw.call, 'get_state')
                record({'label': 'unchanged_rejection', 'before': before, 'after': after})
                assert before['state'] == after['state'], (before, after)
                await click(cards[0]['id'], 'valid_card_after_rejection')
                return
            if args.scenario == 'covered':
                await call('set_selection_view', {'view': 'battlefield'})
                rejected = await call('select_card', {'card_id': cards[0]['id']}, error='illegal_action', label='battlefield')
                assert 'battlefield' in rejected['error']['message'].lower(), rejected
                await call('set_selection_view', {'view': 'selection'})
                await call('set_selection_view', {'view': 'battlefield'})
                await call('inspect_deck')
                rejected = await call('select_card', {'card_id': cards[0]['id']}, error='illegal_action', label='covered')
                assert 'cover' in rejected['error']['message'].lower(), rejected
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
                _, cleared = await click(cards[0]['id'], 'deselect_without_read', [('card_deselected', cards[0]['id'])])
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
                preview = args.scenario in {'deck', 'smith', 'upgrade_view', 'multi_upgrade', 'enchant_single', 'enchant_multi', 'transform'}
                if preview:
                    # Re-clicking a card in a confirmation preview is a preflight rejection.
                    rejected = await call('select_card', {'card_id': selected_cards[0]['id']}, error='illegal_action', label='preview_rejection')
                    assert 'preview' in rejected['error']['message'].lower(), rejected
                    canceled = await call('selection_option', {'option_id': 'cancel_preview'}, label='cancel_after_preview_rejection')
                    # These multi-card previews display only result faces, leaving originals unknown.
                    names = {c['id']: None for c in selected_cards} if args.scenario in {'multi_upgrade', 'enchant_multi'} else None
                    if args.scenario == 'upgrade_view':
                        assert selected_cards[0]['name'] == 'Bash+', selected_cards
                        names = {selected_cards[0]['id']: 'Bash'}
                    changes(canceled, [('card_deselected', c['id']) for c in selected_cards], names=names)
                    for card in selected_cards:
                        result, after = await click(card['id'], 'reselect_after_cancel')
                result = await call('selection_option', {'option_id': 'confirm'}, label='confirm')
                changes(result, [])
            expected = {'combat_entry': 'player_ready'}.get(args.scenario)
            assert result['transition']['complete'], result
            if expected:
                assert result['transition']['stop_reason'] == expected, result
            observed = await call('get_observation')
            assert observed.get('selection') is None

    print(f'PASS select_card review: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
