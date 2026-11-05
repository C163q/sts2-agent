"""Verify claim outcomes, explicit preflight recovery and scroll failure boundaries."""
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

SCENARIOS = ('basic', 'full', 'linked', 'nested', 'returned', 'covered', 'no_rewards', 'transform', 'deck_covered', 'scroll_success', 'scroll_failure')


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(item):
        evidence.append(item)
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
                item = {'tool': tool, 'arguments': arguments, 'result': result, 'label': label,
                    'image_count': sum(part.type == 'image' for part in response.content)}
                added = set((raw.directory / 'responses').glob('*.json')) - old
                if added:
                    assert len(added) == 1, added
                    native = json.loads(added.pop().read_text())
                    item.update(native_error=native.get('error'), execution=native.get('execution'))
                record(item)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def native(operation, arguments=None, expected=None, error=None, label=None):
                result = await asyncio.to_thread(raw.call, operation, expected, arguments=arguments)
                record({'native_operation': operation, 'arguments': arguments, 'result': result, 'label': label})
                assert result.get('ok') == (error is None), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def ready():
                deadline = time.monotonic() + 5
                while True:
                    observed = await call('get_observation', {'preset': 'actions_only'}, label='wait_rewards')
                    if 'claim_reward' in observed['available_actions'] or 'proceed' in observed['available_actions']:
                        return observed
                    assert time.monotonic() < deadline, observed
                    await asyncio.sleep(.1)

            async def claim(row, status='claimed', reason='action_completed', **kwargs):
                receipt = await call('claim_reward', {'reward_id': row['id'], **kwargs})
                assert receipt['reward_result'] == {'reward_id': row['id'], 'status': status}, receipt
                assert receipt['transition']['stop_reason'] == reason and receipt['transition']['complete'], receipt
                assert not {'rewards', 'player', 'top_bar', 'enemies'} & receipt.keys(), receipt
                return receipt

            await call('claim_reward', {'reward_id': 0}, 'observation_required', 'no_permission')
            if args.scenario == 'no_rewards':
                await call('get_observation')
                rejected = await call('claim_reward', {'reward_id': 0}, 'illegal_action', 'wrong_scene')
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                assert 'No reward list' in rejected['error']['message'], rejected
                await call('end_turn', label='direct_after_rejection')
                return

            details = await call('inspect_rewards')
            rows = details['rewards']['items']
            by_type = lambda kind: next(row for row in rows if row['type'] == kind)
            proceeded = False
            if args.scenario == 'covered':
                graph = await call('inspect_map')
                rejected = await call('claim_reward', {'reward_id': rows[0]['id']}, 'illegal_action', 'map_covered')
                assert 'close_map' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]}, label='direct_map_after_rejection')
                return
            elif args.scenario == 'deck_covered':
                await call('inspect_deck')
                rejected = await call('claim_reward', {'reward_id': rows[0]['id']}, 'illegal_action', 'deck_covered')
                assert 'close_card_view' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('claim_reward', {'reward_id': rows[0]['id']}, 'illegal_action', 'retained_on_deck')
                await call('close_card_view')
                await ready()
            elif args.scenario == 'basic':
                current = (await native('get_state'))['state']
                rejected = await call('claim_reward', {'reward_id': 2147483647}, 'illegal_action', 'unknown_id')
                assert 'current ID' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                invalid = await native('claim_reward', {'reward_id': True}, current['snapshot_id'], 'invalid_request', 'native_invalid')
                assert invalid['error'].get('action_submitted') is False and invalid['execution']['ui_interaction_started'] is False, invalid
                await native('claim_reward', {'reward_id': 2147483647}, 'expired-observation', 'stale_state', 'stale_before_id_lookup')
                await call('claim_reward', {'reward_id': True}, 'invalid_request', 'local_invalid')
                gold = by_type('gold')
                receipt = await claim(gold, preset='default')
                assert any(event['type'] == 'gold_changed' for event in receipt['transition']['events']), receipt
                rejected = await call('claim_reward', {'reward_id': gold['id']}, 'illegal_action', 'already_claimed')
                assert 'no longer available' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                receipt = await claim(by_type('potion'))
                assert any(e['type'] == 'potion_obtained' for e in receipt['transition']['events']), receipt
                receipt = await claim(by_type('special_card'))
                assert any(e['type'] == 'card_added' and e['pile'] == 'deck' for e in receipt['transition']['events']), receipt
                receipt = await claim(by_type('relic'))
                assert any(e['type'] == 'relic_obtained' for e in receipt['transition']['events']), receipt
                card = by_type('card')
                await claim(card, status='pending', reason='choice_required')
                rejected = await call('claim_reward', {'reward_id': card['id']}, 'illegal_action', 'selection_covered')
                assert 'inspect_selection' in rejected['error']['message'] and rejected['error']['recovery'] == 'choose_legal_action', rejected
                await call('selection_option', {'option_id': 'skip'}, label='direct_skip_after_rejection')
                await ready()
                await claim(card, status='pending', reason='choice_required')
                selection = await call('inspect_selection')
                await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
            elif args.scenario == 'full':
                potion = by_type('potion')
                receipt = await claim(potion, status='not_claimed')
                assert not any(e['type'] == 'potion_obtained' for e in receipt['transition']['events']), receipt
                await call('discard_potion', {'potion_slot': 0})
                await claim(potion)
            elif args.scenario == 'linked':
                await claim(by_type('gold'))
                assert (await call('inspect_rewards'))['rewards']['items'] == []
                await call('claim_reward', {'reward_id': by_type('potion')['id']}, 'illegal_action', 'linked_removed')
                await call('proceed', label='direct_proceed_after_rejection')
                proceeded = True
            elif args.scenario == 'nested':
                await claim(by_type('relic'), status='pending')
                nested = await call('inspect_rewards')
                assert len(nested['rewards']['items']) == 3, nested
                await call('proceed')
            elif args.scenario == 'returned':
                receipt = await claim(by_type('special_card'))
                assert any(e['type'] == 'card_added' and e['pile'] == 'deck' for e in receipt['transition']['events']), receipt
            elif args.scenario in {'scroll_success', 'scroll_failure'}:
                card = by_type('card')
                if args.scenario == 'scroll_failure':
                    armed = await native('arm_test_reward_scroll_failure')
                    assert card['id'] in armed['state']['offscreen_reward_ids'], armed
                    try:
                        rejected = await call('claim_reward', {'reward_id': card['id']}, 'illegal_action', 'after_scroll')
                        assert 'revealed' in rejected['error']['message'] and rejected['error']['recovery'] == 'get_observation', rejected
                        facts = evidence[-1]
                        assert facts['execution']['ui_interaction_started'] is True, facts
                        assert 'action_submitted' not in facts['native_error'], facts
                        await call('claim_reward', {'reward_id': card['id']}, 'observation_required', 'lost_after_scroll')
                    finally:
                        await native('clear_test_reward_scroll_failure')
                    await call('inspect_rewards')
                await claim(card, status='pending', reason='choice_required')
                selection = await call('inspect_selection')
                await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
            elif args.scenario == 'transform':
                receipt = await claim(by_type('relic'), status='pending', reason='choice_required')
                from tests.game.support.verification_actions import confirm_transform
                await confirm_transform(call, receipt)

            if not proceeded:
                await call('proceed')
            graph = await call('inspect_map')
            await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]})
    print('PASS claim reward audit:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
