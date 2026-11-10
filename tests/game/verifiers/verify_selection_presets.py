"""Compare selection presets and act from summaries in an isolated native run."""
from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
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


def compare_summary(full, summary, path=()):
    if isinstance(full, dict):
        assert set(summary) <= set(full), (full, summary)
        card = type(full.get('id')) is int and 'name' in full
        allowed = {'id', 'name', 'type', 'energy_cost', 'star_cost', 'energy_cost_color',
                   'star_cost_color', 'unplayable_markers', 'outline', 'enchantment', 'affliction'}
        comparison = 'before' in path or 'after' in path
        for key, value in full.items():
            omitted = (card and key not in allowed or key == 'hover_tips'
                       or value is None and not (comparison or key in {'before', 'after'} and {'before', 'after'} <= full.keys())
                       or card and key == 'star_cost' and value is None
                       or card and key == 'outline' and value == 'none'
                       or card and key == 'unplayable_markers' and value == []
                       or key in {'bundles', 'upgrade_previews', 'enchant_previews', 'transform_previews'} and value == [])
            assert (key not in summary) == omitted, (path, key, full, summary)
            if key in summary:
                compare_summary(value, summary[key], (*path, key))
    elif isinstance(full, list):
        assert len(full) == len(summary), (full, summary)
        for before, after in zip(full, summary):
            compare_summary(before, after, (*path, '*'))
    else:
        assert full == summary, (full, summary)


def card_lists(choice):
    yield choice['cards']
    for bundle in choice.get('bundles', []):
        yield bundle['cards']
    pairs = ([choice['upgrade_preview']] if choice.get('upgrade_preview') is not None else [])
    for field in ('upgrade_previews', 'enchant_previews', 'transform_previews'):
        pairs += choice.get(field, [])
    for pair in pairs:
        yield [card for card in (pair['before'], pair['after']) if card is not None]


