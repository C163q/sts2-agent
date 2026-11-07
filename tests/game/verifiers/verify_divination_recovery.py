"""Verify divination refusals, direct continuation, and native reveal boundaries."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    name = args.scenario
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()

        async def call(tool, args=None, *, error=None, label=None):
            supplied = {'preset': 'full', **(args or {})}
            old = set((raw.directory / 'responses').glob('*.json'))
            response = await session.call_tool(tool, supplied)
            result = response.structuredContent
            files = set((raw.directory / 'responses').glob('*.json')) - old
            row = {'case': name, 'tool': tool, 'arguments': supplied, 'label': label, 'result': result,
                   'images': sum(part.type == 'image' for part in response.content),
                   'native_files': [str(p.relative_to(ROOT)) for p in sorted(files)]}
            if files:
                assert len(files) == 1, files
                original = json.loads(next(iter(files)).read_text())
                row.update(native_error=original.get('error'), execution=original.get('execution'))
            record(row)
            assert result == json.loads(response.content[0].text) and response.isError == bool(error), response
            assert result.get('error', {}).get('code') == error, result
            return result

        async def native(operation, token=None, args=None):
            result = await asyncio.to_thread(raw.call, operation, token, arguments=args,
                                            response_options={'include_divination_image': False})
            record({'case': name, 'native_operation': operation, 'result': result})
            return result

        async def reject(x, y, label):
            before = (await native('get_state'))['state']
            result = await call('divine', {'x': x, 'y': y}, error='illegal_action', label=label)
            hints = {'no_board': 'No divination board', 'already_cleared': 'already uncovered',
                     'empty_corner': 'already uncovered', 'inspect_map_covered': 'close_map',
                     'inspect_deck_covered': 'close_card_view', 'finished_board': 'proceed',
                     'rewards_covered': 'inspect_rewards', 'selection_covered': 'inspect_selection'}
            assert hints[label] in result['error']['message'], result
            assert result['error']['recovery'] == 'choose_legal_action', result
            assert evidence[-1]['native_error']['action_submitted'] is False, evidence[-1]
            assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
            assert evidence[-1]['execution']['action_submission_observed'] is False, evidence[-1]
            after = (await native('get_state'))['state']
            assert before['snapshot_id'] == after['snapshot_id'], (before, after)

        async def reveal(state, x, y, label, preset='full'):
            count = state['divination']['remaining']
            rows = state['divination']['grid']['cell_rows']
            tool = state['divination']['tool']
            receipt = await call('divine', {'x': x, 'y': y, 'preset': preset}, label=label)
            assert set(receipt) == {'scene', 'screen', 'available_actions', 'transition'}, receipt
            assert receipt['transition']['complete'] and evidence[-1]['images'] == 0, receipt
            after = await call('get_observation', label=label + '_observed')
            if after['divination']['status'] == 'visible' and after['divination']['phase'] == 'playing':
                assert after['divination']['remaining'] == count - 1, after
                radius = 1 if tool == 'big' else 0
                expected = [''.join('#' if c == '#' and not (abs(cx-x) <= radius and abs(cy-y) <= radius) else '.'
                                    for cx, c in enumerate(row)) for cy, row in enumerate(rows)]
                actual = [''.join('#' if c == '#' else '.' for c in row) for row in after['divination']['grid']['cell_rows']]
                assert actual == expected, (expected, actual)
            return after, receipt

        await call('divine', {'x': 5, 'y': 5}, error='observation_required', label='cold_call')
        state = await call('get_observation')
        if name == 'no_board':
            await reject(5, 5, 'no_board')
            await call('end_turn', label='legal_after_rejection')
            return
        await call('choose_event_option', {'option_id': state['event']['options'][1 if name == 'relic' else 0]['id']})
        state = await call('get_observation', label='initial_board')
        assert state['divination']['remaining'] == (6 if name == 'relic' else 3) and state['divination']['tool'] == 'big', state

        if name == 'small':
            await call('set_divination_tool', {'tool': 'small'})
            state = await call('get_observation')
            for invalid_arguments in ({'x': True, 'y': 5}, {'x': 0.0, 'y': 5}, {'x': 11, 'y': 5}, {'x': 5}, {'x': 5, 'y': 5, 'extra': 1}):
                await call('divine', invalid_arguments, error='invalid_request', label='local_invalid')
            state, _ = await reveal(state, 5, 5, 'small_full')
            await call('divine', {'x': 5, 'y': 6, 'preset': 'default'}, label='small_default_direct')
            observed = await call('get_observation')
            assert observed['divination']['remaining'] == 1, observed
            current = (await native('get_state'))['state']
            bad = await native('divine', current['snapshot_id'], {'x': -1, 'y': 0})
            assert bad['error']['code'] == 'invalid_request' and bad['error']['action_submitted'] is False, bad
            stale = await native('divine', 'obsolete', {'x': 5, 'y': 7})
            assert stale['error']['code'] == 'stale_state' and 'action_submitted' not in stale['error'], stale
            return
        if name == 'big':
            state, _ = await reveal(state, 0, 5, 'big_edge_full')
            state, _ = await reveal(state, 5, 5, 'big_center_full')
            return
        if name == 'cleared':
            await call('set_divination_tool', {'tool': 'small'})
            state = await call('get_observation')
            state, _ = await reveal(state, 5, 5, 'first_reveal')
            await reject(5, 5, 'already_cleared')
            await call('divine', {'x': 5, 'y': 6}, label='legal_after_rejection')
            await call('get_observation')
            await reject(0, 0, 'empty_corner')
            await call('divine', {'x': 5, 'y': 7}, label='after_corner_rejection')
            return
        if name == 'covered':
            for page, close in [('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')]:
                await call(page)
                await reject(5, 5, page + '_covered')
                await call(close, label=page + '_closed_after_rejection')
                await call('divine', {'x': 5, 'y': 5 if page == 'inspect_map' else 8}, label=page + '_reveal_after_close')
            return
        if name == 'finished':
            await call('set_divination_tool', {'tool': 'small'})
            state = await call('get_observation')
            while state['divination']['phase'] == 'playing':
                x, y = next((x, y) for y, row in enumerate(state['divination']['grid']['cell_rows']) for x, c in enumerate(row) if c == '#')
                state, receipt = await reveal(state, x, y, 'finish_reveal')
                if state['scene'] == 'rewards':
                    await call('proceed'); state = await call('get_observation')
            assert state['divination']['phase'] == 'finished', state
            await reject(5, 5, 'finished_board')
            await call('proceed', label='proceed_after_rejection')
            return

        if name == 'direct':
            await call('set_divination_tool', {'tool': 'small'})
            await call('divine', {'x': 5, 'y': 5}, label='first_direct')
            await call('divine', {'x': 5, 'y': 6}, label='second_direct')
            state = await call('get_observation', label='two_direct_observed')
            assert state['divination']['remaining'] == 1, state
            return

        geometry = (await native('check_test_divination'))['state']
        kind = {'rewards': 'CrystalSpherePotion', 'selection': 'CrystalSphereCardReward',
                'curse': 'CrystalSphereCurse', 'gold': 'CrystalSphereGold', 'relic': 'CrystalSphereRelic'}[name]
        item = next(i for i in geometry['items'] if i['kind'] == kind and (name != 'rewards' or i['width'] == 1))
        planned = [(item['x'] + item['width']//2, item['y'] + item['height']//2)]
        if name == 'relic':
            planned = [(item['x']+dx, item['y']+dy) for dx, dy in [(1, 1), (3, 1), (1, 3), (3, 3)]]
        while state['divination']['phase'] == 'playing':
            rows = state['divination']['grid']['cell_rows']
            while planned and rows[planned[0][1]][planned[0][0]] != '#': planned.pop(0)
            x, y = planned.pop(0) if planned else next((x, y) for y, row in enumerate(rows) for x, c in enumerate(row) if c == '#')
            state, receipt = await reveal(state, x, y, name + '_reveal')
            if name == 'curse':
                assert any(e['type'] == 'card_added' and e.get('pile') == 'deck' for e in receipt['transition']['events']), receipt
                return
            if state['scene'] == 'rewards':
                if name in {'gold', 'relic'}:
                    expected_type = 'gold' if name == 'gold' else 'relic'
                    expected_event = 'gold_changed' if name == 'gold' else 'relic_obtained'
                    reward = next(r for r in state['rewards']['items'] if r['type'] == expected_type)
                    assert not any(e['type'] == expected_event for row in evidence if row.get('tool') == 'divine' for e in row['result'].get('transition', {}).get('events', [])), receipt
                    acquired = await call('claim_reward', {'reward_id': reward['id']}, label=name + '_claimed')
                    assert any(e['type'] == expected_event for e in acquired['transition']['events']), acquired
                    return
                if name in {'rewards', 'selection'}:
                    if name == 'selection':
                        reward = next(r for r in state['rewards']['items'] if r['type'] == 'card')
                        await call('claim_reward', {'reward_id': reward['id']})
                        await reject(5, 5, 'selection_covered')
                        await call('selection_option', {'option_id': 'skip'}, label='selection_after_rejection')
                    else:
                        await reject(5, 5, 'rewards_covered')
                        await call('discard_potion', {'potion_slot': 0}, label='discard_after_rejection')
                        claimed = await call('claim_reward', {'reward_id': state['rewards']['items'][0]['id']}, label='claim_after_rejection')
                        assert claimed['reward_result']['status'] == 'claimed', claimed
                    return
                await call('proceed'); state = await call('get_observation')
        raise AssertionError(('Expected reward page', name, state))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
