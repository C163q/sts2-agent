"""Exercise default/full against actual UI output through real stdio MCP."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import base64
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from sts2_mcp.mcp_server import SERVER_VERSION
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
            assert initialized.serverInfo.version == SERVER_VERSION, initialized
            definitions = (await session.list_tools()).tools
            assert {'get_observation', 'choose_event_option'} <= {tool.name for tool in definitions}
            assert all(t.inputSchema['properties']['preset']['default'] == 'default' for t in definitions)

            async def call(name, arguments=None, error=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                images = [c for c in reply.content if c.type == 'image']
                evidence.append({'tool': name, 'arguments': arguments, 'result': data, 'images': len(images)})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error:
                    assert reply.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not reply.isError and 'error' not in data, data
                assert json.loads(reply.content[0].text) == data, reply
                if images:
                    assert len(images) == 1 and images[0].mimeType == 'image/png'
                    (args.report.parent / f'{len(evidence):02}-{name}.png').write_bytes(base64.b64decode(images[0].data))
                assert len(images) == int(bool((arguments or {}).get('include_image')) and (data.get('divination') or {}).get('status') == 'visible')
                return data

            full = await call('get_observation', {'preset': 'full'})
            state = await call('get_observation')
            assert state == await call('get_observation', {'preset': 'default'})
            assert 'player' not in state if full['player'] is None else state['player'] is not None

            if args.scenario == 'combat':
                hand = await call('inspect_hand')
                hand_full = await call('inspect_hand', {'preset': 'full'})
                assert hand == await call('inspect_hand', {'preset': 'default'})
                assert len(hand['hand']) == len(hand_full['hand']) > 0
                assert all(c['star_cost'] is None for c in hand_full['hand']), hand_full
                assert all('star_cost' not in c and c['description'] for c in hand['hand']), hand
                selected = hand['hand'][0]['id']
                filtered = await call('inspect_hand', {'card_ids': [selected, 2147483647]})
                assert filtered['hand'] == hand['hand'][:1]
                assert filtered['errors'] == [{'code': 'cards_not_in_hand', 'card_ids': [2147483647]}]
                potions = await call('inspect_potions')
                potions_full = await call('inspect_potions', {'preset': 'full'})
                assert any(p is None for p in potions_full['potion_slots']), potions_full
                assert [p is None for p in potions['potion_slots']] == [p is None for p in potions_full['potion_slots']]
                relics = await call('inspect_relics')
                relic_full = await call('inspect_relics', {'preset': 'full'})
                summary = await call('inspect_relics', {'preset': 'summary'})
                ordinary = [(a, b, c) for a, b, c in zip(relics['relics'], relic_full['relics'], summary['relics'])
                            if b['name'] == 'Burning Blood']
                assert ordinary, relic_full
                for compact, complete, brief in ordinary:
                    assert 'melted' not in compact and complete['melted'] is None and 'melted' not in brief
                defend = next(c for c in hand['hand'] if c['name'] == 'Defend')
                receipt = await call('play_card', {'card_id': defend['id']})
                assert receipt['transition']['complete'] and 'player' not in receipt
                played = next(e for e in receipt['transition']['events'] if e['type'] == 'card_played')
                assert 'source' not in played, played
                assert (await call('end_turn', {'preset': 'full'}))['transition']['complete']
            elif args.scenario == 'orbs':
                slots, original = state['player']['orb_slots'], full['player']['orb_slots']
                assert len(slots) == len(original) and any(s is None for s in original)
                assert any(s and s['evoke'] is None for s in original), original
                for compact, complete in zip(slots, original):
                    if complete is None:
                        assert compact is None
                    else:
                        assert compact['name'] == complete['name']
                        for key in ('passive', 'evoke'):
                            if complete[key] is None:
                                assert key not in compact, (compact, complete)
                            else:
                                assert compact[key] == complete[key]
                assert (await call('inspect_combatants'))['player']['orb_slots'] == slots
            elif args.scenario in {'smith', 'transform'}:
                if args.scenario == 'smith':
                    await call('choose_rest_option', {'option_id': 'SMITH'})
                else:
                    await call('choose_event_option', {'option_id': state['event']['options'][0]['id']})
                candidates = await call('inspect_selection')
                complete = await call('inspect_selection', {'preset': 'full'})
                assert candidates['selection']['cards'][0]['description']
                assert 'star_cost' not in candidates['selection']['cards'][0]
                assert complete['selection']['cards'][0]['star_cost'] is None
                chosen = candidates['selection']['cards'][0]['id']
                await call('select_card', {'card_id': chosen})
                preview = await call('inspect_selection')
                complete = await call('inspect_selection', {'preset': 'full'})
                field = 'upgrade_previews' if args.scenario == 'smith' else 'transform_previews'
                assert preview['selection'][field] == complete['selection'][field]
                assert len(preview['selection'][field]) == 1, preview
                pair = preview['selection'][field][0]
                assert pair['before']['id'] == chosen
                if args.scenario == 'transform':
                    assert pair['random'] and pair['after'] is None
                else:
                    assert pair['after']['id'] == chosen and pair['after']['star_cost'] is None
                assert (await call('get_observation'))['selection'][field] == complete['selection'][field]
            elif args.scenario == 'divination':
                await call('choose_event_option', {'option_id': state['event']['options'][0]['id']})
                for name in ('get_observation', 'inspect_event'):
                    compact = await call(name)
                    complete = await call(name, {'preset': 'full'})
                    assert compact['divination']['grid'] == complete['divination']['grid']
                    assert compact['divination']['status'] == 'visible'
                minimal = await call('get_observation', {'preset': 'actions_only'})
                assert 'divination' not in minimal
            else:
                if args.scenario == 'event':
                    option = state['event']['options'][0]['id']
                    receipt = await call('choose_event_option', {'option_id': option, 'preset': 'default'})
                    assert receipt['transition']['complete']
                    assert any(e['type'] == 'hp_changed' for e in receipt['transition']['events']), receipt
                    await call('inspect_event')
                graph = await call('inspect_map')
                graph_full = await call('inspect_map', {'preset': 'full'})
                assert graph['nodes'] == graph_full['nodes']
                if graph_full['current_node'] is None:
                    assert 'current_node' not in graph
                else:
                    assert graph['current_node'] == graph_full['current_node']
                if args.scenario == 'event':
                    covered = await call('get_observation')
                    assert covered['event'] == {'status': 'covered'}, covered
                tools = await call('get_observation', {'preset': 'actions_only'})
                await call('close_map', {'preset': 'full'},
                           error=None if 'close_map' in tools['available_actions'] else 'illegal_action')
    print('PASS default/full:', args.scenario, len(evidence), 'actual MCP calls')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证统一 default 输出预设。')
    parser.add_argument('--scenario', required=True, choices=('combat', 'orbs', 'smith', 'transform', 'divination', 'map', 'event'))
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
