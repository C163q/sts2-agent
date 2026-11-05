"""Audit chest action boundaries, visible events and current preflight recovery."""
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
from tests.game.support.verification_actions import confirm_transform

SCENARIOS = ('basic', 'open', 'empty', 'extra', 'nested', 'choice', 'covered', 'no_treasure', 'map_pending', 'display')


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, arguments=None):
        reply = await asyncio.to_thread(raw.call, operation, arguments=arguments)
        record({'native_operation': operation, 'arguments': arguments, 'result': reply})
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

            def boundary(value, reason='action_completed'):
                assert value['transition']['complete'] and value['transition']['stop_reason'] == reason, value
                assert [e['sequence'] for e in value['transition']['events']] == list(range(1, len(value['transition']['events']) + 1)), value
                assert not {'treasure', 'player', 'top_bar', 'rewards'} & value.keys(), value

            async def reject(label, arguments=None):
                result = await call('loot_treasure', arguments, 'illegal_action', label)
                assert result['error'] == {'code': 'illegal_action', 'message': 'The requested action is unavailable.',
                                           'recovery': 'get_observation'}, result
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                return result

            await call('loot_treasure', error='observation_required', label='no_initial_permission')
            if args.scenario == 'no_treasure':
                await call('get_observation')
                await reject('wrong_scene')
                await call('end_turn', error='observation_required', label='after_wrong_scene_rejection')
                await call('get_observation')
                await call('end_turn')
                return

            await call('inspect_treasure')
            before = await native('check_test_treasure')
            if args.scenario == 'covered':
                await call('inspect_map')
                await reject('map_covered')
                await call('loot_treasure', error='observation_required', label='after_map_rejection')
                await call('close_map')
                await call('inspect_deck')
                await reject('deck_covered')
                await call('loot_treasure', error='observation_required', label='after_deck_rejection')
                await call('close_card_view')
            await call('loot_treasure', {'open_only': 1}, 'invalid_request', 'local_invalid')
            stepwise = args.scenario in {'open', 'display'}
            receipt = await call('loot_treasure', {'open_only': True} if stepwise else None, label='initial_loot')
            boundary(receipt, 'choice_required' if args.scenario == 'choice' else 'action_completed')
            events = receipt['transition']['events']

            if stepwise:
                assert any(e['type'] == 'gold_changed' for e in events) and not any(e['type'] == 'relic_obtained' for e in events), receipt
                shown = await call('inspect_treasure')
                assert shown['treasure']['relic']['name'] == 'Anchor', shown
                if args.scenario == 'display':
                    for mode in ('disabled', 'offscreen', 'hidden'):
                        await native('set_test_treasure_display', {'mode': mode})
                        try:
                            await call('inspect_treasure')
                            await reject(mode + '_rejected')
                            await call('loot_treasure', error='observation_required', label=mode + '_lost_permission')
                        finally:
                            await native('set_test_treasure_display', {'mode': 'normal'})
                    await call('inspect_treasure')
                else:
                    await reject('already_open', {'open_only': True})
                    await call('loot_treasure', error='observation_required', label='after_already_open_rejection')
                    await call('inspect_treasure')
                receipt = await call('loot_treasure', {'open_only': False, 'preset': 'default'}, label='take_opened_default')
                boundary(receipt)
                assert any(e['type'] == 'relic_obtained' for e in receipt['transition']['events']), receipt
            elif args.scenario == 'extra':
                assert receipt['scene'] == 'rewards' and not any(e['type'] == 'relic_obtained' for e in events), receipt
                assert (await native('check_test_treasure'))['relics'] == before['relics']
                rows = (await call('inspect_rewards'))['rewards']['items']
                await reject('extra_rewards_covered')
                await call('claim_reward', {'reward_id': rows[0]['id']}, 'observation_required', 'after_extra_rejection')
                await call('inspect_rewards')
                claimed = await call('claim_reward', {'reward_id': rows[0]['id']})
                if claimed['scene'] == 'rewards': await call('proceed')
                returned = await call('inspect_treasure')
                assert returned['treasure']['relic']['name'] == 'Anchor', returned
                assert (await native('check_test_treasure'))['relics'] == before['relics'], 'The earlier request continued to take the relic.'
                receipt = await call('loot_treasure', label='explicit_take_after_extra')
                boundary(receipt)
            elif args.scenario == 'nested':
                assert receipt['scene'] == 'rewards' and any(e['type'] == 'relic_obtained' for e in events), receipt
                await reject('nested_rewards_covered')
                await call('proceed', error='observation_required', label='after_nested_rejection')
                await call('inspect_rewards')
                await call('proceed')
            elif args.scenario == 'choice':
                selection = await call('inspect_selection')
                await reject('selection_covered')
                await call('select_card', {'card_id': selection['selection']['cards'][0]['id']}, 'observation_required', 'after_selection_rejection')
                await confirm_transform(call, receipt)
            elif args.scenario == 'empty':
                assert events == [], receipt
                after = await native('check_test_treasure')
                assert after['gold'] == before['gold'] and after['relics'] == before['relics'], after
            elif args.scenario == 'map_pending':
                assert receipt['screen'] == {'status': 'covered', 'view': 'map'}, receipt
                after = await native('check_test_treasure')
                assert after['delayed_done'] and not after['obtaining'], after
                await call('close_map')
            else:
                assert any(e['type'] == 'gold_changed' for e in events) and any(e['type'] == 'relic_obtained' for e in events), receipt

            current = await call('inspect_treasure')
            assert current['treasure']['chest'] == 'open' and current['treasure']['relic'] is None, current
            await reject('empty_or_collected')
            await call('proceed', error='observation_required', label='after_collected_rejection')
            await call('inspect_treasure')
            await call('proceed')
    print('PASS loot treasure audit:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
