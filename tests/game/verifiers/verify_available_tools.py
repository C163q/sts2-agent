from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from tests.game.support.verification_actions import observe_after_action
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client


async def verify(args):
    root = ROOT
    report = args.report.resolve()
    if report.exists() or report.with_suffix('').exists():
        raise ValueError('Use a fresh report and screenshot directory.')
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.with_suffix(''))}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    observed = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while observed['state']['scene'] == 'unrecognized' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        observed = await asyncio.to_thread(raw.call, 'get_state')
    assert observed['state']['scene'] == 'main_menu', 'Requires a fresh isolated test game.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', observed['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[str(root / 'scripts/mcp_server.py'),
                                  '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            public = {t.name for t in (await session.list_tools()).tools} - {'get_observation', 'capture_screenshot'}

            async def call(name, arguments=None):
                result = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = result.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert data == json.loads(result.content[0].text), result
                assert not result.isError, data
                if name == 'get_observation' and arguments == {'preset': 'actions_only'}:
                    assert [item.type for item in result.content] == ['text'], result
                elif (data.get('divination') or {}).get('status') == 'visible':
                    assert [item.type for item in result.content] == ['text', 'image'], result
                return data

            async def check(label, required=(), forbidden=()):
                full = await call('get_observation')
                actions = full['available_actions']
                assert set(actions) <= public and len(actions) == len(set(actions)), full
                assert set(required) <= set(actions), (label, 'missing', sorted(set(required) - set(actions)), full)
                assert not set(forbidden) & set(actions), (label, 'forbidden', full)
                compact = await call('get_observation', {'preset': 'actions_only'})
                expected = {key: full[key] for key in ('scene', 'screen', 'available_actions')}
                if full.get('selection') is not None:
                    expected['selection'] = {key: full['selection'][key] for key in ('type', 'status')}
                assert compact == expected, (label, compact, expected)
                for name in actions:
                    if name.startswith('inspect_') and name not in {'inspect_deck', 'inspect_pile', 'inspect_map', 'inspect_targets'}:
                        await call(name)
                await call('capture_screenshot', {'filename': label + '.png'})
                return full

            combat_forbidden = {'play_card', 'end_turn', 'use_potion', 'discard_potion'}
            if args.scenario == 'combat':
                await check('combat', {'inspect_hand', 'inspect_ui', 'inspect_combatants', 'inspect_relics', 'inspect_potions',
                                       'inspect_targets', 'inspect_deck', 'inspect_pile', 'inspect_map', 'play_card', 'end_turn'})
                await call('inspect_deck')
                await check('deck', {'inspect_deck', 'inspect_pile', 'close_card_view', 'inspect_map'}, combat_forbidden | {'inspect_hand'})
                await call('close_card_view')
                await call('inspect_pile', {'pile': 'draw'})
                await check('draw-pile', {'inspect_deck', 'inspect_pile', 'close_card_view', 'inspect_map'}, combat_forbidden | {'inspect_hand'})
                await call('close_card_view')
                await call('inspect_map')
                await check('map', {'inspect_map', 'close_map', 'inspect_deck'}, combat_forbidden | {'inspect_hand', 'inspect_pile'})
                await call('close_map')
                final = await check('returned', {'play_card', 'inspect_targets'})
                card = final['player']['hand'][0]
                await call('inspect_targets', {'card_id': card['id']})
            elif args.scenario in {'selection', 'upgrade'}:
                if args.scenario == 'upgrade':
                    full = await call('get_observation')
                    card = next(c for c in full['player']['hand'] if c['name'] == 'Armaments')
                    await call('play_card', {'card_id': card['id']})
                full = await check('selection', {'inspect_selection', 'select_card', 'set_selection_view'}, combat_forbidden | {'inspect_hand'})
                assert full['selection']['status'] == 'visible', full
                await call('set_selection_view', {'view': 'battlefield'})
                await check('battlefield', {'inspect_hand', 'inspect_combatants', 'inspect_ui', 'inspect_deck', 'inspect_pile', 'set_selection_view'},
                            combat_forbidden | {'inspect_selection', 'select_card', 'selection_option', 'inspect_targets'})
                await call('inspect_deck')
                await check('selection-covered', {'close_card_view', 'inspect_deck'}, combat_forbidden | {'inspect_selection', 'select_card', 'set_selection_view'})
                await call('close_card_view')
                await call('set_selection_view', {'view': 'selection'})
                await check('selection-returned', {'inspect_selection', 'select_card', 'set_selection_view'}, combat_forbidden)
            elif args.scenario == 'shop':
                await check('merchant', {'open_shop', 'inspect_map'}, {'inspect_shop', 'buy_item'})
                await call('get_observation')
                await call('open_shop')
                await check('inventory', {'inspect_shop', 'buy_item', 'close_shop'}, {'open_shop', 'play_card'})
                await call('get_observation')
                await call('close_shop')
                await check('merchant-returned', {'open_shop'}, {'inspect_shop', 'buy_item'})
            elif args.scenario == 'confirmation':
                full = await check('event', {'inspect_event', 'choose_event_option'})
                await call('get_observation')
                full = await observe_after_action(call, await call('choose_event_option', {'option_id': full['event']['options'][1]['id']}))
                option = next(o for o in full['event']['options'] if o['enabled'] and o['lethal_warning'])
                await call('get_observation'); await call('choose_event_option', {'option_id': option['id']})
                await check('confirmation', {'respond_to_confirmation'}, public - {'respond_to_confirmation'})
            elif args.scenario == 'ending':
                await check('result', {'inspect_run_result', 'run_result_option'}, combat_forbidden | {'inspect_map', 'inspect_hand', 'inspect_deck'})
            elif args.scenario == 'map':
                full = await call('get_observation')
                if full.get('map') is None: await call('inspect_map')
                await check('travel-map', {'inspect_map', 'travel_to_node'}, combat_forbidden | {'inspect_hand'})
            elif args.scenario in {'map_potions', 'epilogue'}:
                if args.scenario == 'epilogue':
                    await call('get_observation'); await call('proceed')
                else:
                    deadline = time.monotonic() + 15
                    while 'inspect_map' not in (await call('get_observation'))['available_actions'] and time.monotonic() < deadline:
                        await asyncio.sleep(.1)
                required = {'inspect_potions', 'inspect_targets', 'use_potion', 'discard_potion', 'inspect_map'}
                full = await check(args.scenario, required, {'play_card', 'end_turn', 'inspect_hand'})
                target = await call('inspect_targets', {'potion_slot': 0})
                assert target['usable'] and not target['requires_target'], target
                await call('get_observation')
                following = await observe_after_action(call, await call('use_potion', {'potion_slot': 0}))
                assert following['top_bar']['max_hp'] == full['top_bar']['max_hp'] + 5, following
                await check(args.scenario + '-used', required, {'play_card', 'end_turn'})
                await call('get_observation'); await call('discard_potion', {'potion_slot': 2})
                if args.scenario == 'epilogue':
                    await call('inspect_map')
                    await check('epilogue-map', {'inspect_potions', 'inspect_targets', 'use_potion', 'discard_potion', 'close_map'})
                    await call('close_map')
                    await check('epilogue-returned', {'inspect_potions', 'inspect_targets'})
            elif args.scenario == 'divination':
                full = await call('get_observation')
                await call('choose_event_option', {'option_id': full['event']['options'][0]['id']})
                await check('divination', {'inspect_event', 'set_divination_tool', 'divine'}, {'choose_event_option'})
            else:
                tools = {'rewards': 'inspect_rewards', 'rest': 'inspect_rest_site', 'treasure': 'inspect_treasure',
                         'ancient': 'inspect_ancient', 'event': 'inspect_event', 'divination': 'inspect_event'}
                await check(args.scenario, {tools[args.scenario]}, {'play_card', 'end_turn', 'inspect_hand'})
    print('PASS', args.scenario, len(evidence), 'MCP calls')


def main():
    parser = argparse.ArgumentParser(description='检查隔离游戏当前可用工具与完整/精简观察。')
    parser.add_argument('--scenario', choices=('combat', 'selection', 'upgrade', 'shop', 'confirmation', 'ending', 'map', 'map_potions', 'epilogue',
                                              'rewards', 'rest', 'treasure', 'ancient', 'event', 'divination'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
