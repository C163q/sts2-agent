"""Collect public play receipts and probe native single-player queue behavior."""
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


QUEUE_MODES = ('ordered', 'energy', 'stars', 'target', 'random_exhaust', 'hand_exhaust',
               'automatic_hand', 'choose_one', 'combat_pile', 'victory', 'death', 'immediate_death',
               'bullet_time', 'survivor_manual', 'survivor_auto', 'dagger_manual', 'dagger_auto')
PUBLIC_MODES = ('basic', 'energy', 'stars', 'unplayable', 'card_logic', 'cancel', 'hand_choice',
                'choose_one', 'combat_pile', 'victory', 'death', 'covered', 'noncombat', 'random', 'x_cost', 'hook')
SCENARIOS = (*('queue_' + mode for mode in QUEUE_MODES), *PUBLIC_MODES)


async def verify(args):
    raw = Client(ipc_directory(), timeout=65)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert result == json.loads(response.content[0].text)
                if error: assert response.isError and result['error']['code'] == error, result
                else: assert not response.isError, result
                return result

            before = await call('get_observation')
            if args.scenario.startswith('queue_'):
                probe = await asyncio.to_thread(raw.call, 'check_test_play_queue',
                    arguments={'mode': args.scenario.removeprefix('queue_')})
                record({'native_operation': 'check_test_play_queue', 'response': probe})
                assert probe['ok'] and probe['state']['passed'], probe
                if args.scenario in {'queue_victory', 'queue_death', 'queue_immediate_death'}:
                    deadline = time.monotonic() + 12
                    previous, quiet_since = None, time.monotonic()
                    while time.monotonic() < deadline:
                        current = await asyncio.to_thread(raw.call, 'get_state')
                        assert current['ok'], current
                        token = current['state']['snapshot_id']
                        if token != previous:
                            previous, quiet_since = token, time.monotonic()
                        if time.monotonic() - quiet_since >= 2:
                            break
                        await asyncio.sleep(.1)
                    else:
                        raise AssertionError('The terminal test screen did not settle before cleanup.')
                await call('get_observation')
                return
            if args.scenario == 'noncombat':
                result = await call('play_card', {'card_id': 0}, error='illegal_action')
                assert result['error']['recovery'] == 'choose_legal_action', result
                return
            hand = (await call('inspect_hand'))['hand']
            first = hand[0]
            target = max(before['enemies'], key=lambda e: e['hp'])['id']

            async def play(card, **kwargs):
                query = await call('inspect_targets', {'card_id': card['id']})
                return await call('play_card', {'card_id': card['id'],
                    **({'target_id': target} if query['requires_target'] else {}), **kwargs})

            if args.scenario == 'hook':
                for card in hand[:3]:
                    await play(card)
                query = await call('inspect_targets', {'card_id': hand[3]['id']})
                assert not query['playable'] and query['reason'] == 'This card cannot be played now.', query
                result = await call('play_card', {'card_id': hand[3]['id']}, error='illegal_action')
                assert result['error']['recovery'] == 'choose_legal_action'
                return
            if args.scenario == 'covered':
                for tool, close in [('inspect_deck', 'close_card_view'), ('inspect_map', 'close_map')]:
                    await call(tool)
                    covered = await call('get_observation')
                    rejected = await call('play_card', {'card_id': first['id']}, error='illegal_action')
                    assert rejected['error']['recovery'] == 'choose_legal_action'
                    assert covered == await call('get_observation')
                    if close in covered['available_actions']:
                        await call(close)
                return
            if args.scenario in {'energy', 'stars', 'unplayable', 'card_logic'}:
                query = await call('inspect_targets', {'card_id': first['id']})
                assert not query['playable'] and query['reason'], query
                rejected = await call('play_card', {'card_id': first['id'],
                    **({'target_id': target} if query['requires_target'] else {})}, error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                if args.scenario == 'energy': await call('end_turn')
                return
            if args.scenario == 'basic':
                for arguments, code in [({'card_id': True}, 'invalid_request'),
                    ({'card_id': first['id'], 'target_id': None}, 'invalid_request'),
                    ({'card_id': 2147483647}, 'illegal_action'),
                    ({'card_id': first['id']}, 'illegal_action'),
                    ({'card_id': first['id'], 'target_id': 4294967295}, 'illegal_action')]:
                    await call('play_card', arguments, error=code)
                old = await asyncio.to_thread(raw.call, 'get_state')
                played = await play(first)
                assert played['transition']['stop_reason'] == 'player_ready'
                native = await asyncio.to_thread(raw.call, 'play_card', old['state']['snapshot_id'],
                    arguments={'card_id': hand[1]['id']})
                record({'native_operation': 'play_card_stale', 'response': native})
                assert not native['ok'] and native['error']['code'] == 'stale_state', native
                await call('inspect_hand')
                own_target = (await call('inspect_targets', {'card_id': hand[1]['id']}))['targets'][0]['id']
                await call('play_card', {'card_id': hand[1]['id'], 'target_id': own_target}, error='illegal_action')
                await play(hand[1])
                return
            if args.scenario == 'combat_pile':
                await play(next(c for c in hand if c['name'] == 'Defend'))
                await play(next(c for c in hand if c['name'] == 'Strike'))
            result = await play(first)
            expected = {'cancel': 'action_canceled', 'victory': 'combat_won', 'death': 'combat_lost',
                'hand_choice': 'choice_required', 'choose_one': 'choice_required', 'combat_pile': 'choice_required'}
            assert result['transition']['stop_reason'] == expected.get(args.scenario, 'player_ready'), result
            assert result['transition']['complete'], result
            if expected.get(args.scenario) == 'choice_required':
                selection = await call('inspect_selection')
                await call('play_card', {'card_id': hand[-1]['id']}, error='illegal_action')
                selected = await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
                if selected['transition']['stop_reason'] == 'choice_required':
                    pending = await call('inspect_selection')
                    confirm = next((b for b in pending['selection']['options'] if b['id'] == 'confirm' and b['enabled']), None)
                    if confirm: await call('selection_option', {'option_id': 'confirm'})
            elif args.scenario == 'cancel':
                await call('play_card', {'card_id': hand[1]['id']}, error='observation_required')
                await call('inspect_hand')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=SCENARIOS)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
