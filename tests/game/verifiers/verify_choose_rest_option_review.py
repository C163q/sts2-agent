"""Verify rest action feedback, explicit rejection recovery and native effect boundaries."""
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

SCENARIOS = ('no_rest', 'basic', 'disabled', 'selection', 'rewards', 'counters', 'combat', 'targets')


async def verify(args):
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, *, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                old = set((raw.directory / 'responses').glob('*.json'))
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                row = {'tool': tool, 'arguments': arguments, 'result': result, 'label': label,
                    'image_count': sum(part.type == 'image' for part in response.content)}
                added = set((raw.directory / 'responses').glob('*.json')) - old
                if added:
                    assert len(added) == 1, added
                    native = json.loads(added.pop().read_text())
                    row.update(native_error=native.get('error'), execution=native.get('execution'))
                record(row)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def rejected(option_id, label, continuation, continuation_args=None):
                result = await call('choose_rest_option', {'option_id': option_id}, error='illegal_action', label=label)
                assert result['error']['message'] != 'The requested action is unavailable.', result
                assert result['error']['recovery'] == 'choose_legal_action', result
                hint = ('close_map' if label == 'map_covered' else 'close_card_view' if label == 'deck_covered'
                    else 'inspect_selection' if label == 'selection_covered' else 'inspect_rewards' if label == 'reward_covered'
                    else 'disabled' if label.startswith('disabled_') else 'inspect_rest_site' if label in {'unknown_option','wrong_case','already_consumed'}
                    else 'rest site')
                assert hint in result['error']['message'], result
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                assert evidence[-1]['native_error'].get('action_submitted') is False, evidence[-1]
                return await call(continuation, continuation_args, label=label + '_direct_continuation')

            await call('choose_rest_option', {'option_id': 'HEAL'}, error='observation_required', label='no_initial_permission')
            initial = await call('get_observation', label='initial')
            if args.scenario == 'no_rest':
                assert initial['scene'] == 'combat', initial
                await rejected('HEAL', 'no_rest', 'end_turn')
                return

            assert initial['scene'] == 'rest_site', initial
            if args.scenario == 'targets':
                for mode in ('no_hover', 'offscreen'):
                    try:
                        configured = await asyncio.to_thread(raw.call, 'set_test_rest_site_display', arguments={'mode': mode})
                        record({'native_operation': 'set_test_rest_site_display', 'arguments': {'mode': mode}, 'result': configured})
                        assert configured['ok'], configured
                        await call('get_observation', label=mode + '_observation')
                        result = await call('choose_rest_option', {'option_id': 'HEAL'}, error='illegal_action', label=mode + '_reject')
                        assert 'interactive' in result['error']['message'] and result['error']['recovery'] == 'choose_legal_action', result
                        assert evidence[-1]['native_error']['action_submitted'] is False, evidence[-1]
                        await call('choose_rest_option', {'option_id': 'SMITH'}, label=mode + '_direct_smith')
                        await call('selection_option', {'option_id': 'cancel'})
                    finally:
                        reset = await asyncio.to_thread(raw.call, 'set_test_rest_site_display', arguments={'mode': 'normal'})
                        record({'native_operation': 'set_test_rest_site_display', 'arguments': {'mode': 'normal'}, 'result': reset})
                        assert reset['ok'], reset
                return
            if args.scenario == 'combat':
                await call('choose_rest_option', {'option_id': 'HEAL'}, label='heal_before_combat')
                await call('proceed')
                graph = await call('inspect_map')
                await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]})
                finished = None
                for _ in range(80):
                    hand = await call('inspect_hand')
                    played = False
                    for card in sorted(hand['hand'], key=lambda c: c.get('type') != 'Attack'):
                        targets = await call('inspect_targets', {'card_id': card['id']})
                        if not targets['playable']: continue
                        arguments = {'card_id': card['id']}
                        if targets['requires_target']: arguments['target_id'] = targets['targets'][0]['id']
                        result = await call('play_card', arguments, label='combat_play')
                        played = True
                        break
                    if not played: result = await call('end_turn', label='combat_end_turn')
                    assert result['transition']['complete'], result
                    if result['transition']['stop_reason'] in {'combat_won', 'action_completed'}:
                        finished = result; break
                    assert result['transition']['stop_reason'] == 'player_ready', result
                assert finished is not None, 'Combat did not finish within the bounded action count.'
                changes = [e for e in finished['transition']['events'] if e['type'] == 'relic_counter_changed']
                assert [(e['relic']['name'], e['before'], e['after']) for e in changes] == [('Pumpkin Candle', 5, 4)], finished
                await call('inspect_rewards', label='after_combat_counter_change')
                return
            if args.scenario == 'counters':
                for operation in ('check_test_relic_counters', 'check_test_dispatch'):
                    reply = await asyncio.to_thread(raw.call, operation)
                    record({'native_operation': operation, 'result': reply})
                    assert reply['ok'], reply
                    if operation == 'check_test_relic_counters': assert reply['state']['passed'], reply
                    else: assert all(count == 80 for count in reply['state'].values()), reply
                await call('get_observation', label='after_native_checks')
                await call('choose_rest_option', {'option_id': 'LIFT'}, label='lift_after_checks')
            elif args.scenario == 'basic':
                for arguments in ({'option_id': ''}, {'option_id': 0}, {'option_id': 'HEAL', 'repeat': True}):
                    await call('choose_rest_option', arguments, error='invalid_request', label='local_invalid')
                await call('inspect_map')
                await rejected('HEAL', 'map_covered', 'close_map')
                await call('inspect_deck')
                await rejected('HEAL', 'deck_covered', 'close_card_view')
                await rejected('heal', 'wrong_case', 'inspect_rest_site')
                await rejected('UNKNOWN', 'unknown_option', 'inspect_rest_site')
                value = await call('choose_rest_option', {'option_id': 'HEAL'}, label='heal')
                assert value['transition']['complete'] and value['transition']['stop_reason'] == 'action_completed', value
                assert any(event['type'] == 'hp_changed' and event['before'] == 30 and event['after'] == 54
                    for event in value['transition']['events']), value
                assert evidence[-1]['image_count'] == 0, evidence[-1]
                await rejected('HEAL', 'already_consumed', 'proceed')
            elif args.scenario == 'disabled':
                for option in ('SMITH', 'COOK'):
                    await rejected(option, 'disabled_' + option.lower(), 'inspect_rest_site')
                await call('choose_rest_option', {'option_id': 'HEAL', 'preset': 'default'}, label='heal_default')
            elif args.scenario == 'selection':
                value = await call('choose_rest_option', {'option_id': 'SMITH'}, label='smith')
                assert value['transition']['stop_reason'] == 'choice_required', value
                assert value['transition']['events'] == [], value
                await rejected('HEAL', 'selection_covered', 'selection_option', {'option_id': 'cancel'})
                await call('choose_rest_option', {'option_id': 'SMITH'}, label='smith_after_cancel')
            elif args.scenario == 'rewards':
                value = await call('choose_rest_option', {'option_id': 'HEAL'}, label='heal_reward')
                assert value['transition']['stop_reason'] == 'action_completed' and value['scene'] == 'rewards', value
                await rejected('SMITH', 'reward_covered', 'proceed')

            native = await asyncio.to_thread(raw.call, 'choose_rest_option', 'not-current', arguments={'option_id': 'HEAL'})
            record({'native_operation': 'choose_rest_option', 'label': 'stale_state', 'result': native})
            assert native['error']['code'] == 'stale_state', native
            assert native['execution']['ui_interaction_started'] is False, native
    print(f'PASS: {args.scenario}; {len(evidence)} recorded calls; {args.report}')


def main():
    parser = argparse.ArgumentParser(description='核验火堆选择动作和拒绝恢复的当前行为。')
    parser.add_argument('--scenario', required=True, choices=SCENARIOS)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__': main()
