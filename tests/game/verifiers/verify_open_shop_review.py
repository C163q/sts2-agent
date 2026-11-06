"""Audit native shop opening, rejection recovery and compact action results."""
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
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, expected_state=None):
        reply = await asyncio.to_thread(raw.call, operation, expected_state)
        record({'native_operation': operation, 'result': reply})
        return reply

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
                    original = json.loads(added.pop().read_text())
                    row.update(native_error=original.get('error'), execution=original.get('execution'))
                record(row)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def observe(action=None):
                deadline = time.monotonic() + 15
                while True:
                    value = await call('get_observation', label='observe_' + (action or 'screen'))
                    if action is None or action in value['available_actions']: return value
                    assert time.monotonic() < deadline, value
                    await asyncio.sleep(.1)

            async def reject(label):
                before = await native('get_state')
                assert 'open_shop' not in before['state']['available_actions'], before
                value = await call('open_shop', error='illegal_action', label=label)
                assert value['error'] == {'code': 'illegal_action',
                    'message': 'The requested action is unavailable.', 'recovery': 'get_observation'}, value
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                assert 'action_submitted' not in evidence[-1]['native_error'], evidence[-1]
                return value

            async def opened(label, preset='full'):
                value = await call('open_shop', {'preset': preset}, label=label)
                assert value['scene'] == 'shop' and value['screen'] == {'status': 'visible'}, value
                assert value['transition'] == {'stop_reason': 'action_completed', 'complete': True, 'events': []}, value
                assert 'inspect_shop' in value['available_actions'] and 'close_shop' in value['available_actions'], value
                assert 'open_shop' not in value['available_actions'], value
                assert not {'shop', 'player', 'top_bar', 'map'} & value.keys(), value
                assert evidence[-1]['image_count'] == 0, evidence[-1]
                current = await call('get_observation', label=label + '_immediate_observation')
                assert current['shop']['view'] == 'inventory' and current['shop']['items'], current
                return value

            await call('open_shop', error='observation_required', label='no_initial_permission')
            initial = await observe()
            if args.scenario == 'no_shop':
                await reject('no_shop')
                await call('end_turn', error='observation_required', label='legal_turn_blocked_after_rejection')
                await call('inspect_hand', label='read_restores_permission')
                await call('end_turn', label='turn_after_read')
                stale = await native('open_shop', 'not-current')
                assert stale['error']['code'] == 'stale_state', stale
                return
            if args.scenario == 'parasol':
                assert initial['selection']['type'] == 'deck', initial
                await reject('automatic_purchase_selection')
                await call('select_card', {'card_id': initial['selection']['cards'][0]['id']},
                    error='observation_required', label='selection_blocked_after_rejection')
                selected = await call('inspect_selection')
                await call('select_card', {'card_id': selected['selection']['cards'][0]['id']})
                await call('selection_option', {'option_id': 'confirm'})
                await observe('close_shop')
                await call('close_shop')
                await observe('open_shop')
                await opened('reopen_after_automatic_purchase')
                return

            await observe('open_shop')
            await call('open_shop', {'unexpected': True}, error='invalid_request', label='local_invalid_preserves_permission')
            await opened('open_inventory')
            await reject('already_open')
            await call('close_shop', error='observation_required', label='close_blocked_after_rejection')
            await call('inspect_shop', label='details_restore_permission')
            if args.scenario == 'remove':
                inventory = await call('inspect_shop')
                service = next(i for i in inventory['shop']['items'] if i['kind'] == 'card_removal')
                await call('buy_item', {'item_id': service['id']})
                await reject('card_removal_selection')
                await call('selection_option', {'option_id': 'cancel'}, error='observation_required', label='cancel_blocked_after_rejection')
                await call('inspect_selection')
                await call('selection_option', {'option_id': 'cancel'})
                return
            await call('close_shop')
            await observe('open_shop')
            if args.scenario == 'basic':
                await call('inspect_map')
                await reject('map_covered')
                await call('open_shop', error='observation_required', label='map_rejection_clears_permission')
                await call('close_map')
                await observe('open_shop')
                await call('inspect_deck')
                await reject('deck_covered')
                await call('open_shop', error='observation_required', label='deck_rejection_clears_permission')
                await call('close_card_view')
                await observe('open_shop')
            await opened('reopen_inventory_default', preset='default')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('no_shop', 'basic', 'fake', 'remove', 'parasol'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
