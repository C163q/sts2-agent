"""Record claim outcomes and the current rejection/recovery behavior."""
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

SCENARIOS = ('basic', 'full', 'linked', 'nested', 'returned', 'covered', 'no_rewards', 'transform')


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
                assert rejected['error']['recovery'] == 'get_observation', rejected
                await call('end_turn', error='observation_required', label='after_rejection')
                await call('get_observation')
                await call('end_turn')
                return

            details = await call('inspect_rewards')
            rows = details['rewards']['items']
            by_type = lambda kind: next(row for row in rows if row['type'] == kind)
            if args.scenario == 'covered':
                graph = await call('inspect_map')
                await call('claim_reward', {'reward_id': rows[0]['id']}, 'illegal_action', 'map_covered')
                await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]}, 'observation_required', 'after_rejection')
                await call('close_map')
                await ready()
                await call('inspect_deck')
                await call('claim_reward', {'reward_id': rows[0]['id']}, 'illegal_action', 'deck_covered')
                await call('close_card_view')
                await ready()
            elif args.scenario == 'basic':
                await call('claim_reward', {'reward_id': True}, 'invalid_request', 'local_invalid')
                gold = by_type('gold')
                receipt = await claim(gold, preset='default')
                assert any(event['type'] == 'gold_changed' for event in receipt['transition']['events']), receipt
                await call('claim_reward', {'reward_id': gold['id']}, 'illegal_action', 'already_claimed')
                await call('claim_reward', {'reward_id': by_type('potion')['id']}, 'observation_required', 'after_rejection')
                await call('inspect_rewards')
                receipt = await claim(by_type('potion'))
                assert any(e['type'] == 'potion_obtained' for e in receipt['transition']['events']), receipt
                receipt = await claim(by_type('special_card'))
                assert any(e['type'] == 'card_added' and e['pile'] == 'deck' for e in receipt['transition']['events']), receipt
                receipt = await claim(by_type('relic'))
                assert any(e['type'] == 'relic_obtained' for e in receipt['transition']['events']), receipt
                card = by_type('card')
                await claim(card, status='pending', reason='choice_required')
                await call('claim_reward', {'reward_id': card['id']}, 'illegal_action', 'selection_covered')
                await call('selection_option', {'option_id': 'skip'}, 'observation_required', 'after_selection_rejection')
                await call('inspect_selection')
                await call('selection_option', {'option_id': 'skip'})
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
                await call('proceed', error='observation_required', label='after_rejection')
                await call('inspect_rewards')
            elif args.scenario == 'nested':
                await claim(by_type('relic'), status='pending')
                nested = await call('inspect_rewards')
                assert len(nested['rewards']['items']) == 3, nested
                await call('proceed')
            elif args.scenario == 'returned':
                receipt = await claim(by_type('special_card'))
                assert any(e['type'] == 'card_added' and e['pile'] == 'deck' for e in receipt['transition']['events']), receipt
            elif args.scenario == 'transform':
                receipt = await claim(by_type('relic'), status='pending', reason='choice_required')
                from tests.game.support.verification_actions import confirm_transform
                await confirm_transform(call, receipt)

            await call('proceed')
            graph = await call('inspect_map')
            await call('travel_to_node', {'node_id': graph['selectable_nodes'][0]})
    print('PASS claim reward audit:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
