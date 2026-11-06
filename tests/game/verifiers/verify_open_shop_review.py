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

    async def native(operation, expected_state=None, arguments=None):
        reply = await asyncio.to_thread(raw.call, operation, expected_state, arguments=arguments)
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
                    shop = value.get('shop')
                    if shop and shop['status'] == 'visible':
                        assert ('open_shop' in value['available_actions']) == bool(shop.get('open') and shop['open']['enabled']), value
                    if action is None or action in value['available_actions']: return value
                    assert time.monotonic() < deadline, value
                    await asyncio.sleep(.1)

            async def reject(label, hint):
                before = await native('get_state')
                assert 'open_shop' not in before['state']['available_actions'], before
                value = await call('open_shop', error='illegal_action', label=label)
                assert value['error']['recovery'] == 'choose_legal_action', value
                assert hint in value['error']['message'], value
                assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
                assert evidence[-1]['execution']['action_submission_observed'] is False, evidence[-1]
                assert evidence[-1]['native_error']['action_submitted'] is False, evidence[-1]
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
                await reject('no_shop', 'No shop')
                await call('end_turn', label='legal_turn_after_rejection')
                stale = await native('open_shop', 'not-current')
                assert stale['error']['code'] == 'stale_state', stale
                return
            if args.scenario == 'parasol':
                assert initial['selection']['type'] == 'deck', initial
                await reject('automatic_purchase_selection', 'inspect_selection')
                await call('select_card', {'card_id': initial['selection']['cards'][0]['id']},
                    label='selection_after_rejection')
                await call('selection_option', {'option_id': 'confirm'})
                await observe('close_shop')
                await call('close_shop')
                await observe('open_shop')
                await opened('reopen_after_automatic_purchase')
                return

            await observe('open_shop')
            if args.scenario == 'basic':
                current = await native('get_state')
                bad = await native('open_shop', current['state']['snapshot_id'], {'unexpected': True})
                assert bad['error']['code'] == 'invalid_request' and bad['error']['action_submitted'] is False, bad
                assert bad['execution']['ui_interaction_started'] is False, bad
            await call('open_shop', {'unexpected': True}, error='invalid_request', label='local_invalid_preserves_permission')
            await opened('open_inventory')
            await reject('already_open', 'already open')
            await call('close_shop', label='close_after_rejection')
            await observe('open_shop')
            await opened('reopen_after_rejection')
            if args.scenario == 'remove':
                inventory = await call('inspect_shop')
                service = next(i for i in inventory['shop']['items'] if i['kind'] == 'card_removal')
                await call('buy_item', {'item_id': service['id']})
                await reject('card_removal_selection', 'inspect_selection')
                await call('selection_option', {'option_id': 'cancel'}, label='cancel_after_rejection')
                return
            await call('close_shop')
            await observe('open_shop')
            if args.scenario == 'basic':
                await call('inspect_map')
                await reject('map_covered', 'close_map')
                await call('close_map')
                await observe('open_shop')
                await call('inspect_deck')
                await reject('deck_covered', 'close_card_view')
                await call('close_card_view')
                await observe('open_shop')
            await opened('reopen_inventory_default', preset='default')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('no_shop', 'basic', 'fake', 'remove', 'parasol'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
