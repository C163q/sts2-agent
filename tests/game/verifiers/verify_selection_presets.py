"""Compare selection presets and act from summaries in an isolated native run."""
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


def compare_summary(full, summary):
    if isinstance(full, dict):
        if type(full.get('id')) is int and 'name' in full:
            allowed = {'id', 'name', 'type', 'energy_cost', 'star_cost', 'energy_cost_color',
                       'star_cost_color', 'unplayable_markers', 'outline', 'enchantment'}
            assert set(summary) == (set(full) & allowed) - ({'star_cost'} if full.get('star_cost') is None else set())
            assert summary['id'] == full['id'] and summary['name'] == full['name']
            assert all(value == full[key] for key, value in summary.items()), (full, summary)
        else:
            assert set(summary) == set(full) - {'hover_tips'}, (full, summary)
            for key in summary:
                compare_summary(full[key], summary[key])
    elif isinstance(full, list):
        assert len(full) == len(summary), (full, summary)
        for before, after in zip(full, summary):
            compare_summary(before, after)
    else:
        assert full == summary, (full, summary)


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
                response = await session.call_tool(name, arguments or {})
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
                summary = await call('inspect_selection', {'preset': 'summary'})
                compare_summary(full, summary)
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
            elif args.scenario == 'smith':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario in ('paels_wing', 'driftwood'):
                rewards = await call('inspect_rewards')
                row = next(r for r in rewards['rewards']['items'] if r['type'] == 'card')
                await call('claim_reward', {'reward_id': row['id']})
            elif args.scenario == 'hand':
                await call('end_turn')

            choice = await presets('candidates')
            expected = {'discovery': 'choose_one', 'hand_upgrade': 'hand_upgrade', 'smith': 'deck_upgrade',
                        'ancient_multi': 'deck_enchant', 'ancient_transform': 'deck_transform',
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
                assert choice['cards'] and not choice['bundles'], choice
                result = await call('selection_option', {'option_id': 'confirm'})
            else:
                count = 3 if expected == 'deck_enchant' else 1
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
