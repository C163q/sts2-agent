import argparse
import asyncio
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    before = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while before['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        before = await asyncio.to_thread(raw.call, 'get_state')
    assert before['state']['scene'] == 'main_menu', 'Requires a fresh isolated instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', before['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.version == '0.20.0'

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                assert data == json.loads(response.content[0].text)
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert 'snapshot_id' not in data
                if error:
                    assert data.get('error', {}).get('code') == error, data
                else:
                    assert 'error' not in data, data
                return data

            await call('end_turn', error='observation_required')
            initial = await call('get_observation')
            cards = initial['player']['hand']
            armaments = next(c for c in cards if c['name'] == 'Armaments')
            defend = next(c for c in cards if c['name'] == 'Defend')
            strike = next(c for c in cards if c['name'] == 'Strike')
            await call('capture_screenshot', {'filename': 'initial.png'})
            await call('inspect_targets', {'potion_slot': 0})
            used = await call('use_potion', {'potion_slot': 0})
            assert used['transition']['stop_reason'] == 'choice_required', used
            options = await call('inspect_selection')
            chosen = options['selection']['cards'][0]
            added = await call('select_card', {'card_id': chosen['id']})
            assert added['transition']['stop_reason'] == 'player_ready', added
            hand = await call('inspect_hand')
            assert next(c for c in hand['hand'] if c['id'] == chosen['id'])['energy_cost'] == '0', hand
            await call('inspect_targets', {'card_id': armaments['id']})
            played = await call('play_card', {'card_id': armaments['id']})
            assert played['selection']['type'] == 'hand_upgrade', played
            await call('inspect_selection')
            selected = await call('select_card', {'card_id': defend['id']})
            assert selected['selection']['upgrade_preview']['after']['name'] == 'Defend+', selected
            await call('capture_screenshot', {'filename': 'upgrade-preview.png'})
            upgraded = await call('selection_option', {'option_id': 'confirm'})
            assert upgraded['transition']['stop_reason'] == 'player_ready', upgraded
            queried = await call('inspect_targets', {'card_id': defend['id']})
            assert queried['card']['name'] == 'Defend+', queried
            await call('play_card', {'card_id': defend['id']})
            targets = await call('inspect_targets', {'card_id': strike['id']})
            await call('play_card', {'card_id': strike['id'], 'target_id': targets['targets'][0]['id']})
            await call('discard_potion', {'potion_slot': 2})
            await call('use_potion', {'potion_slot': 1})
            ended = await call('end_turn')
            assert ended['turn'] == initial['turn'] + 1 and ended['transition']['complete'], ended
            await call('capture_screenshot', {'filename': 'after-chain.png'})
            assert sum(item['tool'] == 'get_observation' for item in evidence) == 1
            actions = {'end_turn', 'play_card', 'use_potion', 'discard_potion', 'select_card', 'selection_option'}
            assert sum(item['tool'] in actions and 'error' not in item['result'] for item in evidence) == 10

            # Simulate a player or another file client advancing the game after the returned observation.
            state = await asyncio.to_thread(raw.call, 'get_state')
            advanced = await asyncio.to_thread(raw.call, 'end_turn', state['state']['snapshot_id'])
            assert advanced['ok'] and advanced['state']['transition']['stop_reason'] == 'player_ready', advanced
            await call('end_turn', error='stale_state')
            await call('end_turn', error='observation_required')
            await call('get_observation')
            await call('inspect_deck')
            await call('close_card_view')
            await call('end_turn', error='observation_required')
            await call('get_observation')
            resumed = await call('end_turn')
            assert resumed['turn'] == advanced['state']['turn'] + 1, resumed
    print('PASS: one observation supports 10 native chained actions; external state changes and views still require re-observation.')


def main():
    parser = argparse.ArgumentParser(description='验证隔离图形实例的动作观察复用，需 --play-scenario armaments_free --potion-scenario skill。')
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
