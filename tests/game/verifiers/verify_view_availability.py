"""Check offered inspections and native deck/map round trips across rooms."""
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
from sts2_mcp.output.available_tools import INSPECTIONS, GAME_ACTIONS
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
        'directory': str(args.report.parent / 'screenshots')}}))
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                reply = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = reply.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert data == json.loads(reply.content[0].text), reply
                if error:
                    assert reply.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not reply.isError and 'error' not in data, data
                return data

            async def offered(label, expected_actions=None):
                deadline = time.monotonic() + 10
                while True:
                    state = await call('get_observation')
                    compact = await call('get_observation', {'preset': 'actions_only'})
                    expected = {k: state[k] for k in ('scene', 'screen', 'available_actions')}
                    if state.get('selection'):
                        expected['selection'] = {k: state['selection'][k] for k in ('type', 'status')}
                    if compact == expected and (expected_actions is None
                                               or state['available_actions'] == expected_actions):
                        break
                    assert time.monotonic() < deadline, (label, state, compact, expected_actions)
                    await asyncio.sleep(.1)
                before = await asyncio.to_thread(raw.call, 'get_state')
                for tool in state['available_actions']:
                    if tool in INSPECTIONS - {'inspect_targets'}:
                        await call(tool)
                if 'inspect_targets' in state['available_actions']:
                    hand = (state.get('player') or {}).get('hand') or []
                    if hand:
                        await call('inspect_targets', {'card_id': hand[0]['id']})
                    else:
                        slots = state['top_bar']['potion_slots']
                        slot = next(i for i, p in enumerate(slots) if p is not None)
                        await call('inspect_targets', {'potion_slot': slot})
                after = await asyncio.to_thread(raw.call, 'get_state')
                assert before['state'] == after['state'], f'{label}: inspection changed state'
                await call('capture_screenshot', {'filename': label + '.png'})
                return state

            state = await call('get_observation')
            if args.scenario == 'confirmation':
                summary = await call('get_observation', {'preset': 'summary'})
                assert 'description' not in state['event'] and 'description' not in summary['event'], summary
                assert all('description' in option for option in summary['event']['options']), summary
                await call('choose_event_option', {'option_id': state['event']['options'][1]['id']})
                state = await call('get_observation')
                summary = await call('get_observation', {'preset': 'summary'})
                assert 'description' not in state['event'] and 'description' not in summary['event'], summary
                option = next(o for o in state['event']['options'] if o['enabled'] and o.get('lethal_warning'))
                await call('choose_event_option', {'option_id': option['id']})
                covered = await offered('confirmation')
                assert covered['available_actions'] == ['respond_to_confirmation'], covered
                summary = await call('get_observation', {'preset': 'summary'})
                assert summary['confirmation']['description'] == covered['confirmation']['description'], summary
                assert summary['event'] == {'status': 'covered'}, summary
                for tool in ('inspect_relics', 'inspect_potions', 'inspect_deck', 'inspect_map'):
                    await call(tool, error='illegal_action')
                await call('get_observation')
                await call('respond_to_confirmation', {'option': 'cancel'})
                restored = await offered('cancelled')
                assert {'inspect_relics', 'inspect_deck'} <= set(restored['available_actions']), restored
                return
            if args.scenario == 'epilogue':
                await call('proceed')
            if args.scenario == 'shop':
                await call('open_shop')
            elif args.scenario == 'selection':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario == 'result':
                await call('end_turn')
                deadline = time.monotonic() + 20
                while True:
                    state = await call('get_observation')
                    if (state.get('run_result') or {}).get('status') == 'visible':
                        break
                    assert time.monotonic() < deadline, state
                    await asyncio.sleep(.1)
            state = await offered('initial')
            assert 'inspect_relics' in state['available_actions'], state
            if args.scenario in ('selection', 'result'):
                assert 'inspect_deck' not in state['available_actions'], state
                await call('inspect_deck', error='illegal_action')
                return
            assert 'inspect_deck' in state['available_actions'], state
            original_scene = state['scene']
            deck = await call('inspect_deck')
            assert deck['deck'], deck
            covered = await offered('deck')
            assert covered['screen'] == {'status': 'covered', 'view': 'deck'}, covered
            assert not set(covered['available_actions']) & GAME_ACTIONS, covered
            assert 'close_card_view' in covered['available_actions'], covered
            if args.scenario == 'epilogue':
                assert {'inspect_potions', 'inspect_relics'} <= set(covered['available_actions']), covered
                for preset in ('default', 'full', 'summary', 'actions_only', 'top_bar'):
                    projected = await call('get_observation', {'preset': preset})
                    assert projected['screen'] == {'status': 'covered', 'view': 'deck'}, projected
                    assert projected['available_actions'] == covered['available_actions'], projected
                    if preset in ('default', 'summary'):
                        assert projected['epilogue'] == {'status': 'covered'}, projected
                await call('advance_dialogue', error='illegal_action')
                await call('get_observation')
            assert await call('inspect_deck') == deck
            await call('inspect_deck', {'sort_by': 'name', 'descending': True, 'view_upgrades': True})
            closed = await call('close_card_view')
            assert closed['scene'] == original_scene, closed
            restored = await offered('restored', state['available_actions'])
            assert restored['available_actions'] == state['available_actions'], (restored, state)

            if 'inspect_map' in restored['available_actions']:
                await call('inspect_map')
                mapped = await offered('map')
                assert 'inspect_deck' in mapped['available_actions'], mapped
                await call('inspect_deck')
                over_map = await call('get_observation')
                assert over_map['screen']['view'] == 'deck', over_map
                assert over_map.get('map') is None, over_map
                closed = await call('close_card_view')
                assert closed['screen'] == {'status': 'covered', 'view': 'map'}, closed
                # Opening the map from a deck page must replace the covering page natively.
                await call('inspect_deck')
                await call('inspect_map')
                mapped = await offered('map-from-deck')
                if 'close_map' not in mapped['available_actions']:
                    await call('close_map', error='illegal_action')
                    return
                await call('close_map')
                await offered('map-closed')

            if args.scenario == 'treasure':
                await call('inspect_relics')
                receipt = await call('loot_treasure')
                assert receipt['transition']['complete'], receipt
            elif args.scenario == 'reward':
                # Terminal Proceed only opens the map; leaving the room completes Offer.
                await call('inspect_rewards')
                receipt = await call('proceed')
                assert receipt['transition']['complete'], receipt
                mapped = await call('inspect_map', {'preset': 'selectable'})
                receipt = await call('travel_to_node', {'node_id': mapped['selectable_nodes'][0]})
                assert receipt['transition']['complete'], receipt
            elif args.scenario == 'combat':
                await call('inspect_relics')
                receipt = await call('end_turn')
                assert receipt['transition']['complete'], receipt
    print('PASS available tools:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证可用查看工具与页面切换。')
    parser.add_argument('--scenario', choices=('epilogue', 'confirmation', 'event', 'rest', 'treasure', 'reward', 'shop', 'ancient',
                                             'selection', 'combat', 'result'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
