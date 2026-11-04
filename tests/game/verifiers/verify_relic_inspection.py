"""Verify shared relic icon states, original positions and actionable read failures."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory(), timeout=100)
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(value):
        evidence.append(value)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, arguments=None):
        value = await asyncio.to_thread(raw.call, operation, arguments=arguments)
        record({'native': operation, 'arguments': arguments, 'result': value})
        assert value['ok'], value
        return value['state']

    if args.scenario == 'combat':
        checks = await native('check_test_display_readers')
        assert all(row['passed'] for row in checks['results']), checks
    for module in ('verify_relics', 'verify_mcp_relics'):
        completed = await asyncio.to_thread(subprocess.run, [sys.executable, '-m', 'tests.game.verifiers.' + module,
            '--ipc-dir', str(raw.directory), '--output', str(args.report.parent/(module+'.full.json')),
            '--report', str(args.report.parent/(module+'.report.json'))], cwd=ROOT, capture_output=True, text=True, timeout=100)
        assert completed.returncode == 0, completed.stdout + completed.stderr
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                options = {'preset': 'full', **(arguments or {})}
                reply = await session.call_tool(tool, options)
                data = reply.structuredContent
                record({'tool': tool, 'arguments': options, 'result': data})
                assert data == json.loads(reply.content[0].text), reply
                if error: assert reply.isError and data['error']['code'] == error, data
                else: assert not reply.isError and 'error' not in data, data
                return data

            before = await native('get_state')
            full = await call('inspect_relics')
            count = len(full['relics']); assert count > 0
            index = count - 1
            for preset in ('full', 'default', 'summary'):
                all_data = await call('inspect_relics', {'preset': preset})
                assert await call('inspect_relics', {'preset': preset, 'relic_indices': None}) == all_data
                assert 'relic_indices' not in all_data
                filtered = await call('inspect_relics', {'preset': preset, 'relic_indices': [99, index, 98, index, 99]})
                assert filtered['relic_indices'] == [index]
                assert filtered['relics'] == [all_data['relics'][index]]
                assert filtered['errors'] == [{'code':'relic_indices_out_of_range', 'relic_indices':[99, 98]}]
                for tip in filtered.get('hover_tips', []): assert tip['relic_indices'] == [index], tip
                empty = await call('inspect_relics', {'preset': preset, 'relic_indices': []})
                assert empty['relic_indices'] == [] and empty['relics'] == []
                assert empty.get('hover_tips') == (None if preset == 'summary' else [])
                assert 'notes' not in empty
            assert before['snapshot_id'] == (await native('get_state'))['snapshot_id']
            if args.scenario == 'combat':
                for mode, gray, pulse in [('grayed', True, False), ('pulsing', False, True), ('both', True, True),
                                         ('unknown_tint', None, False), ('no_shader', False, None)]:
                    await native('set_test_relic_display', {'mode':mode, 'index':index})
                    try:
                        native_before = await native('get_state')
                        data = await call('inspect_relics', {'relic_indices':[index]})
                        item = data['relics'][0]
                        assert item['grayed_out'] is gray and item['pulsing'] is pulse, (mode, item)
                        observed = await call('get_observation')
                        assert observed['top_bar']['relics'][index]['grayed_out'] is gray
                        assert observed['top_bar']['relics'][index]['pulsing'] is pulse
                        for preset in ('default', 'summary'):
                            compact = (await call('inspect_relics', {'preset':preset,'relic_indices':[index]}))['relics'][0]
                            for field, value in [('grayed_out',gray), ('pulsing',pulse)]:
                                if value is True: assert compact[field] is True
                                else: assert field not in compact
                        observed = await call('get_observation', {'preset':'default'})
                        for field, value in [('grayed_out',gray), ('pulsing',pulse)]:
                            if value is True: assert observed['top_bar']['relics'][index][field] is True
                            else: assert field not in observed['top_bar']['relics'][index]
                        summary = await call('get_observation', {'preset':'summary'})
                        assert 'relics' not in summary['top_bar']
                        assert native_before == await native('get_state'), 'Inspection mutated state.'
                    finally: await native('set_test_relic_display', {'mode':'normal'})
                for mode, fragment in [('hidden_inventory','inventory'),('hidden_top_bar','top bar')]:
                    await call('get_observation')
                    await native('set_test_relic_display', {'mode':mode})
                    try:
                        for preset in ('full', 'summary'):
                            rejected = await call('inspect_relics', {'preset':preset}, error='illegal_action')
                            assert fragment in rejected['error']['message'].lower(), rejected
                            assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                    finally: await native('set_test_relic_display', {'mode':'normal'})
                # Restored native UI equals the pre-rejection snapshot; no intervening observation.
                receipt = await call('end_turn')
                assert receipt['transition']['complete'], receipt
                for tool, options in [('inspect_deck',{}), ('inspect_pile',{'pile':'draw'}),
                                      ('inspect_pile',{'pile':'discard'}), ('inspect_pile',{'pile':'exhaust'})]:
                    await call(tool, options)
                    detail = await call('inspect_relics', {'preset':'summary','relic_indices':[index]})
                    assert detail['relic_indices'] == [index]
                    state = await call('get_observation')
                    assert detail['screen'] == state['screen'] and detail['scene'] == state['scene']
                    if 'close_card_view' in state['available_actions']: await call('close_card_view')
                    if 'close_map' in state['available_actions']: await call('close_map')
                await call('inspect_map')
                detail = await call('inspect_relics', {'preset':'summary','relic_indices':[index]})
                assert detail['screen']['view'] == 'map'
    print('PASS relic icon states, original mappings and read errors:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--scenario', choices=('combat','context'), default='combat')
    asyncio.run(verify(parser.parse_args()))
