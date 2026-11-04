"""Verify deck filtering, passive faces, minimal closes and preflight recovery."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.output.card_format import format_card
from sts2_mcp.output.null_fields import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(value):
        evidence.append(value)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full'} if arguments is None else arguments
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert result == json.loads(response.content[0].text)
                if error:
                    assert response.isError and result['error']['code'] == error, result
                else:
                    assert not response.isError, result
                return result

            before = await call('get_observation')
            if args.scenario == 'selection':
                await call('choose_rest_option', {'option_id': 'SMITH'})
                state = await call('get_observation')
                rejection = await call('inspect_deck', error='illegal_action')
                assert rejection['error']['recovery'] == 'choose_legal_action', rejection
                assert 'selection' in rejection['error']['message'].lower(), rejection
                option = next(o['id'] for o in state['selection']['options'] if o['enabled'])
                await call('selection_option', {'option_id': option})
                return
            if args.scenario == 'shop':
                await call('open_shop')
                before = await call('get_observation')
            if args.scenario == 'epilogue':
                await call('proceed')
                before = await call('get_observation')

            full = await call('inspect_deck', {'preset': 'full', 'view_upgrades': False, 'sort_by': 'obtained'})
            assert full['scene'] == before['scene'] and full['deck']

            async def check_observation(details):
                stable = await asyncio.to_thread(raw.call, 'get_state')
                record({'native_before_read': stable})
                for preset, mode in [('full', 'face_full'), ('default', 'face_default'), ('summary', 'summary')]:
                    observation = await call('get_observation', {'preset': preset})
                    expected = [format_card(card, mode) for card in details['deck']]
                    if preset == 'summary': expected = apply_preset(expected, 'default')
                    assert observation.get('deck') == expected, (observation, expected)
                    assert observation['view_upgrades'] == details['view_upgrades']
                    assert observation['sort'] == details['sort']
                    assert 'hover_tips' not in observation
                    assert all('description' not in card and 'hover_tips' not in card for card in observation['deck'])
                for preset in ('actions_only', 'top_bar'):
                    assert 'deck' not in await call('get_observation', {'preset': preset})
                after = await asyncio.to_thread(raw.call, 'get_state')
                record({'native_after_read': after})
                assert stable['state'] == after['state'], 'Passive reads changed the page or gameplay.'

            await check_observation(full)
            ids = [card['id'] for card in full['deck']]
            for preset in ('full', 'default', 'summary'):
                result = await call('inspect_deck', {'preset': preset, 'card_ids': [ids[-1], 'deck:999999', ids[-1], ids[0]]})
                assert [c['id'] for c in result['deck']] == [ids[0], ids[-1]], result
                assert result['errors'] == [{'code': 'cards_not_in_deck', 'card_ids': ['deck:999999']}]
                if preset != 'summary':
                    assert all(set(t['card_ids']) <= {ids[0], ids[-1]} for t in result['hover_tips'])
                empty = await call('inspect_deck', {'preset': preset, 'card_ids': []})
                assert empty['deck'] == [] and empty['view_upgrades'] is False
                if preset != 'summary': assert empty['hover_tips'] == []
            assert (await call('inspect_deck', {'preset': 'full', 'card_ids': None})) == full
            upgraded = await call('inspect_deck', {'preset': 'full', 'view_upgrades': True,
                'sort_by': 'cost', 'descending': True})
            assert upgraded['sort'] == {'by': 'cost', 'descending': True}
            assert upgraded['view_upgrades'] and {c['id'] for c in upgraded['deck']} == set(ids)
            await check_observation(upgraded)
            assert await call('inspect_deck') == upgraded
            await call('inspect_deck', {'card_ids': ['deck:01']}, error='invalid_request')

            closed = await call('close_card_view')
            assert set(closed) <= {'scene', 'screen', 'available_actions', 'selection'}
            assert closed['scene'] == full['scene']
            current = await call('get_observation')
            assert 'deck' not in current and 'view_upgrades' not in current and 'sort' not in current
            if args.scenario == 'combat':
                # A successful close is enough permission; no observation is needed for the action.
                await call('inspect_deck', {'preset': 'summary', 'card_ids': []})
                await call('close_card_view')
                await call('end_turn')
            if args.scenario in ('combat', 'context'):
                await call('inspect_map')
                await call('inspect_deck')
                observed = await call('get_observation')
                assert observed['deck'] and observed['screen']['view'] == 'deck'
                closed = await call('close_card_view')
                actions = await call('get_observation', {'preset': 'actions_only'})
                assert closed == actions and closed['screen']['view'] == 'map'
                assert 'deck' not in await call('get_observation')
    print('PASS deck inspection:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('combat', 'context', 'selection', 'shop', 'epilogue'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
