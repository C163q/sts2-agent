"""Read exposed top bars through map and card browsers without crossing action layers."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.output.presets import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
        'directory': str(args.report.parent / 'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            def record(value):
                evidence.append(value)
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')

            async def call(tool, arguments=None, error=None):
                arguments = arguments or {}
                if tool != 'capture_screenshot':
                    arguments = {'preset': 'full', **arguments}
                reply = await session.call_tool(tool, arguments)
                data = reply.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': data})
                assert json.loads(reply.content[0].text) == data
                if error:
                    assert reply.isError and data['error']['code'] == error, data
                else:
                    assert not reply.isError and 'error' not in data, (tool, data)
                return data

            async def check(view, label, baseline):
                full = await call('get_observation')
                evidence[-1]['label'] = label
                record({'label_screenshot': label})
                await call('capture_screenshot', {'filename': label + '.png'})
                assert full['screen']['view'] == view
                assert full['top_bar'] is not None, (label, full)
                for field in ('hp', 'max_hp', 'gold', 'deck_count', 'relic_count'):
                    assert full['top_bar'][field] == baseline[field], (label, field, full)
                assert 'play_card' not in full['available_actions'] and 'end_turn' not in full['available_actions']
                if full['scene'] == 'combat' or view != 'map':
                    assert not {'use_potion', 'discard_potion', 'inspect_targets'} & set(full['available_actions'])
                assert full['player'] is None and full['enemies'] is None
                before = await asyncio.to_thread(raw.call, 'get_state')
                compact = await call('get_observation', {'preset': 'summary'})
                assert compact == apply_preset(full, 'default'), label
                top = await call('get_observation', {'preset': 'top_bar'})
                assert top['top_bar'] == {k: v for k, v in apply_preset(full, 'default')['top_bar'].items() if k != 'relics'}
                actions = await call('get_observation', {'preset': 'actions_only'})
                assert 'top_bar' not in actions and actions['available_actions'] == full['available_actions']
                assert {'inspect_potions', 'inspect_relics'} <= set(full['available_actions']), full
                potions = await call('inspect_potions')
                assert [p['name'] if p else None for p in potions['potion_slots']] == [
                    p['name'] if p else None for p in full['top_bar']['potion_slots']]
                relics = await call('inspect_relics')
                assert [r['name'] for r in relics['relics']] == [r['name'] for r in full['top_bar']['relics']]
                checks = await asyncio.to_thread(raw.call, 'check_test_top_bar')
                record({'native_checks': checks, 'view': view, 'label': label})
                assert checks['ok'] and checks['state']['passed'], checks
                after = await asyncio.to_thread(raw.call, 'get_state')
                assert before['state'] == after['state'], (label, 'Reads changed state')
                return full

            initial = await call('get_observation')
            baseline = initial['top_bar']
            assert baseline is not None
            if args.scenario == 'confirmation':
                await call('choose_event_option', {'option_id': initial['event']['options'][1]['id']})
                state = await call('get_observation')
                option = next(o for o in state['event']['options'] if o['enabled'] and o['lethal_warning'])
                await call('choose_event_option', {'option_id': option['id']})
                state = await call('get_observation')
                assert state['screen']['view'] == 'confirmation' and state['top_bar'] is None
                assert state['available_actions'] == ['respond_to_confirmation']
                await call('capture_screenshot', {'filename': 'confirmation.png'})
                for tool in ('inspect_potions', 'inspect_relics'):
                    await call(tool, error='illegal_action')
                await call('get_observation')
                await call('respond_to_confirmation', {'option': 'cancel'})
                assert (await call('get_observation'))['top_bar'] is not None
                return
            if args.scenario == 'entry':
                await call('proceed')
                state = await call('get_observation')
                assert state['map']['act'] == 2 and 'close_map' not in state['available_actions']
                baseline = state['top_bar']
                await check('map', 'forced-map', baseline)
                await call('inspect_deck')
                await check('deck', 'deck-over-forced-map', baseline)
                await call('close_card_view')
                graph = await call('inspect_map')
                await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]})
                return
            if args.scenario == 'selection':
                card = next(c for c in initial['player']['hand'] if c['name'] == 'Discovery')
                await call('play_card', {'card_id': card['id']})
                await call('set_selection_view', {'view': 'battlefield'})
            elif args.scenario == 'divination':
                await call('choose_event_option', {'option_id': initial['event']['options'][0]['id']})
                baseline = (await call('get_observation'))['top_bar']
            await call('inspect_map')
            mapped = await check('map', 'map', baseline)
            if initial['scene'] == 'combat':
                await call('end_turn', error='illegal_action')
                await call('inspect_potions')
                await call('use_potion', {'potion_slot': 0}, error='illegal_action')
            await call('inspect_deck')
            covered = await check('deck', 'deck-over-map', baseline)
            assert covered['map'] is None
            await call('end_turn', error='illegal_action')
            await call('inspect_potions')
            await call('use_potion', {'potion_slot': 0}, error='illegal_action')
            await call('close_card_view')
            assert (await call('get_observation'))['map'] == mapped['map']
            await call('close_map')
            await call('inspect_deck')
            await check('deck', 'deck', baseline)
            await call('close_card_view')
            if args.scenario == 'combat':
                await call('inspect_pile', {'pile': 'draw'})
                await check('draw_pile', 'draw-pile', baseline)
                await call('close_card_view')
                hand = await call('inspect_hand')
                defend = next(c for c in hand['hand'] if c['name'] == 'Defend')
                await call('play_card', {'card_id': defend['id']})
                await call('inspect_pile', {'pile': 'discard'})
                await check('discard_pile', 'discard-pile', baseline)
                await call('close_card_view')
            elif args.scenario == 'selection':
                state = await call('get_observation')
                assert state['selection']['status'] == 'battlefield'
                await call('set_selection_view', {'view': 'selection'})
                selected = await call('inspect_selection')
                await call('select_card', {'card_id': selected['selection']['cards'][0]['id']})
                await call('inspect_pile', {'pile': 'exhaust'})
                await check('exhaust_pile', 'exhaust-pile', baseline)
                await call('close_card_view')
    print('PASS top bar views:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True,
        choices=('combat', 'selection', 'event', 'entry', 'confirmation', 'divination'))
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
