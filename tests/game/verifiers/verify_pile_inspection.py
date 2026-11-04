"""Verify pile filtering, passive observations and preflight recovery through stdio."""
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
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)
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
                if error: assert response.isError and result['error']['code'] == error, result
                else: assert not response.isError, result
                return result

            before = await call('get_observation')
            if args.scenario == 'selection':
                await call('choose_rest_option', {'option_id': 'SMITH'})
                state = await call('get_observation')
                rejected = await call('inspect_pile', {'pile': 'draw'}, error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                assert 'selection' in rejected['error']['message'].lower()
                option = next(o['id'] for o in state['selection']['options'] if o['enabled'])
                await call('selection_option', {'option_id': option})
                return
            if args.scenario == 'battlefield':
                await call('set_selection_view', {'view': 'battlefield'})
            if args.scenario == 'combat':
                for pile in ('draw', 'discard', 'exhaust'):
                    for preset in ('full', 'summary'):
                        result = await call('inspect_pile', {'pile': pile, 'preset': preset, 'card_ids': ['pile:999999']})
                        assert result['status'] in ('empty', 'unavailable'), result
                        assert result['message']
                        if result['status'] == 'empty': assert result['errors'][0]['code'] == 'cards_not_in_pile'
                        else: assert 'errors' not in result
                hand = await call('inspect_hand')
                blade = next(c for c in hand['hand'] if c['name'] == 'Blade Dance')
                await call('play_card', {'card_id': blade['id']})
                hand = await call('inspect_hand')
                defend = next(c for c in hand['hand'] if c['name'] == 'Defend')
                await call('play_card', {'card_id': defend['id']})
                piles = ('discard', 'exhaust')
            else: piles = ('draw',)

            async def check_observation(details):
                before = await asyncio.to_thread(raw.call, 'get_state')
                record({'native_before': before})
                for preset, mode in [('full', 'face_full'), ('default', 'face_default'), ('summary', 'summary')]:
                    observed = await call('get_observation', {'preset': preset})
                    cards = [format_card(card, mode) for card in details['cards']]
                    if preset == 'summary': cards = apply_preset(cards, 'default')
                    assert observed['pile'] == details['pile'] and observed['cards'] == cards
                    assert ('message' in observed) == (preset != 'summary')
                    if preset != 'summary': assert observed['message'] == details['message']
                    assert 'hover_tips' not in observed
                    assert all('description' not in c and 'hover_tips' not in c for c in observed['cards'])
                for preset in ('actions_only', 'top_bar'):
                    assert not {'pile', 'cards', 'message'} & (await call('get_observation', {'preset': preset})).keys()
                after = await asyncio.to_thread(raw.call, 'get_state')
                record({'native_after': after})
                assert before['state'] == after['state'], 'Passive observation changed the native state.'

            for pile in piles:
                full = await call('inspect_pile', {'pile': pile, 'preset': 'full'})
                assert full['status'] == 'opened' and full['cards']
                await check_observation(full)
                ids = [c['id'] for c in full['cards']]
                for preset in ('full', 'default', 'summary'):
                    filtered = await call('inspect_pile', {'pile': pile, 'preset': preset,
                        'card_ids': [ids[-1], 'pile:999999', ids[-1]]})
                    assert [c['id'] for c in filtered['cards']] == [ids[-1]]
                    assert filtered['errors'] == [{'code': 'cards_not_in_pile', 'card_ids': ['pile:999999']}]
                    if preset != 'summary': assert all(t['card_ids'] == [ids[-1]] for t in filtered['hover_tips'])
                    else: assert 'message' not in filtered and 'hover_tips' not in filtered
                    empty = await call('inspect_pile', {'pile': pile, 'preset': preset, 'card_ids': []})
                    assert empty['cards'] == [] and empty['status'] == 'opened'
                assert await call('inspect_pile', {'pile': pile, 'preset': 'full', 'card_ids': None}) == full
                await check_observation(full)
                await call('inspect_pile', {'pile': pile, 'card_ids': ['pile:01']}, error='invalid_request')
                closed = await call('close_card_view')
                assert set(closed) <= {'scene', 'screen', 'available_actions', 'selection'}
                state = await call('get_observation')
                assert not {'pile', 'cards', 'message'} & state.keys()
            if args.scenario == 'draw':
                # Closing the filtered view refreshes permission for a direct combat action.
                await call('inspect_pile', {'pile': 'draw', 'card_ids': []})
                await call('close_card_view')
                await call('end_turn')
            if args.scenario == 'battlefield':
                await call('set_selection_view', {'view': 'selection'})
                choosing = (await call('get_observation'))['selection']
                await call('select_card', {'card_id': choosing['cards'][0]['id']})
                state = await call('get_observation')
                if (state.get('selection') or {}).get('status') == 'visible':
                    option = next(o['id'] for o in state['selection']['options'] if o['enabled'])
                    await call('selection_option', {'option_id': option})
    print('PASS pile inspection:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('draw', 'combat', 'selection', 'battlefield'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
