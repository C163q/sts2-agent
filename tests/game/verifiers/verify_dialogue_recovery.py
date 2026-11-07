"""Verify dialogue preflight reasons, permission recovery and native handoffs."""
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

SCENARIOS = ('wrong_room', 'basic', 'dialogue', 'default', 'selection', 'rewards', 'stale', 'architect')


async def verify(args):
    report = args.report.resolve()
    if report.exists(): raise FileExistsError(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=70)
    created = await asyncio.to_thread(ensure_run, raw)
    assert created['ok'], created
    evidence = []

    def record(row):
        evidence.append(row)
        report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()

        async def call(tool, arguments=None, *, error=None, label=None):
            supplied = {'preset': 'full', **(arguments or {})}
            previous = set((raw.directory / 'responses').glob('*.json'))
            response = await session.call_tool(tool, supplied)
            data = response.structuredContent
            files = set((raw.directory / 'responses').glob('*.json')) - previous
            row = {'tool': tool, 'arguments': supplied, 'label': label, 'result': data,
                   'native_files': [str(p.relative_to(ROOT)) for p in sorted(files)]}
            if files:
                assert len(files) == 1, files
                original = json.loads(next(iter(files)).read_text())
                row.update(execution=original.get('execution'), native_error=original.get('error'))
            record(row)
            assert data == json.loads(response.content[0].text), response
            assert response.isError == bool(error) and data.get('error', {}).get('code') == error, data
            return data

        async def native(operation='get_state', token=None, arguments=None):
            value = await asyncio.to_thread(raw.call, operation, token, arguments=arguments,
                                           response_options={'include_divination_image': False})
            record({'native_operation': operation, 'arguments': arguments, 'result': value})
            return value

        async def observe(action=None):
            deadline = time.monotonic() + 25
            while True:
                value = await call('get_observation')
                if action is None or action in value['available_actions']: return value
                assert time.monotonic() < deadline, value
                await asyncio.sleep(.15)

        async def reject(label, hint):
            before = (await native())['state']
            result = await call('advance_dialogue', error='illegal_action', label=label)
            facts = evidence[-1]
            assert hint.lower() in result['error']['message'].lower(), result
            assert result['error']['recovery'] == 'choose_legal_action', result
            assert facts['native_error']['action_submitted'] is False, facts
            assert facts['execution']['ui_interaction_started'] is False, facts
            assert facts['execution']['action_submission_observed'] is False, facts
            after = (await native())['state']
            assert before['snapshot_id'] == after['snapshot_id'], (before, after)

        await call('advance_dialogue', error='observation_required', label='cold')
        mode = args.scenario
        if mode == 'wrong_room':
            await observe('end_turn')
            await reject('wrong_room', 'dialogue')
            await call('end_turn', label='direct_end_turn')
            return
        if mode in {'basic', 'selection', 'rewards'}:
            value = await observe('choose_ancient_option')
            if mode == 'basic': await reject('gifts_ready', 'choose_ancient_option')
            await call('choose_ancient_option', {'option_id': value['ancient']['options'][0]['id']}, label='direct_gift')
            if mode == 'selection':
                await reject('selection_cover', 'inspect_selection')
                await call('selection_option', {'option_id': 'bundle:0'}, label='direct_bundle_preview')
            elif mode == 'rewards':
                await reject('rewards_cover', 'inspect_rewards')
                await call('proceed', label='direct_reward_proceed')
            else:
                await reject('gift_finished', 'proceed')
                await call('proceed', label='direct_proceed')
            return
        architect = mode == 'architect'
        if architect:
            await observe('proceed')
            await call('proceed', label='enter_architect')
        state = await observe('advance_dialogue')
        if mode == 'stale':
            changed = await native('advance_dialogue', state.get('snapshot_id') or (await native())['state']['snapshot_id'])
            assert changed['ok'], changed
            await call('advance_dialogue', error='stale_state', label='stale')
            await call('advance_dialogue', error='observation_required', label='after_stale')
            await observe()
            return
        for view, close in [('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')]:
            await call(view)
            await reject(view + '_covered', close)
            await call(close, label='direct_' + close)
            state = await observe('advance_dialogue')
        for invalid in ({'extra': True}, {'preset': 'summary'}):
            await call('advance_dialogue', invalid, error='invalid_request', label='local_invalid')
        current = (await native())['state']
        invalid = await native('advance_dialogue', current['snapshot_id'], {'extra': True})
        assert invalid['error']['code'] == 'invalid_request' and invalid['error']['action_submitted'] is False, invalid
        key = 'epilogue' if architect else 'ancient'
        count = 0
        while 'advance_dialogue' in state['available_actions']:
            previous = state[key]['dialogue']
            receipt = await call('advance_dialogue', {'preset': 'default'} if mode == 'default' else None,
                                 label='advance_' + str(count))
            assert receipt['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, receipt
            assert set(receipt) == {'scene', 'screen', 'available_actions', 'transition'}, receipt
            state = (await native())['state']
            assert previous != state[key]['dialogue'], (previous, state[key])
            if not architect: assert len(state[key]['dialogue']) == len(previous) + 1, state[key]
            count += 1
            assert count < 25
        if architect:
            assert state['epilogue']['continue'] is None and state['epilogue']['proceed']['enabled'], state
            await reject('architect_final', 'proceed')
            final = await call('proceed', label='direct_final_proceed')
            assert final['transition']['stop_reason'] == 'run_won', final
            await call('advance_dialogue', error='observation_required', label='terminal_no_permission')
        else:
            assert state['ancient']['continue'] is None and any(o['enabled'] for o in state['ancient']['options']), state
            await reject('dialogue_finished', 'choose_ancient_option')
            await call('choose_ancient_option', {'option_id': state['ancient']['options'][0]['id']}, label='direct_final_gift')
        record({'advanced_lines': count})
    print('PASS', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证对话推进的具体拒绝及已有许可恢复。')
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
