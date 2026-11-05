"""Capture exposed treasure details, covered refusals and read-only recovery."""
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

SCENARIOS = ('basic', 'empty', 'extra', 'nested', 'choice', 'no_treasure', 'map_pending', 'display_red', 'display')


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
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

            async def native(operation, arguments=None):
                result = await asyncio.to_thread(raw.call, operation, arguments=arguments)
                record({'native_operation': operation, 'arguments': arguments, 'result': result})
                assert result['ok'], result
                return result['state']

            async def reject(label, *, permission=True):
                result = await call('inspect_treasure', error='illegal_action', label=label)
                expected = ('close_card_view' if 'deck' in label else 'close_map' if 'map' in label
                    else 'inspect_selection' if 'selection' in label else 'inspect_rewards' if 'rewards' in label
                    else 'No treasure room')
                assert expected in result['error']['message'], result
                assert result['error']['recovery'] == ('choose_legal_action' if permission else 'get_observation'), result
                return result

            async def inspect(label):
                value = await call('inspect_treasure', label=label)
                assert set(value) == {'scene', 'screen', 'treasure'}, value
                assert value['scene'] == 'treasure' and value['screen'] == {'status': 'visible'}, value
                assert value['treasure']['status'] == 'visible', value
                return value

            if args.scenario == 'no_treasure':
                await reject('no_initial_permission', permission=False)
                await call('end_turn', error='observation_required')
                await call('get_observation')
                await reject('wrong_scene_with_permission')
                await call('end_turn', label='direct_after_read_refusal')
                return

            closed = await inspect('closed_full')
            assert closed['treasure'] == {'status': 'visible', 'chest': 'closed', 'relic': None, 'proceed': None}, closed
            assert await inspect('repeat_closed_full') == closed
            compact = await call('inspect_treasure', {'preset': 'default'}, label='closed_default')
            assert compact['treasure'] == {'status': 'visible', 'chest': 'closed', 'relic': None}, compact
            empty_summary = await call('inspect_treasure', {'preset': 'summary'}, label='closed_summary')
            assert empty_summary == compact, empty_summary
            observed = await call('get_observation')
            assert observed['treasure'] == closed['treasure'], observed

            if args.scenario == 'basic':
                await call('inspect_deck')
                await reject('deck_covered')
                await call('close_card_view')
                await inspect('after_deck')
                await call('inspect_map')
                await reject('map_covered')
                # Reaching the native refusal proves the read kept existing permission.
                await call('loot_treasure', error='illegal_action', label='native_action_after_read_refusal')
                await call('close_map')
                await call('inspect_treasure', {'preset': 'bad'}, 'invalid_request', 'invalid_preset')

            receipt = await call('loot_treasure', {'open_only': True})
            if args.scenario == 'extra':
                assert receipt['scene'] == 'rewards', receipt
                rewards = await call('inspect_rewards')
                await reject('extra_rewards_covered')
                claimed = await call('claim_reward', {'reward_id': rewards['rewards']['items'][0]['id']}, label='direct_claim_after_read_refusal')
                if claimed['scene'] == 'rewards':
                    await call('proceed')

            opened = await inspect('opened_full')
            if args.scenario == 'display_red':
                checks = []
                for mode in ('no_hover', 'offscreen'):
                    await native('set_test_treasure_display', {'mode': mode})
                    try:
                        value = await native('inspect_treasure')
                        relic = value['treasure']['relic']
                        checks.append(relic is not None and (mode != 'no_hover' or relic['description'] is None))
                    finally:
                        await native('set_test_treasure_display', {'mode': 'normal'})
                record({'native_boundary_checks': checks})
                assert all(checks), checks
                return
            if args.scenario == 'display':
                for mode in ('no_hover', 'disabled', 'offscreen', 'hidden', 'transparent', 'clipped'):
                    await native('set_test_treasure_display', {'mode': mode})
                    try:
                        value = await call('inspect_treasure', label=mode + '_full')
                        compact = await call('inspect_treasure', {'preset': 'default'}, label=mode + '_default')
                        summary = await call('inspect_treasure', {'preset': 'summary'}, label=mode + '_summary')
                        relic = value['treasure']['relic']
                        if mode in {'hidden', 'transparent', 'clipped'}:
                            assert relic is None and compact['treasure']['relic'] is None and summary['treasure']['relic'] is None, value
                        else:
                            assert relic['name'] == 'Anchor' and relic['enabled'] is False, value
                            if mode in {'no_hover', 'disabled'}:
                                assert relic['description'] is None and relic['hover_tips'] == [], value
                                assert value['notes']['hover_tips_unavailable']['sources'] == ['treasure.relic'], value
                                assert 'description' not in compact['treasure']['relic'] and 'notes' not in summary, (compact, summary)
                            else:
                                assert relic['description'] and 'notes' not in value, value
                            assert summary['treasure']['relic'] == {'name': 'Anchor', 'enabled': False}, summary
                        for preset in ('full', 'default', 'summary'):
                            observation = await call('get_observation', {'preset': preset}, label=mode + '_observation_' + preset)
                            assert observation['treasure'] == summary['treasure'], observation
                            assert 'inspect_treasure' in observation['available_actions'] and 'loot_treasure' not in observation['available_actions'], observation
                        await call('loot_treasure', error='illegal_action', label=mode + '_cannot_loot')
                    finally:
                        await native('set_test_treasure_display', {'mode': 'normal'})
                assert await inspect('restored_full') == opened

            open_summary = await call('inspect_treasure', {'preset': 'summary'}, label='opened_summary')
            if args.scenario == 'empty':
                assert opened['treasure']['relic'] is None and opened['treasure']['proceed']['enabled'], opened
                value = await call('inspect_treasure', {'preset': 'default'}, label='empty_default')
                assert 'relic' in value['treasure'] and value['treasure']['relic'] is None, value
            else:
                relic = opened['treasure']['relic']
                assert relic and set(relic) == {'name', 'enabled', 'description', 'hover_tips'}, opened
                assert relic['enabled'] is True and relic['description'], opened
                assert all(set(tip) == {'title', 'description'} for tip in relic['hover_tips']), relic
                for preset in ('full', 'default', 'summary'):
                    observation = await call('get_observation', {'preset': preset}, label='observation_' + preset)
                    assert observation['treasure']['relic'] == {'name': relic['name'], 'enabled': True}, observation
                    assert observation['treasure'] == open_summary['treasure'], observation
                await call('inspect_treasure', {'preset': 'default'}, label='opened_default')
                receipt = await call('loot_treasure')
                if args.scenario == 'nested':
                    assert receipt['scene'] == 'rewards', receipt
                    await reject('nested_rewards_covered')
                    await call('proceed', label='direct_proceed_after_read_refusal')
                elif args.scenario == 'choice':
                    assert receipt['transition']['stop_reason'] == 'choice_required', receipt
                    selection = await call('inspect_selection')
                    await reject('selection_covered')
                    for card in selection['selection']['cards'][:3]:
                        await call('select_card', {'card_id': card['id']})
                    await call('inspect_selection')
                    await call('selection_option', {'option_id': 'confirm'})
                elif args.scenario == 'map_pending':
                    assert receipt['screen']['view'] == 'map', receipt
                    await reject('obtain_map_covered')
                    await call('close_map')

            collected = await inspect('collected_full')
            assert collected['treasure']['chest'] == 'open' and collected['treasure']['relic'] is None, collected
            assert not collected['treasure']['proceed']['skips_remaining'], collected
            await call('proceed')
    print('PASS treasure inspection review:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
