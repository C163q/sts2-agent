"""Audit current proceed routing, native boundaries and rejection recovery."""
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
from sts2_mcp.output.available_tools import GAME_ACTIONS
from tests.game.support.verification_runtime import ensure_run, ipc_directory

SCENARIOS = ('combat', 'reward_skip', 'reward_empty', 'nested_reward', 'treasure_skip', 'treasure_collected',
    'rest', 'tent', 'shop', 'event', 'ancient', 'divination', 'boss1', 'event_resume', 'architect')


async def verify(args):
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation):
        reply = await asyncio.to_thread(raw.call, operation)
        record({'native_operation': operation, 'result': reply})
        assert reply['ok'], reply
        return reply['state']

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                old = set((raw.directory / 'responses').glob('*.json'))
                reply = await session.call_tool(tool, arguments)
                result = reply.structuredContent
                row = {'tool': tool, 'arguments': arguments, 'result': result, 'label': label,
                    'image_count': sum(part.type == 'image' for part in reply.content)}
                added = set((raw.directory / 'responses').glob('*.json')) - old
                if added:
                    assert len(added) == 1, added
                    original = json.loads(added.pop().read_text())
                    row.update(native_error=original.get('error'), execution=original.get('execution'))
                record(row)
                assert result == json.loads(reply.content[0].text), reply
                assert reply.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def observed(action=None):
                deadline = time.monotonic() + 15
                while True:
                    name = action if isinstance(action, str) else '|'.join(action) if action else 'screen'
                    value = await call('get_observation', label='observe_' + name)
                    wanted = {action} if isinstance(action, str) else set(action or ())
                    if action is None or wanted.intersection(value['available_actions']): return value
                    assert time.monotonic() < deadline, value
                    await asyncio.sleep(.1)

            async def reject(label):
                value = await call('proceed', error='illegal_action', label=label)
                assert value['error'] == {'code': 'illegal_action', 'message': 'The requested action is unavailable.',
                    'recovery': 'get_observation'}, value
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                return value

            async def proceed(label, *, reason='action_completed', preset='full'):
                await call('proceed', {'skip': True}, 'invalid_request', label + '_local_invalid')
                value = await call('proceed', {'preset': preset}, label=label)
                assert value['transition']['stop_reason'] == reason and value['transition']['complete'], value
                assert not {'player', 'top_bar', 'map', 'rewards', 'treasure', 'event', 'ancient', 'rest_site', 'shop', 'divination', 'epilogue', 'run_result'} & value.keys(), value
                assert evidence[-1]['image_count'] == 0, evidence[-1]
                return value

            async def leave_map():
                graph = await call('inspect_map')
                if graph['selectable_nodes']:
                    await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]}, label='fixture_room_exit')

            await call('proceed', error='observation_required', label='no_initial_permission')
            state = await observed()
            scenario = args.scenario

            if scenario == 'combat':
                await reject('no_proceed_in_combat')
                await call('end_turn', error='observation_required', label='after_combat_rejection')
                await observed(); await call('end_turn')
                return
            if scenario in {'reward_skip', 'reward_empty'}:
                if scenario == 'reward_skip':
                    await call('inspect_map'); await reject('reward_map_covered')
                    await call('proceed', error='observation_required', label='after_reward_rejection')
                    await call('close_map')
                await observed('proceed')
                result = await proceed('reward_skip' if scenario == 'reward_skip' else 'empty_reward', preset='default' if scenario == 'reward_empty' else 'full')
                assert result['screen']['view'] == 'map', result
                await leave_map(); return
            if scenario == 'nested_reward':
                rewards = await call('inspect_rewards')
                relic = next(r for r in rewards['rewards']['items'] if r['type'] == 'relic')
                await call('claim_reward', {'reward_id': relic['id']})
                await proceed('nested_reward_return')
                parent = await call('inspect_rewards')
                assert parent['rewards']['items'] == [], parent
                await proceed('parent_reward_leave'); await leave_map(); return
            if scenario in {'treasure_skip', 'treasure_collected'}:
                await reject('closed_chest')
                await call('loot_treasure', error='observation_required', label='after_chest_rejection')
                await call('inspect_treasure')
                await call('loot_treasure', {'open_only': scenario == 'treasure_skip'})
                result = await proceed('unclaimed_relic_skip' if scenario == 'treasure_skip' else 'collected_chest_leave')
                assert result['screen']['view'] == 'map', result
                await leave_map(); return
            if scenario in {'rest', 'tent'}:
                await reject('unused_rest')
                await call('choose_rest_option', {'option_id': 'HEAL'}, 'observation_required', 'after_rest_rejection')
                await call('inspect_rest_site'); await call('choose_rest_option', {'option_id': 'HEAL'})
                if scenario == 'tent':
                    current = await observed('proceed'); assert current['rest_site']['options'], current
                await proceed('tent_leave_remaining' if scenario == 'tent' else 'rest_leave')
                await leave_map(); return
            if scenario == 'shop':
                await call('open_shop'); await reject('shop_inventory_open')
                await call('close_shop', error='observation_required', label='after_shop_rejection')
                await call('inspect_shop'); await call('close_shop')
                await proceed('shop_leave'); await leave_map(); return
            if scenario == 'event':
                await reject('unfinished_event')
                await call('choose_event_option', {'option_id': state['event']['options'][1]['id']}, 'observation_required', 'after_event_rejection')
                details = await call('inspect_event')
                await call('choose_event_option', {'option_id': details['event']['options'][1]['id']})
                await proceed('event_leave'); await leave_map(); return
            if scenario == 'ancient':
                await reject('unfinished_ancient')
                await call('choose_ancient_option', {'option_id': state['ancient']['options'][0]['id']}, 'observation_required', 'after_ancient_rejection')
                await call('inspect_ancient')
                details = await observed('choose_ancient_option')
                option = next(option for option in details['ancient']['options'] if option['enabled'])
                await call('choose_ancient_option', {'option_id': option['id']})
                for _ in range(15):
                    current = await observed(('advance_dialogue', 'proceed'))
                    if 'proceed' in current['available_actions']: break
                    assert 'advance_dialogue' in current['available_actions'], current
                    await call('advance_dialogue')
                else: raise AssertionError('Ancient dialogue did not end')
                await proceed('ancient_leave'); await leave_map(); return
            if scenario == 'divination':
                await call('choose_event_option', {'option_id': state['event']['options'][0]['id']})
                await reject('unfinished_divination')
                await call('set_divination_tool', {'tool': 'small'}, 'observation_required', 'after_divination_rejection')
                await call('inspect_event'); await call('set_divination_tool', {'tool': 'small'})
                for attempt in range(15):
                    current = await observed()
                    if 'proceed' in current['available_actions']: break
                    board = current['divination']; assert board['phase'] == 'playing', current
                    preferred = [(0, 0), (5, 5), (10, 10)]
                    cells = preferred + [(x, y) for y in range(11) for x in range(11)]
                    x, y = next((x, y) for x, y in cells if board['grid']['covered_rows'][y][x] == '#')
                    await call('divine', {'x': x, 'y': y})
                else: raise AssertionError('Divination did not finish')
                await proceed('divination_leave'); await leave_map(); return
            if scenario == 'boss1':
                result = await proceed('next_act')
                assert result['scene'] == 'map' and result['screen']['view'] == 'map', result
                immediate = await observed(); assert immediate['scene'] == 'map', immediate
                return
            if scenario == 'event_resume':
                await call('choose_event_option', {'option_id': state['event']['options'][1]['id']})
                await native('prepare_test_event_victory')
                hand = await call('inspect_hand')
                thunder = next(card for card in hand['hand'] if card['name'] == 'Thunderclap')
                played = await call('play_card', {'card_id': thunder['id']})
                if played['transition']['stop_reason'] == 'player_ready':
                    hand = await call('inspect_hand'); card = next(c for c in hand['hand'] if c['name'] in {'Strike', 'Bash'})
                    targets = await call('inspect_targets', {'card_id': card['id']})
                    await call('play_card', {'card_id': card['id'], 'target_id': targets['targets'][0]['id']})
                current = await observed('proceed')
                if current['scene'] == 'rewards':
                    await proceed('combat_return_to_event')
                    current = await observed('proceed')
                assert current['scene'] == 'event', current
                await proceed('resumed_event_leave'); await leave_map(); return
            if scenario == 'architect':
                await proceed('boss_to_architect')
                current = await observed()
                assert current['scene'] == 'epilogue', current
                if 'advance_dialogue' in current['available_actions']:
                    await reject('architect_dialogue_not_finished')
                    await call('advance_dialogue', error='observation_required', label='after_architect_rejection')
                    await observed()
                for _ in range(20):
                    current = await observed()
                    if 'proceed' in current['available_actions']: break
                    assert 'advance_dialogue' in current['available_actions'], current
                    await call('advance_dialogue')
                else: raise AssertionError('Architect dialogue did not end')
                result = await proceed('architect_run_won', reason='run_won')
                assert not set(result['available_actions']) & GAME_ACTIONS, result
                await call('proceed', error='observation_required', label='terminal_has_no_permission')
                await call('inspect_run_result'); await reject('result_requires_result_tool')
                await call('run_result_option', {'option_id': 'continue'}, 'observation_required', 'after_result_rejection')
                return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