def compare_filter(source, result, requested):
    selected = set(requested)
    before, after = source['selection'], result['selection']
    card_fields = {'cards', 'bundles', 'upgrade_preview', 'upgrade_previews', 'enchant_previews', 'transform_previews'}
    assert {k: v for k, v in before.items() if k not in card_fields} == {
        k: v for k, v in after.items() if k not in card_fields}, (before, after)
    assert after['cards'] == [c for c in before['cards'] if c['id'] in selected]
    assert after.get('bundles', []) == [{**b, 'cards': [c for c in b['cards'] if c['id'] in selected]}
                                         for b in before.get('bundles', [])]
    if 'upgrade_preview' in before:
        pair = before['upgrade_preview']
        assert after.get('upgrade_preview') == (pair if pair and pair['before']['id'] in selected else None)
    for field in ('upgrade_previews', 'enchant_previews', 'transform_previews'):
        if field in before:
            assert after.get(field, []) == [p for p in before[field] if p['before']['id'] in selected]
    known = {c['id'] for cards in card_lists(before) for c in cards}
    missing = list(dict.fromkeys(i for i in requested if i not in known))
    assert result.get('errors') == ([{'code': 'cards_not_in_selection', 'card_ids': missing}] if missing else None)
    if 'hover_tips' in source:
        assert result['hover_tips'] == [{**t, 'card_ids': [i for i in t['card_ids'] if i in selected]}
                                         for t in source['hover_tips'] if selected.intersection(t['card_ids'])]
    else:
        assert 'hover_tips' not in result


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(args.report.parent / 'screenshots')}}))
    evidence = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                response = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = response.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert data == json.loads(response.content[0].text), response
                if error:
                    assert response.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not response.isError and 'error' not in data, data
                return data

            async def presets(label):
                before = await asyncio.to_thread(raw.call, 'get_state')
                await call('capture_screenshot', {'filename': label + '.png'})
                full = await call('inspect_selection')
                assert full == await call('inspect_selection', {'preset': 'full'})
                expanded = await call('get_observation', {'preset': 'full'})
                for cards in card_lists(expanded['selection']):
                    assert all('hover_tips' in card for card in cards if 'description' in card), cards
                for key in ('upgrade_preview', 'upgrade_previews', 'enchant_previews', 'transform_previews'):
                    if expanded['selection'].get(key):
                        assert expanded['selection'][key] == full['selection'][key]
                summary = await call('inspect_selection', {'preset': 'summary'})
                compare_summary(full, summary)
                observed = await call('get_observation', {'preset': 'summary'})
                assert observed['selection'] == summary['selection'], (observed, summary)
                ids = list(dict.fromkeys(c['id'] for cards in card_lists(full['selection']) for c in cards))
                missing = max(ids, default=0) + 100000
                requested = [ids[-1], ids[0], ids[0], missing, missing] if ids else [missing]
                for preset, source in (('full', full), ('summary', summary)):
                    for selected in (requested, []):
                        filtered = await call('inspect_selection', {'preset': preset, 'card_ids': selected})
                        compare_filter(source, filtered, selected)
                after = await asyncio.to_thread(raw.call, 'get_state')
                record({'label': label, 'native_before': before, 'native_after': after})
                assert before['ok'] and after['ok'] and before['state'] == after['state'], 'Presets changed the native UI.'
                return summary['selection']

            state = await call('get_observation')
            if args.scenario.startswith('ancient_'):
                deadline = time.monotonic() + 10
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline, 'Ancient input did not become ready.'
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                option = next(o for o in state['ancient']['options'] if o['enabled'])
                await call('choose_ancient_option', {'option_id': option['id']})
            elif args.scenario in ('discovery', 'hand_upgrade'):
                name = 'Discovery' if args.scenario == 'discovery' else 'Armaments'
                card = next(c for c in state['player']['hand'] if c['name'] == name)
                await call('play_card', {'card_id': card['id']})
            elif args.scenario == 'event_enchant':
                option = next(o for o in state['event']['options'] if o['enabled'])
                await call('choose_event_option', {'option_id': option['id']})
            elif args.scenario == 'smith':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario in ('paels_wing', 'driftwood'):
                rewards = await call('inspect_rewards')
                row = next(r for r in rewards['rewards']['items'] if r['type'] == 'card')
                await call('claim_reward', {'reward_id': row['id']})
            elif args.scenario == 'hand':
                purity = next(c for c in state['player']['hand'] if c['name'] == 'Purity')
                await call('play_card', {'card_id': purity['id']})

            choice = await presets('candidates')
            expected = {'discovery': 'choose_one', 'hand_upgrade': 'hand_upgrade', 'smith': 'deck_upgrade',
                        'ancient_multi': 'deck_enchant', 'event_enchant': 'deck_enchant', 'ancient_transform': 'deck_transform',
                        'ancient_bundle': 'bundle', 'ancient_pandora': 'view_cards',
                        'paels_wing': 'reward', 'driftwood': 'reward', 'grid': 'grid',
                        'combat_pile': 'combat_pile', 'deck': 'deck', 'hand': 'hand'}[args.scenario]
            assert choice['type'] == expected, choice
            if args.scenario in ('paels_wing', 'driftwood'):
                label = 'Sacrifice' if args.scenario == 'paels_wing' else 'Reroll'
                option = next(o for o in choice['options'] if o['text'] == label and o['enabled'])
                result = await call('selection_option', {'option_id': option['id']})
                if args.scenario == 'driftwood':
                    choice = await presets('rerolled')
                    assert not any(o['text'] == 'Reroll' for o in choice['options'])
                    result = await call('select_card', {'card_id': choice['cards'][0]['id']})
                # A terminal reward's Proceed opens the map; finish both offers before resetting.
                assert result['transition']['complete'], result
                remaining = await call('inspect_rewards')
                row = next(r for r in remaining['rewards']['items'] if r['type'] == 'card')
                await call('claim_reward', {'reward_id': row['id']})
                choice = await presets('remaining-reward')
                await call('select_card', {'card_id': choice['cards'][0]['id']})
                result = await call('proceed')
                assert result['screen']['view'] == 'map', result
            elif expected == 'view_cards':
                assert choice['min_select'] == choice['max_select'] == 0
                result = await call('selection_option', {'option_id': 'confirm'})
            elif expected == 'bundle':
                result = await call('selection_option', {'option_id': choice['bundles'][0]['id']})
                choice = await presets('bundle-preview')
                assert choice['cards'] and 'bundles' not in choice, choice
                result = await call('selection_option', {'option_id': 'confirm'})
            else:
                count = max(1, choice['min_select'])
                cards = choice['cards'][-count:]
                assert len(cards) == count, choice
                for card in cards:
                    await call('select_card', {'card_id': card['id']})
                # Native multi-select and preview pages still await explicit confirmation.
                current = await asyncio.to_thread(raw.call, 'get_state')
                if (current['state'].get('selection') or {}).get('status') == 'visible':
                    choice = await presets('preview')
                    if expected == 'deck_transform':
                        assert all(p['random'] and p['after'] is None for p in choice['transform_previews'])
                    if expected == 'hand_upgrade':
                        assert choice['upgrade_preview'] is not None
                        await call('set_selection_view', {'view': 'battlefield'})
                        await call('inspect_selection', {'preset': 'summary'}, error='illegal_action')
                        await call('set_selection_view', {'view': 'selection'})
                        choice = await presets('returned')
                    assert any(o['id'] == 'confirm' and o['enabled'] for o in choice['options']), choice
                    await call('selection_option', {'option_id': 'confirm'})
                # Capture an ordinary read only after the summary-authorized action.
                result = await call('get_observation')
                assert result.get('selection') is None, result
            assert result.get('transition', {}).get('complete', True), result
    print(f'PASS selection presets: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证隔离游戏的选择预设及摘要后的原生动作。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
