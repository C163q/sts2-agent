"""Verify card browser preflight recovery and successful minimal closes."""
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


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full'} if arguments is None else arguments
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                evidence.append({'tool': tool, 'arguments': arguments, 'result': result})
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert result == json.loads(response.content[0].text)
                if error: assert response.isError and result['error']['code'] == error, result
                else: assert not response.isError, result
                return result

            await call('get_observation')
            if args.scenario == 'ancient':
                for _ in range(3):
                    await call('inspect_deck')
                    closed = await call('close_card_view')
                    assert 'choose_ancient_option' in closed['available_actions'], closed
                    current = await call('inspect_ancient')
                    assert current['ancient']['status'] == 'visible', current
                for preset in ('full', 'default'):
                    await call('inspect_deck')
                    partial = await asyncio.to_thread(raw.call, 'set_test_presentation', arguments={'mode': 'partial'})
                    assert partial['ok'], partial
                    try:
                        closed = await call('close_card_view', {'preset': preset})
                        assert closed['notes']['presentation']['sources'] == ['ancient'], closed
                        assert 'choose_ancient_option' not in closed['available_actions'], closed
                        for compact in ('actions_only', 'top_bar'):
                            viewed = await call('get_observation', {'preset': compact})
                            assert viewed['notes']['presentation']['sources'] == ['ancient'], viewed
                    finally:
                        restored = await asyncio.to_thread(raw.call, 'set_test_presentation', arguments={'mode': 'normal'})
                        assert restored['ok'], restored
                    current = await call('inspect_ancient')
                option = next(o for o in current['ancient']['options'] if o['enabled'])
                await call('choose_ancient_option', {'option_id': option['id']})
                return
            if args.scenario == 'selection':
                await call('choose_rest_option', {'option_id': 'SMITH'})
                choosing = await call('get_observation')
                rejected = await call('close_card_view', error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                assert 'selection' in rejected['error']['message'].lower(), rejected
                option = next(o['id'] for o in choosing['selection']['options'] if o['enabled'])
                await call('selection_option', {'option_id': option})
                return
            if args.scenario == 'battlefield':
                await call('set_selection_view', {'view': 'battlefield'})
                await call('inspect_pile', {'pile': 'draw'})
                closed = await call('close_card_view')
                assert closed['selection']['status'] == 'battlefield'
                await call('set_selection_view', {'view': 'selection'})
                selection = (await call('get_observation'))['selection']
                await call('select_card', {'card_id': selection['cards'][0]['id']})
                current = await call('get_observation')
                if (current.get('selection') or {}).get('status') == 'visible':
                    option = next(o['id'] for o in current['selection']['options'] if o['enabled'])
                    await call('selection_option', {'option_id': option})
                return
            rejected = await call('close_card_view', error='illegal_action')
            assert rejected['error']['recovery'] == 'choose_legal_action', rejected
            assert 'open' in rejected['error']['message'].lower(), rejected
            await call('end_turn')
            for preset in ('full', 'default'):
                await call('inspect_deck')
                closed = await call('close_card_view', {'preset': preset})
                assert set(closed) == {'scene', 'screen', 'available_actions'}
                # The rejection must retain the successful close's permission.
                rejected = await call('close_card_view', error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                await call('end_turn')
            await call('inspect_map')
            rejected = await call('close_card_view', error='illegal_action')
            assert rejected['error']['recovery'] == 'choose_legal_action'
            assert (await call('get_observation'))['screen']['view'] == 'map'
            await call('inspect_deck')
            closed = await call('close_card_view')
            assert closed['screen']['view'] == 'map'
            assert closed == await call('get_observation', {'preset': 'actions_only'})
    print('PASS card view close:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('combat', 'selection', 'battlefield', 'ancient'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
