"""Check compact combat observations and top-bar context through real MCP."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import base64
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
    config.write_text(json.dumps({'screenshots': {'enabled': False}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.version == '0.50.2'
            definitions = {t.name: t for t in (await session.list_tools()).tools}
            assert len(definitions) == 42
            assert definitions['get_observation'].inputSchema['properties']['preset']['enum'] == [
                'default', 'full', 'actions_only', 'summary', 'top_bar']

            async def call(name, arguments=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                images = [c for c in reply.content if c.type == 'image']
                evidence.append({'tool': name, 'arguments': arguments, 'result': data, 'images': len(images)})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert not reply.isError and 'error' not in data, data
                assert json.loads(reply.content[0].text) == data
                for index, content in enumerate(images):
                    assert content.mimeType == 'image/png'
                    png = base64.b64decode(content.data)
                    assert png.startswith(b'\x89PNG\r\n\x1a\n')
                    (args.report.parent / f'{len(evidence):02}-{index}.png').write_bytes(png)
                if arguments and arguments.get('preset') in {'top_bar', 'actions_only'}:
                    assert not images
                return data

            initial = await call('get_observation', {'preset': 'full'})
            if args.scenario == 'divination':
                await call('choose_event_option', {'option_id': initial['event']['options'][0]['id']})
            full = await call('get_observation', {'preset': 'full'})
            state = await call('get_observation')
            summary = await call('get_observation', {'preset': 'summary'})
            actions = await call('get_observation', {'preset': 'actions_only'})
            bar = await call('get_observation', {'preset': 'top_bar'})
            assert state == apply_preset(full, 'default')
            assert {k: v for k, v in bar.items() if k != 'top_bar'} == actions
            assert bar['top_bar']['relic_count'] == full['top_bar']['relic_count'] >= 0
            assert 'relics' not in bar['top_bar']
            assert bar['top_bar']['potion_slots'] == state['top_bar']['potion_slots']
            assert bar['top_bar']['floor'] == full['top_bar']['floor']
            assert bar['top_bar']['hp'] == full['top_bar']['hp']
            assert bar['top_bar']['deck_count'] == full['top_bar']['deck_count']
            before = await asyncio.to_thread(raw.call, 'get_state')
            if full['scene'] == 'combat':
                player = summary['player']
                assert player['health'] == f"{full['player']['hp']}/{full['player']['max_hp']}"
                assert player['energy'] == f"{full['player']['energy']}/{full['player']['max_energy']}"
                assert not {'hp', 'max_hp', 'hp_display', 'max_energy'} & player.keys()
                assert 'floor' not in summary['top_bar'] and 'relics' not in summary['top_bar']
                assert summary['top_bar']['relic_count'] == full['top_bar']['relic_count']
                assert summary['available_actions'] == full['available_actions']
                assert all('health' in enemy and 'hp' not in enemy for enemy in summary['enemies'])
                assert all(unit.get('powers') != [] for unit in [player, *summary['enemies'], *summary['allies']])
                details = await call('inspect_hand', {'preset': 'summary'})
                assert player['hand'] == apply_preset(details, 'default')['hand']
                if args.scenario == 'orbs':
                    assert len(player['orb_slots']) == 5 and player['orb_slots'][-1] is None
                    assert player['orb_slots'][3] == {'name': 'Plasma'}
                elif args.scenario == 'osty':
                    assert summary['allies'][0]['name'] == 'Osty'
                    assert summary['allies'][0]['block_shared_with'] == 'player'
                    assert summary['allies'][0]['health'] == '1/1'
                elif args.scenario == 'blade':
                    assert player['stars'] == 3 and player['sovereign_blades'][0]['name'] == 'Sovereign Blade'
                elif args.scenario == 'enchantments':
                    assert player['hand'][0]['enchantment'] == {'name': 'Sharp', 'dimmed': False, 'amount': 3}
                    assert 'amount' not in player['hand'][2]['enchantment']
                    assert 'enchantment' not in player['hand'][3]
                elif args.scenario == 'empty_inventory':
                    assert player['character'] == 'NECROBINDER'
                    assert full['top_bar']['relics'] == []
                    assert summary['top_bar']['relic_count'] == bar['top_bar']['relic_count'] == 0
            else:
                expected = dict(state)
                expected['top_bar'] = {k: v for k, v in state['top_bar'].items()
                                       if k in {'gold', 'potion_slots', 'deck_count', 'relic_count'}}
                assert summary == expected
                if args.scenario == 'divination':
                    assert summary['divination']['status'] == 'visible'
                    assert 'divination' not in bar
            after = await asyncio.to_thread(raw.call, 'get_state')
            # The board's visual animation changes PNG bytes without a gameplay change.
            logical_before = {k: v for k, v in before['state'].items() if k != 'divination_image'}
            logical_after = {k: v for k, v in after['state'].items() if k != 'divination_image'}
            assert logical_before == logical_after, 'Output projections changed the native state.'
            if args.scenario == 'native':
                checked = await asyncio.to_thread(raw.call, 'check_test_capacity')
                evidence.append({'native_checks': checked})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert checked['ok'] and checked['state']['passed'], checked
            elif args.scenario == 'rest':
                await call('choose_rest_option', {'option_id': 'SMITH'})
                choice = await call('get_observation', {'preset': 'top_bar'})
                assert choice['selection'] == {'type': 'deck_upgrade', 'status': 'visible'}
                assert set(choice) == {'scene', 'screen', 'selection', 'available_actions', 'top_bar'}
            elif args.scenario == 'event':
                await call('inspect_map')
                covered = await call('get_observation', {'preset': 'top_bar'})
                assert covered['scene'] == 'event' and covered['screen']['view'] == 'map'
                assert 'event' not in covered
            elif full['scene'] == 'combat':
                await call('get_observation', {'preset': 'top_bar'})
                defend = next(c for c in full['player']['hand'] if c['name'].startswith('Defend'))
                receipt = await call('play_card', {'card_id': defend['id']})
                assert receipt['transition']['complete'] and 'player' not in receipt
    print('PASS observation presets:', args.scenario, len(evidence), 'records')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True,
        choices=('combat', 'orbs', 'osty', 'blade', 'enchantments', 'rest', 'event', 'divination', 'native', 'empty_inventory'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
