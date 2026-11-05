"""Audit rest-site details, cover boundaries and pure-read permission recovery."""
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

SCENARIOS = ('no_rest', 'basic', 'disabled', 'tent', 'selection', 'heal_rewards', 'dig', 'display_red', 'display')


async def verify(args):
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, *, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                old = set((raw.directory / 'responses').glob('*.json'))
                reply = await session.call_tool(tool, arguments)
                data = reply.structuredContent
                row = {'tool': tool, 'arguments': arguments, 'result': data, 'label': label,
                    'image_count': sum(part.type == 'image' for part in reply.content)}
                added = set((raw.directory / 'responses').glob('*.json')) - old
                if added:
                    assert len(added) == 1, added
                    original = json.loads(added.pop().read_text())
                    row.update(native_error=original.get('error'), execution=original.get('execution'))
                evidence.append(row)
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert data == json.loads(reply.content[0].text), reply
                assert reply.isError == bool(error), data
                assert data.get('error', {}).get('code') == error, data
                return data

            async def native(operation, arguments=None):
                reply = await asyncio.to_thread(raw.call, operation, arguments=arguments)
                evidence.append({'native_operation': operation, 'arguments': arguments, 'result': reply})
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert reply['ok'], reply
                return reply['state']

            async def details(label, preset='full'):
                value = await call('inspect_rest_site', {'preset': preset}, label=label)
                assert value['scene'] == 'rest_site' and value['screen'] == {'status': 'visible'}, value
                assert value['rest_site']['status'] == 'visible', value
                assert all(option['description'] for option in value['rest_site']['options']), value
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                assert evidence[-1]['image_count'] == 0, evidence[-1]
                return value

            async def reject(label, recovery='choose_legal_action'):
                value = await call('inspect_rest_site', error='illegal_action', label=label)
                assert value['error']['recovery'] == recovery, value
                hint = 'close_map' if label == 'map_covered' else 'close_card_view' if label == 'deck_covered' else (
                    'inspect_selection' if label == 'selection_covered' else 'inspect_rewards' if label == 'reward_covered' else 'rest site')
                assert hint in value['error']['message'], value
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                return value

            scenario = args.scenario
            if scenario == 'no_rest':
                await reject('no_rest_first_read', 'get_observation')
                await call('end_turn', error='observation_required', label='failed_first_read_has_no_permission')
                await call('get_observation')
                await reject('no_rest_existing_permission')
                await call('end_turn', label='continue_after_read_rejection')
                return

            initial = await details(scenario + '_initial')
            if scenario == 'basic':
                assert initial['rest_site']['proceed'] is None, initial
            if scenario == 'display_red':
                try:
                    await native('set_test_rest_site_display', {'mode': 'offscreen'})
                    observed = await call('get_observation', label='offscreen_observation_red')
                    assert any(o['id'] == 'HEAL' for o in observed['rest_site']['options']), observed
                finally: await native('set_test_rest_site_display', {'mode': 'normal'})
                return
            if scenario == 'display':
                for mode in ('no_hover', 'disabled', 'offscreen', 'hidden', 'transparent', 'clipped', 'fade'):
                    try:
                        configured = await native('set_test_rest_site_display', {'mode': mode})
                        value = await call('inspect_rest_site', label=mode + '_full')
                        rows = {o['id']: o for o in value['rest_site']['options']}
                        if mode in {'hidden', 'transparent', 'clipped'}:
                            assert 'HEAL' not in rows, value
                        else: assert 'HEAL' in rows, value
                        if mode == 'no_hover':
                            assert rows['HEAL']['description'] is None and rows['HEAL']['enabled'] is False, value
                            assert value['notes']['hover_tips_unavailable']['sources'] == ['rest_site.options.HEAL'], value
                            filtered = await call('inspect_rest_site', {'option_ids': ['SMITH']}, label='no_hover_filtered')
                            assert 'hover_tips_unavailable' not in filtered.get('notes', {}), filtered
                        if mode == 'fade':
                            assert configured['ready'] is False, configured
                            assert all(not row['enabled'] for row in rows.values()), value
                        summary = await call('inspect_rest_site', {'preset': 'summary'}, label=mode + '_summary')
                        assert 'description' not in summary['rest_site'], summary
                        assert all('description' not in o for o in summary['rest_site']['options']), summary
                        assert 'hover_tips_unavailable' not in summary.get('notes', {}), summary
                        observed = await call('get_observation', label=mode + '_observation')
                        assert [o['id'] for o in observed['rest_site']['options']] == list(rows), observed
                        assert 'description' not in observed['rest_site'], observed
                        current = await native('get_state')
                        assert 'inspect_rest_site' in current['available_actions'], current
                    finally: await native('set_test_rest_site_display', {'mode': 'normal'})
                guards = await native('check_test_dispatch')
                assert guards['test_mode_off'] == guards['suite_and_scenarios_off'] and guards['test_mode_off'] >= 79, guards
                return
            summary = await call('inspect_rest_site', {'preset': 'summary'}, label=scenario + '_summary')
            assert 'description' not in summary['rest_site'], summary
            assert all('description' not in option for option in summary['rest_site']['options']), summary
            for preset in ('full', 'default', 'summary'):
                observed = await call('get_observation', {'preset': preset}, label=scenario + '_observation_' + preset)
                assert 'description' not in observed['rest_site'], observed
                assert all('description' not in option for option in observed['rest_site']['options']), observed
            selected = await call('inspect_rest_site', {'preset': 'summary', 'option_ids': ['SMITH', 'HEAL', 'SMITH', 'UNKNOWN']}, label=scenario + '_filtered')
            assert [o['id'] for o in selected['rest_site']['options']] == ['HEAL', 'SMITH'], selected
            assert selected['errors'] == [{'code': 'option_ids_not_found', 'option_ids': ['UNKNOWN']}], selected
            empty = await call('inspect_rest_site', {'option_ids': []}, label=scenario + '_empty_filter')
            assert empty['rest_site']['options'] == [], empty
            await call('inspect_rest_site', {'option_ids': ['  ']}, error='invalid_request', label='invalid_filter')
            compact = await details(scenario + '_default', 'default')
            if initial['rest_site']['description'] is None:
                assert 'description' not in compact['rest_site'], compact
            if initial['rest_site']['proceed'] is None:
                assert 'proceed' not in compact['rest_site'], compact

            if scenario == 'basic':
                assert {o['id'] for o in initial['rest_site']['options']} == {'HEAL', 'SMITH'}, initial
                await call('inspect_map')
                covered = await call('get_observation', label='map_cover_observation')
                assert covered['rest_site']['status'] == 'covered', covered
                await reject('map_covered')
                await call('close_map', label='close_map_after_rejection')
                await call('inspect_deck')
                await reject('deck_covered')
                await call('close_card_view', label='close_deck_after_rejection')
                await call('choose_rest_option', {'option_id': 'HEAL'}, label='rest_after_details')
                ended = await details('activity_complete')
                assert ended['rest_site']['options'] == [] and ended['rest_site']['proceed']['enabled'], ended
                return
            if scenario == 'disabled':
                options = {o['id']: o for o in initial['rest_site']['options']}
                assert not options['SMITH']['enabled'] and not options['COOK']['enabled'], initial
                assert options['SMITH']['description'] and options['COOK']['description'], initial
                await call('choose_rest_option', {'option_id': 'HEAL'}, label='continue_after_local_rejections')
                await details('disabled_activity_complete')
                return
            if scenario == 'tent':
                assert {o['id'] for o in initial['rest_site']['options']} == {'HEAL', 'SMITH', 'COOK', 'KINDLE', 'LIFT'}, initial
                await call('choose_rest_option', {'option_id': 'LIFT'})
                after = await details('tent_after_lift')
                assert {o['id'] for o in after['rest_site']['options']} == {'HEAL', 'SMITH', 'COOK', 'KINDLE'}, after
                assert after['rest_site']['proceed']['enabled'], after
                return
            if scenario == 'selection':
                await call('choose_rest_option', {'option_id': 'SMITH'})
                covered = await call('get_observation', label='selection_cover_observation')
                assert covered['rest_site']['status'] == 'covered', covered
                await reject('selection_covered')
                await call('selection_option', {'option_id': 'cancel'}, label='cancel_after_read_rejection')
                await details('after_selection_cancel')
                return
            if scenario == 'heal_rewards':
                result = await call('choose_rest_option', {'option_id': 'HEAL'})
                assert result['scene'] == 'rewards', result
                await reject('reward_covered')
                await call('proceed', label='finish_reward_after_read_rejection')
                await details('after_nested_reward')
                return
            if scenario == 'dig':
                assert any(o['id'] == 'DIG' and o['description'] for o in initial['rest_site']['options']), initial
                assert 'rewards' not in initial and 'relic' not in initial, initial
                return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
