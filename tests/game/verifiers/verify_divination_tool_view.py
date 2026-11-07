"""Verify divination tool views through real MCP and unchanged preflight evidence."""
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
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    async def native(operation, token=None, arguments=None):
        result = await asyncio.to_thread(raw.call, operation, token, arguments=arguments,
                                        response_options={'include_divination_image': False})
        record({'native_operation': operation, 'result': result})
        return result

    # Prepare the board before this MCP session exists, so the first public view is genuinely cold.
    if args.scenario == 'playing':
        current = (await native('get_state'))['state']
        opened = await native('choose_event_option', current['snapshot_id'], {'option_id': current['event']['options'][0]['id']})
        assert opened['ok'], opened
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()

        async def call(tool, arguments=None, *, error=None, label=None):
            supplied = {'preset': 'full', **(arguments or {})}
            old = set((raw.directory / 'responses').glob('*.json'))
            response = await session.call_tool(tool, supplied)
            result = response.structuredContent
            row = {'tool': tool, 'arguments': supplied, 'label': label, 'result': result,
                   'images': sum(part.type == 'image' for part in response.content)}
            added = set((raw.directory / 'responses').glob('*.json')) - old
            if added:
                assert len(added) == 1, added
                original = json.loads(added.pop().read_text())
                row.update(native_error=original.get('error'), execution=original.get('execution'))
            record(row)
            assert result == json.loads(response.content[0].text) and response.isError == bool(error), response
            assert result.get('error', {}).get('code') == error, result
            return result

        async def reject(label, hint, *, existing=True):
            before = (await native('get_state'))['state']
            result = await call('set_divination_tool', {'tool': 'small'}, error='illegal_action', label=label)
            assert hint in result['error']['message'], result
            assert result['error']['recovery'] == ('choose_legal_action' if existing else 'get_observation'), result
            assert evidence[-1]['native_error']['ui_unchanged'] is True, evidence[-1]
            assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
            assert evidence[-1]['execution']['action_submission_observed'] is False, evidence[-1]
            after = (await native('get_state'))['state']
            assert before['snapshot_id'] == after['snapshot_id'], 'Rejected view changed the state.'

        async def switch(tool, label, preset='full'):
            before = (await native('get_state'))['state']
            result = await call('set_divination_tool', {'tool': tool, 'preset': preset}, label=label)
            assert set(result) == {'scene', 'screen', 'available_actions'}, result
            assert result['scene'] == 'event' and result['screen'] == {'status': 'visible', 'view': 'divination'}, result
            assert 'divine' in result['available_actions'] and 'set_divination_tool' in result['available_actions'], result
            assert evidence[-1]['images'] == 0, evidence[-1]
            executed = evidence[-1]['execution']['ui_interaction_started']
            after = (await native('get_state'))['state']
            assert after['divination']['tool'] == tool, after
            for key in ('remaining', 'grid'):
                assert before['divination'][key] == after['divination'][key], (before, after)
            assert before['top_bar'] == after['top_bar'], (before, after)
            assert executed == (before['divination']['tool'] != tool), (before, after)
            if not executed: assert before['snapshot_id'] == after['snapshot_id'], (before, after)
            assert all(o['enabled'] for o in after['divination']['tools']), after
            return result

        if args.scenario == 'playing':
            await switch('small', 'cold_switch')
            await call('divine', {'x': 5, 'y': 5}, label='direct_reveal_after_cold_switch')
            await switch('small', 'same_tool')
            await switch('big', 'switch_big_default', preset='default')
            await switch('small', 'switch_small')
            await call('set_divination_tool', {'tool': 'large'}, error='invalid_request', label='local_invalid')
            await switch('big', 'after_local_invalid')
            current = (await native('get_state'))['state']
            bad = await native('set_divination_tool', current['snapshot_id'], {'tool': 'large'})
            assert bad['error']['code'] == 'invalid_request' and bad['error']['ui_unchanged'], bad
            # A view uses the current exposed UI rather than a previous observation token.
            direct = await native('set_divination_tool', 'obsolete', {'tool': 'big'})
            assert direct['ok'] and 'transition' not in direct['state'], direct
            for page, close in [('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')]:
                await call(page)
                await reject(page + '_covered', close)
                await call(close)
                await switch('small', page + '_closed')
            return
        await reject('cold_unavailable', 'No divination board', existing=False)
        await call('divine', {'x': 5, 'y': 5}, error='observation_required', label='no_cold_permission')
        state = await call('get_observation')
        if args.scenario == 'no_board':
            await reject('no_board', 'No divination board')
            await call('end_turn', label='legal_after_rejection')
            return
        await call('choose_event_option', {'option_id': state['event']['options'][0]['id']})
        state = await call('get_observation')
        if args.scenario in {'rewards', 'selection'}:
            geometry = (await native('check_test_divination'))['state']
            kind = 'CrystalSpherePotion' if args.scenario == 'rewards' else 'CrystalSphereCardReward'
            item = next(i for i in geometry['items'] if i['kind'] == kind and (kind != 'CrystalSpherePotion' or i['width'] == 1))
            await call('divine', {'x': item['x'], 'y': item['y'] + 1})
            state = await call('get_observation')
            while state['scene'] != 'rewards' and state['divination']['phase'] == 'playing':
                x, y = next((x, y) for y, row in enumerate(state['divination']['grid']['cell_rows']) for x, c in enumerate(row) if c == '#')
                await call('divine', {'x': x, 'y': y}); state = await call('get_observation')
            assert state['scene'] == 'rewards', state
            if args.scenario == 'selection':
                reward = next(r for r in state['rewards']['items'] if r['type'] == 'card')
                await call('claim_reward', {'reward_id': reward['id']})
                await reject('selection_covered', 'inspect_selection')
                await call('selection_option', {'option_id': 'skip'}, label='selection_after_rejection')
            else:
                await reject('rewards_covered', 'inspect_rewards')
                await call('discard_potion', {'potion_slot': 0}, label='discard_after_rejection')
                await call('claim_reward', {'reward_id': state['rewards']['items'][0]['id']}, label='claim_after_rejection')
            return
        assert args.scenario == 'finished'
        while True:
            if state['scene'] == 'rewards':
                await call('proceed'); state = await call('get_observation'); continue
            if state['divination']['phase'] == 'finished': break
            x, y = next((x, y) for y, row in enumerate(state['divination']['grid']['cell_rows']) for x, c in enumerate(row) if c == '#')
            await call('divine', {'x': x, 'y': y}); state = await call('get_observation')
        await reject('finished_board', 'proceed')
        await call('proceed', label='proceed_after_rejection')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
