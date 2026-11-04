"""Check potion presets, original slot references and display boundaries through MCP."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.output.null_fields import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory(), timeout=110)
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(value):
        evidence.append(value)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, arguments=None):
        result = await asyncio.to_thread(raw.call, operation, arguments=arguments)
        record({'native': operation, 'arguments': arguments, 'result': result})
        assert result['ok'], result
        return result['state']

    if args.scenario == 'checks':
        result = await native('check_test_potion_readers')
        assert all(row['passed'] for row in result['results']), result
        print(f"PASS: {len(result['results'])} native potion boundary checks", flush=True)
        return
    if args.scenario == 'combat':
        for module in ('verify_potions', 'verify_mcp_potions'):
            completed = await asyncio.to_thread(subprocess.run, [sys.executable, '-m', 'tests.game.verifiers.' + module,
                '--ipc-dir', str(raw.directory), '--output', str(args.report.parent / (module + '.full.json')),
                '--report', str(args.report.parent / (module + '.report.json'))],
                cwd=ROOT, capture_output=True, text=True, timeout=100)
            assert completed.returncode == 0, completed.stdout + completed.stderr
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                value = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': value})
                assert value == json.loads(response.content[0].text)
                if error:
                    assert response.isError and value['error']['code'] == error, value
                else:
                    assert not response.isError and 'error' not in value, value
                return value

            before = await native('get_state')
            full = await call('inspect_potions')
            summary = await call('inspect_potions', {'preset': 'summary'})
            observed = await call('get_observation', {'preset': 'summary'})
            assert summary['potion_slots'] == observed['top_bar']['potion_slots']
            assert summary['scene'] == full['scene'] and summary['screen'] == full['screen']
            assert not {'slot_tip', 'hover_tips', 'notes'} & summary.keys(), summary
            assert await call('inspect_potions', {'preset': 'default'}) == apply_preset(full, 'default')
            assert (await native('get_state'))['snapshot_id'] == before['snapshot_id']
            assert await call('inspect_potions', {'slot_indices': None}) == full
            for preset in ('full', 'default', 'summary'):
                empty = await call('inspect_potions', {'preset': preset, 'slot_indices': []})
                assert empty['slot_indices'] == [] and empty['potion_slots'] == []
                assert empty.get('hover_tips') == (None if preset == 'summary' else [])
                assert 'notes' not in empty
                chosen = await call('inspect_potions', {'preset': preset, 'slot_indices': [99, 2, 1, 2, 98, 99]})
                assert chosen['slot_indices'] == [1, 2]
                assert chosen['errors'] == [{'code': 'potion_slot_indices_out_of_range', 'slot_indices': [99, 98]}]
            if args.scenario == 'combat':
                block = next(t for t in full['hover_tips'] if t['title'] == 'Block')
                assert block['slot_indices'] == [1, 2]
                one = await call('inspect_potions', {'slot_indices': [2]})
                assert next(t for t in one['hover_tips'] if t['title'] == 'Block')['slot_indices'] == [2]
                for mode in ('no_hover', 'disabled'):
                    await native('set_test_potion_display', {'mode': mode, 'index': 2})
                    try:
                        data = await call('inspect_potions', {'slot_indices': [2]})
                        assert data['potion_slots'][0]['name'] == 'Block Potion'
                        assert data['potion_slots'][0]['description'] is None
                        assert data['notes']['hover_tips_unavailable']['sources'] == ['potion_slots.2']
                        assert data['hover_tips'] == []
                        compact = await call('inspect_potions', {'preset': 'default', 'slot_indices': [2]})
                        assert 'description' not in compact['potion_slots'][0]
                        assert 'notes' not in await call('inspect_potions', {'slot_indices': [0]})
                        assert 'notes' not in await call('inspect_potions', {'slot_indices': []})
                        static = await call('inspect_potions', {'preset': 'summary'})
                        assert static['potion_slots'] == (await call('get_observation', {'preset': 'summary'}))['top_bar']['potion_slots']
                    finally:
                        await native('set_test_potion_display', {'mode': 'normal'})
                await native('set_test_potion_display', {'mode': 'hidden', 'index': 2})
                try:
                    hidden = await call('get_observation')
                    assert hidden['top_bar']['potion_slots'] is None
                    assert 'inspect_potions' not in hidden['available_actions']
                    for preset in ('full', 'summary'):
                        failure = await call('inspect_potions', {'preset': preset}, error='illegal_action')
                        assert 'hidden' in failure['error']['message'] and failure['error']['recovery'] == 'choose_legal_action'
                finally:
                    await native('set_test_potion_display', {'mode': 'normal'})
                await native('set_test_potion_display', {'mode': 'offscreen', 'index': 2})
                try:
                    assert (await call('inspect_potions'))['potion_slots'][2]['name'] == 'Block Potion'
                    assert (await call('get_observation'))['top_bar']['potion_slots'][2]['name'] == 'Block Potion'
                    failure = await call('inspect_targets', {'potion_slot': 2}, error='illegal_action')
                    assert failure['error']['message'] != 'The requested action is unavailable.'
                finally:
                    await native('set_test_potion_display', {'mode': 'normal'})
                for tool, arguments in (('inspect_deck', {}),
                        ('inspect_pile', {'pile': 'draw'}), ('inspect_pile', {'pile': 'discard'}), ('inspect_pile', {'pile': 'exhaust'})):
                    page = await call(tool, arguments)
                    detail = await call('inspect_potions', {'preset': 'summary', 'slot_indices': [2]})
                    assert detail['potion_slots'] == [{'name': 'Block Potion'}]
                    assert detail['scene'] == 'combat' and detail['screen'] == page['screen']
                    actions = (await call('get_observation'))['available_actions']
                    if 'close_card_view' in actions: await call('close_card_view')
                    if 'close_map' in actions: await call('close_map')
                await call('inspect_potions')
                used = await call('use_potion', {'potion_slot': 1})
                assert used['transition']['complete']
                vacant = await call('inspect_potions', {'slot_indices': [1]})
                assert vacant['potion_slots'] == [None] and vacant['slot_indices'] == [1] and vacant['hover_tips'] == []
                discarded = await call('discard_potion', {'potion_slot': 2})
                assert discarded['transition']['complete']
                vacant = await call('inspect_potions', {'preset': 'summary', 'slot_indices': [2]})
                assert vacant['potion_slots'] == [None]
                await call('use_potion', {'potion_slot': 0})
                selection = await call('get_observation', {'preset': 'summary'})
                assert selection.get('selection'), selection
                static = await call('inspect_potions', {'preset': 'summary'})
                assert static['potion_slots'] == [None, None, None]
                assert static['screen'] == selection['screen']
            elif args.scenario == 'map':
                page = await call('inspect_map')
                data = await call('inspect_potions', {'preset': 'summary', 'slot_indices': [2]})
                assert data['potion_slots'] == [{'name': 'Block Potion'}]
                assert data['screen'] == page['screen']
            elif args.scenario == 'merchant':
                assert type(summary['potion_slots'][0].get('usable_here')) is bool, summary
                target = await call('inspect_targets', {'potion_slot': 0})
                assert summary['potion_slots'][0]['usable_here'] == target['usable'], (summary, target)
            elif args.scenario == 'rest':
                used = await call('use_potion', {'potion_slot': 0})
                assert used['transition']['complete']
                assert (await call('inspect_potions', {'slot_indices': [0]}))['potion_slots'] == [None]
            else:
                assert summary['potion_slots'] == [None, None, None]
    print(f'PASS potion presets, linked help and display boundaries: {args.scenario}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--scenario', choices=('checks', 'combat', 'merchant', 'rest', 'empty', 'map'), default='combat')
    asyncio.run(verify(parser.parse_args()))
