"""Verify Trial responses, preflight recovery, popup ownership, and native outcomes."""
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

            async def call(tool, arguments=None, *, error=None, label=None):
                supplied = {'preset': 'full', **(arguments or {})}
                previous = set((raw.directory / 'responses').glob('*.json'))
                response = await session.call_tool(tool, supplied)
                result = response.structuredContent
                files = set((raw.directory / 'responses').glob('*.json')) - previous
                row = {'case': name, 'tool': tool, 'arguments': supplied, 'label': label, 'result': result, 'images': sum((p.type == 'image' for p in response.content)), 'native_files': [str(p.relative_to(ROOT)) for p in sorted(files)]}
                if files:
                    assert len(files) == 1, files
                    original = json.loads(next(iter(files)).read_text())
                    row.update(native_error=original.get('error'), execution=original.get('execution'))
                record(row)
                assert result == json.loads(response.content[0].text) and response.isError == bool(error), response
                assert result.get('error', {}).get('code') == error, result
                return result

            async def native(operation, token=None, arguments=None):
                result = await asyncio.to_thread(raw.call, operation, token, arguments=arguments, response_options={'include_divination_image': False})
                record({'case': name, 'native_operation': operation, 'result': result})
                return result

            async def reject(label):
                before = (await native('get_state'))['state']
                result = await call('respond_to_confirmation', {'option': 'cancel'}, error='illegal_action', label=label)
                hints = {'no_dialog': 'No supported Trial confirmation', 'already_closed': 'No supported Trial confirmation', 'unowned_dialog': 'not a supported Trial', 'inspect_map_no_dialog': 'close_map', 'inspect_deck_no_dialog': 'close_card_view'}
                assert hints[label] in result['error']['message'], result
                assert result['error']['recovery'] == 'choose_legal_action', result
                assert evidence[-1]['native_error']['action_submitted'] is False, evidence[-1]
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                assert evidence[-1]['execution']['action_submission_observed'] is False, evidence[-1]
                after = (await native('get_state'))['state']
                assert before['snapshot_id'] == after['snapshot_id'], (before, after)
                return result

            async def open_dialog(state):
                options = state['event']['options']
                lethal = next((o for o in options if o.get('lethal_warning')), None)
                if lethal is None:
                    await call('choose_event_option', {'option_id': options[1]['id']}, label='first_refusal')
                    state = await call('get_observation')
                    lethal = next((o for o in state['event']['options'] if o.get('lethal_warning')))
                receipt = await call('choose_event_option', {'option_id': lethal['id']}, label='open_confirmation')
                assert receipt['screen'] == {'status': 'visible', 'view': 'confirmation'}, receipt
                state = await call('get_observation', label='confirmation_observed')
                assert state['confirmation']['type'] == 'abandon_run' and all((o['enabled'] for o in state['confirmation']['options'])), state
                assert state['available_actions'] == ['respond_to_confirmation'], state
                return state
            await call('respond_to_confirmation', {'option': 'cancel'}, error='observation_required', label='cold_call')
            state = await call('get_observation')
            if name == 'no_dialog':
                await reject('no_dialog')
                await call('end_turn', label='legal_after_rejection')
                return
            if name == 'covered':
                for view, close in [('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')]:
                    await call(view)
                    await reject(view + '_no_dialog')
                    await call(close)
                return
            if name == 'unowned':
                opened = await native('open_test_unowned_confirmation')
                assert opened['ok'], opened
                state = await call('get_observation', label='unowned_observed')
                assert state['confirmation'] is None and state['screen'] == {'status': 'covered', 'view': 'confirmation'}, state
                await reject('unowned_dialog')
                truth = await native('check_test_confirmation')
                assert not truth['state']['abandoned'], truth
                await native('cancel_test_confirmation')
                return
            state = await open_dialog(state)
            if name == 'buttons':
                result = await native('set_test_confirmation_buttons', arguments={'confirm': False, 'cancel': False})
                assert result['ok'], result
                state = await call('get_observation', label='both_disabled_observed')
                assert state['confirmation']['status'] == 'visible' and (not any((o['enabled'] for o in state['confirmation']['options']))), state
                assert state['available_actions'] == [], state
                result = await call('respond_to_confirmation', {'option': 'cancel'}, error='illegal_action', label='both_disabled_rejected')
                assert 'No confirmation button' in result['error']['message'] and result['error']['recovery'] == 'choose_legal_action', result
                await native('set_test_confirmation_buttons', arguments={'confirm': False, 'cancel': True})
                state = await call('get_observation', label='confirm_disabled_observed')
                assert state['available_actions'] == ['respond_to_confirmation'], state
                assert {o['id']: o['enabled'] for o in state['confirmation']['options']} == {'confirm': False, 'cancel': True}, state
                before = (await native('get_state'))['state']['snapshot_id']
                result = await call('respond_to_confirmation', {'option': 'confirm'}, error='illegal_action', label='disabled_confirm')
                assert 'disabled' in result['error']['message'] and result['error']['recovery'] == 'choose_legal_action', result
                assert evidence[-1]['native_error']['action_submitted'] is False and (not evidence[-1]['execution']['ui_interaction_started']), evidence[-1]
                after = (await native('get_state'))['state']['snapshot_id']
                assert before == after
                await call('respond_to_confirmation', {'option': 'cancel'}, label='cancel_after_disabled')
                return
            if name == 'replacement':
                old = (await native('get_state'))['state']['snapshot_id']
                opened = await native('reopen_test_confirmation')
                assert opened['ok'], opened
                fresh = (await native('get_state'))['state']['snapshot_id']
                assert old != fresh
                stale = await native('respond_to_confirmation', old, {'option': 'confirm'})
                assert stale['error']['code'] == 'stale_state', stale
                await call('respond_to_confirmation', {'option': 'cancel'}, error='stale_state', label='replaced_popup')
                await call('respond_to_confirmation', {'option': 'cancel'}, error='observation_required', label='after_stale')
                await call('get_observation')
                await call('respond_to_confirmation', {'option': 'cancel'}, label='cancel_fresh')
                return
            if name == 'confirm':
                receipt = await call('respond_to_confirmation', {'option': 'confirm'}, label='confirm_run')
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == 'run_lost', receipt
                truth = await native('check_test_confirmation')
                assert truth['state']['abandoned'] and truth['state']['ended'] and (not truth['state']['pending']) and (truth['state']['hp'] == 0), truth
                await call('respond_to_confirmation', {'option': 'cancel'}, error='observation_required', label='after_run_lost')
                state = await call('get_observation', label='run_result_observed')
                assert state['confirmation'] is None, state
                return
            assert name == 'cancel'
            for invalid in ({'option': True}, {'option': 'yes'}, {'option': 'cancel', 'extra': 1}, {}):
                await call('respond_to_confirmation', invalid, error='invalid_request', label='local_invalid')
            token = (await native('get_state'))['state']['snapshot_id']
            bad = await native('respond_to_confirmation', token, {'option': 'yes'})
            assert bad['error']['code'] == 'invalid_request' and bad['error']['action_submitted'] is False, bad
            before = (await native('check_test_event'))['state']
            receipt = await call('respond_to_confirmation', {'option': 'cancel'}, label='cancel_full')
            assert receipt['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, receipt
            assert receipt['scene'] == 'event' and receipt['screen'] == {'status': 'visible'}, receipt
            after = (await native('check_test_event'))['state']
            assert before == after, (before, after)
            await reject('already_closed')
            state = (await native('get_state'))['state']
            lethal = next((o for o in state['event']['options'] if o.get('lethal_warning')))
            await call('choose_event_option', {'option_id': lethal['id']}, label='reopen_after_rejection')
            await call('get_observation', label='reopened_observed')
            await call('respond_to_confirmation', {'option': 'cancel', 'preset': 'default'}, label='cancel_default')
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('no_dialog', 'cancel', 'replacement', 'unowned', 'covered', 'confirm', 'buttons'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
