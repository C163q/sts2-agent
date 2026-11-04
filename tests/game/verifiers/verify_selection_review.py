"""Capture selection inspection rejections on the pre-fix review baseline."""
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
    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                response = await session.call_tool(name, {'preset': 'full', **(arguments or {})})
                data = response.structuredContent
                evidence.append({'tool': name, 'arguments': {'preset': 'full', **(arguments or {})},
                                 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert data == json.loads(response.content[0].text), response
                assert data.get('error', {}).get('code') == error, data
                assert response.isError == bool(error), response
                return data

            state = await call('get_observation')
            if args.scenario == 'no_selection':
                await call('inspect_selection', error='illegal_action')
                # A read-only rejection retains the existing observation.
                await call('end_turn')
                await call('get_observation')
                native = await asyncio.to_thread(raw.call, 'inspect_selection',
                                                arguments={'view_upgrades': False})
                evidence.append({'native_rejection': native})
                await call('inspect_selection', {'view_upgrades': False}, error='illegal_action')
                # This is the known review defect: the request never clicked anything.
                await call('end_turn', error='observation_required')
                await call('get_observation')
                await call('end_turn')
            elif args.scenario == 'covered':
                assert state['selection']['type'] == 'combat_pile', state
                await call('set_selection_view', {'view': 'battlefield'})
                await call('inspect_deck')
                await call('inspect_selection', error='illegal_action')
                await call('close_card_view')
                await call('set_selection_view', {'view': 'selection'})
                await call('inspect_selection')
            elif args.scenario == 'hand_upgrade':
                card = next(c for c in state['player']['hand'] if c['name'] == 'Armaments')
                await call('play_card', {'card_id': card['id']})
                details = await call('inspect_selection')
                await call('inspect_selection', {'view_upgrades': True, 'card_ids': []})
                target = details['selection']['cards'][0]['id']
                await call('select_card', {'card_id': target})
                await call('inspect_selection')
                await call('set_selection_view', {'view': 'battlefield'})
                native = await asyncio.to_thread(raw.call, 'inspect_selection')
                evidence.append({'native_rejection': native})
                await call('inspect_selection', error='illegal_action')
                await call('set_selection_view', {'view': 'selection'})
                await call('inspect_selection')
                await call('selection_option', {'option_id': 'confirm'})
            else:
                raise AssertionError(args.scenario)
    args.report.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({'scenario': args.scenario, 'records': len(evidence)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
