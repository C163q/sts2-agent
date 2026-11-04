"""Exercise discard outcomes and native choice queues through real stdio MCP."""
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


SCENARIOS = ('choose_one', 'hand', 'pile', 'noncombat_upgrade', 'immediate', 'cancel',
             'hidden', 'multiple', 'skip', 'pending_reset', 'after_reset', 'card_choice', 'card_pile', 'hand_upgrade')


async def verify(args):
    raw = Client(ipc_directory(), timeout=75)
    await asyncio.to_thread(ensure_run, raw)
    rows = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        rows.append(row)
        args.report.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, arguments=None):
        response = await asyncio.to_thread(raw.call, operation, arguments=arguments)
        record({'native_operation': operation, 'arguments': arguments, 'response': response})
        assert response['ok'], response
        return response['state']

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert result == json.loads(response.content[0].text)
                if error:
                    assert response.isError and result['error']['code'] == error, result
                else:
                    assert not response.isError and 'error' not in result, result
                return result

            before = await call('get_observation')
            if args.scenario in {'immediate', 'after_reset'}:
                result = await call('discard_potion', {'potion_slot': 1, 'preset': 'default'})
                assert result['potion_discard'] == {'slot_index': 1, 'name': 'Block Potion', 'status': 'discarded'}, result
                assert result['transition']['stop_reason'] == 'player_ready', result
                assert [e['potion']['slot_index'] for e in result['transition']['events'] if e['type'] == 'potion_discarded'] == [1]
                await call('end_turn')
                result = await call('discard_potion', {'potion_slot': 2})
                assert result['potion_discard']['name'] == 'Fairy in a Bottle'
                assert result['potion_discard']['status'] == 'discarded'
                return
            if args.scenario in {'cancel', 'hidden'}:
                result = await call('discard_potion', {'potion_slot': 0})
                expected = 'not_discarded' if args.scenario == 'cancel' else 'unknown'
                assert result['potion_discard']['status'] == expected, result
                assert not any(e['type'] == 'potion_discarded' for e in result['transition']['events']), result
                await call('end_turn', error='observation_required')
                if args.scenario == 'hidden':
                    await native('set_test_potion_display', {'mode': 'normal'})
                after = await call('get_observation')
                assert bool(after['top_bar']['potion_slots'][0]) == (args.scenario == 'cancel'), after
                if args.scenario == 'cancel':
                    result = await call('discard_potion', {'potion_slot': 0})
                    assert result['potion_discard']['status'] == 'discarded', result
                else:
                    following = await call('end_turn')
                    assert not any(e['type'] == 'potion_discarded' for e in following['transition']['events']), following
                return

            if args.scenario == 'noncombat_upgrade':
                chosen = await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario in {'card_choice', 'card_pile', 'hand_upgrade'}:
                name = {'card_choice': 'Discovery', 'card_pile': 'Headbutt', 'hand_upgrade': 'Armaments'}[args.scenario]
                card = next(c for c in before['player']['hand'] if c['name'] == name)
                chosen = await call('play_card', {'card_id': card['id'],
                    **({'target_id': before['enemies'][0]['id']} if args.scenario == 'card_pile' else {})})
            else:
                chosen = await call('use_potion', {'potion_slot': 0})
            assert chosen['transition']['stop_reason'] == 'choice_required', chosen
            selection = (await call('inspect_selection'))['selection']
            current = await call('get_observation')
            assert 'discard_potion' in current['available_actions'], current
            if args.scenario == 'choose_one':
                targets = await call('inspect_targets', {'potion_slot': 1})
                assert not targets['usable'] and targets['discardable'], targets
            queued = await call('discard_potion', {'potion_slot': 1})
            expected_status = 'discarded' if args.scenario == 'noncombat_upgrade' else 'queued'
            assert queued['potion_discard']['status'] == expected_status, queued
            assert queued['transition']['stop_reason'] == 'choice_required', queued
            assert queued['transition']['complete'], queued
            if expected_status == 'queued':
                assert not any(e['type'] == 'potion_discarded' for e in queued['transition']['events']), queued
                # No read is needed to reject a duplicate or resolve the current selection.
                duplicate = await call('discard_potion', {'potion_slot': 1}, error='illegal_action')
                assert 'queued' in duplicate['error']['message'], duplicate
                assert duplicate['error']['recovery'] == 'choose_legal_action', duplicate
                await call('use_potion', {'potion_slot': 2}, error='illegal_action')
            if args.scenario == 'multiple':
                second = await call('discard_potion', {'potion_slot': 2})
                assert second['potion_discard']['status'] == 'queued', second
            if args.scenario == 'pending_reset':
                return
            if args.scenario == 'skip':
                resolved = await call('selection_option', {'option_id': 'skip'})
            else:
                resolved = await call('select_card', {'card_id': selection['cards'][0]['id']})
            outcomes = [resolved]
            for _ in range(3):
                assert 'potion_discard' not in resolved, resolved
                if resolved['transition']['stop_reason'] != 'choice_required':
                    break
                pending = (await call('inspect_selection'))['selection']
                assert any(o['id'] == 'confirm' and o['enabled'] for o in pending['options']), pending
                resolved = await call('selection_option', {'option_id': 'confirm'})
                outcomes.append(resolved)
            else:
                raise AssertionError('The native choice did not resolve.')
            assert resolved['transition']['stop_reason'] in {'player_ready', 'action_completed'}, resolved
            removed = [e['potion']['slot_index'] for r in outcomes for e in r['transition']['events'] if e['type'] == 'potion_discarded']
            assert removed == ([] if expected_status == 'discarded' else [1, 2] if args.scenario == 'multiple' else [1]), outcomes
            after = await call('get_observation')
            assert after['top_bar']['potion_slots'][1] is None, after
            if args.scenario == 'multiple':
                assert after['top_bar']['potion_slots'][2] is None, after
    print('PASS queued potion discard:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
