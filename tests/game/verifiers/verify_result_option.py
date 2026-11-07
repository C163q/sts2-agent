"""Verify result action recovery, native navigation and stable timeline references."""
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


async def verify(args):
    if args.report.exists(): raise FileExistsError(args.report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=100)
    assert (await asyncio.to_thread(ensure_run, raw))['ok']
    rows = []

    def record(row):
        rows.append(row)
        args.report.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')

    async def native(operation='get_state', arguments=None, token=None):
        value = await asyncio.to_thread(raw.call, operation, token, arguments=arguments,
                                      response_options={'include_divination_image': False})
        record({'native_operation': operation, 'arguments': arguments, 'result': value})
        assert value['ok'], value
        return value['state']

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()

        async def call(tool, arguments=None, *, label=None, error=None):
            supplied = {'preset': 'full', **(arguments or {})}
            before = set((raw.directory / 'responses').glob('*.json'))
            reply = await session.call_tool(tool, supplied)
            result = reply.structuredContent
            paths = set((raw.directory / 'responses').glob('*.json')) - before
            row = {'tool': tool, 'arguments': supplied, 'label': label, 'result': result,
                   'native_files': [str(p.relative_to(ROOT)) for p in sorted(paths)]}
            if paths:
                assert len(paths) == 1
                packet = json.loads(next(iter(paths)).read_text())
                row.update(execution=packet.get('execution'), native_error=packet.get('error'))
            record(row)
            assert result == json.loads(reply.content[0].text), reply
            assert reply.isError == bool(error) and result.get('error', {}).get('code') == error, result
            return result

        async def observe(action=None, label=None):
            deadline = time.monotonic() + 35
            while True:
                value = await call('get_observation', label=label)
                if action is None or action in value['available_actions']: return value
                assert time.monotonic() < deadline, value
                await asyncio.sleep(.2)

        async def reject(option, label, message):
            before = await native()
            value = await call('run_result_option', {'option_id': option}, label=label, error='illegal_action')
            item = rows[-1]
            assert value['error']['recovery'] == 'choose_legal_action', value
            assert message.lower() in value['error']['message'].lower(), value
            assert item['native_error']['action_submitted'] is False, item
            assert item['execution']['ui_interaction_started'] is False, item
            assert before['snapshot_id'] == (await native())['snapshot_id'], label

        async def choose(option, label, preset='full'):
            value = await call('run_result_option', {'option_id': option, 'preset': preset}, label=label)
            assert value['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, value
            assert 'run_result' not in value, value
            packet = json.loads((ROOT / rows[-1]['native_files'][0]).read_text())
            return value, packet['state']

        if args.scenario == 'basic':
            await call('run_result_option', {'option_id': 'continue'}, label='cold', error='observation_required')
            await observe('end_turn')
            await reject('continue', 'wrong_room', 'No run result')
            await call('end_turn', label='direct_corrected_end_turn')
            await observe('end_turn')
            for bad in ({}, {'option_id': None}, {'option_id': 1}, {'option_id': 'epoch:-1'},
                        {'option_id': 'continue\n'}, {'option_id': 'continue', 'extra': 1},
                        {'option_id': 'continue', 'preset': 'summary'}):
                await call('run_result_option', bad, label='local_arguments', error='invalid_request')
            await call('end_turn', label='direct_after_local_errors')
            gate = await native('check_test_dispatch')
            assert gate['test_mode_off'] == gate['suite_and_scenarios_off'] and gate['test_mode_off'] >= 86, gate
            return

        value = await observe()
        if value['scene'] == 'rewards':
            await call('proceed')
            for index in range(15):
                value = await observe()
                if value['scene'] == 'run_result': break
                step = await call('advance_dialogue' if 'advance_dialogue' in value['available_actions'] else 'proceed')
                if step['transition']['stop_reason'] == 'run_won':
                    await call('run_result_option', {'option_id': 'continue'}, label='terminal_read_required', error='observation_required')
            else: raise AssertionError('No result page')
        await observe('run_result_option', 'outcome')
        if args.scenario == 'history':
            await native('prepare_test_browsable_result')
            await observe('run_result_option')
            await choose('continue', 'to_summary')
            await native('prepare_test_browsable_history')
            value = await observe('run_result_option', 'history')
            assert value['run_result']['phase'] == 'history', value
            checks = await native('check_test_browsable_content')
            assert checks['checks'] and all(c['passed'] for c in checks['checks']), checks
            await call('inspect_run_result')
            receipt, state = await choose('back', 'history_back')
            assert state['run_result']['phase'] == 'summary', receipt
            return

        if args.scenario == 'errors':
            for mode, text in (('partial', 'displaying'), ('disabled', 'enabled')):
                await native('set_test_presentation', {'mode': mode})
                try:
                    await observe()
                    await reject('continue', mode, text)
                    await reject('missing', mode + '_direct_correction', text)
                finally: await native('set_test_presentation', {'mode': 'normal'})
                await observe('run_result_option')
            await reject('missing', 'unknown_option', 'not offered')
        _, state = await choose('continue', 'outcome_continue')
        assert state['run_result']['phase'] == 'summary', state
        if args.scenario == 'errors':
            await reject('view_run', 'unoffered_view_run', 'not offered')
            state = await native()
            await native('run_result_option', {'option_id': 'main_menu'}, state['snapshot_id'])
            await call('run_result_option', {'option_id': 'continue'}, label='stale', error='stale_state')
            await call('run_result_option', {'option_id': 'continue'}, label='after_stale', error='observation_required')
        else: await choose('main_menu', 'summary_main_menu')

        revealed = None
        reopened = False
        paginated = False
        scroll_checked = False
        for index in range(60):
            current = await observe(label='page_' + str(index))
            if current['scene'] == 'main_menu': break
            body = current['run_result']
            enabled = [o for o in body['options'] if o['enabled']]
            assert enabled, current
            if body['phase'] == 'timeline':
                if revealed and not reopened:
                    option = next((o for o in enabled if o['id'] == revealed), None)
                    assert option is not None and option['text'] == 'View', body
                    await choose(revealed, 'reopen_completed_epoch')
                    view = await call('inspect_run_result', label='reopened_epoch')
                    assert view['run_result']['phase'] == 'epoch'
                    pager = next((o for o in view['run_result']['options']
                                  if o['enabled'] and o['id'] in {'next_chapter', 'previous_chapter'}), None)
                    if pager:
                        await choose(pager['id'], 'chapter_page')
                        paginated = True
                    await choose('continue', 'close_reopened_epoch')
                    reopened = True
                    continue
                if args.scenario == 'flow' and reopened and not scroll_checked:
                    fault = await native('set_test_result_option', {'mode': 'arm_scroll'})
                    try:
                        await call('inspect_run_result')
                        value = await call('run_result_option', {'option_id': fault['option_id']},
                                           label='scroll_changed', error='illegal_action')
                        assert rows[-1]['execution']['ui_interaction_started'] is True, rows[-1]
                        assert 'scroll' in value['error']['message'].lower(), value
                        await call('run_result_option', {'option_id': 'back'}, label='after_scroll', error='observation_required')
                    finally: await native('set_test_result_option', {'mode': 'reset'})
                    scroll_checked = True
                    continue
                pending = [o for o in enabled if o['text'] == 'Reveal']
                if args.scenario == 'flow' and not pending and not paginated:
                    for view_option in (o for o in enabled if o['text'] == 'View'):
                        await choose(view_option['id'], 'find_story_chapter')
                        before = await call('inspect_run_result')
                        pager = next((o for o in before['run_result']['options']
                                      if o['enabled'] and o['id'] in {'next_chapter', 'previous_chapter'}), None)
                        if pager:
                            await choose(pager['id'], 'chapter_page')
                            after = await call('inspect_run_result', label='chapter_after_page')
                            assert after['run_result']['phase'] == 'epoch'
                            assert after['run_result']['texts'] != before['run_result']['texts']
                            paginated = True
                        await choose('continue', 'close_story_chapter')
                        if paginated: break
                    assert paginated, 'The victory unlock fixture did not expose a story paginator'
                    continue
                selected = pending[-1] if pending else next(o for o in enabled if o['id'] == 'back')
                if pending and revealed is None: revealed = selected['id']
            else:
                selected = next(o for o in enabled if o['id'] in {'continue', 'confirm'})
            receipt, state = await choose(selected['id'], body['phase'] + '_' + str(index))
            if receipt['scene'] == 'main_menu':
                await call('run_result_option', {'option_id': 'back'}, label='menu_requires_read', error='observation_required')
                break
            if body['phase'] == 'epoch' and state['run_result']['phase'] == 'unlock':
                await choose('confirm', 'direct_confirm_' + str(index), 'default')
        else: raise AssertionError('Result flow did not return to menu')
        assert reopened, 'No completed epoch was reopened'
        if args.scenario == 'flow': assert scroll_checked
        record({'completed_reopened': reopened, 'chapter_paginated': paginated, 'scroll_checked': scroll_checked})
        await observe()
        await reject('continue', 'menu_without_result', 'associated')
        await native('reopen_test_timeline')
        await observe()
        await reject('back', 'unowned_timeline', 'associated')
        await native('close_test_timeline')
    print('PASS', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('basic', 'history', 'errors', 'flow'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
