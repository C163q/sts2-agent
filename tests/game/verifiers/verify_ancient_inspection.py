"""Verify ancient UI boundaries through the real MCP stdio transport."""
from scripts._bootstrap import ROOT
import argparse
import base64
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
    report = args.report.resolve()
    if report.exists(): raise FileExistsError(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory()); evidence = []
    created = await asyncio.to_thread(ensure_run, raw)
    assert created['ok'], created
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()

        async def call(name, arguments=None, *, error=None, label=None):
            supplied = {'preset': 'full', **(arguments or {})}
            previous = set((raw.directory / 'responses').glob('*.json'))
            reply = await session.call_tool(name, supplied); data = reply.structuredContent
            files = set((raw.directory / 'responses').glob('*.json')) - previous
            evidence.append({'tool': name, 'arguments': supplied, 'label': label, 'result': data,
                'native_files': [str(p.relative_to(ROOT)) for p in sorted(files)]})
            report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
            assert data == json.loads(reply.content[0].text), reply
            assert reply.isError == bool(error) and data.get('error', {}).get('code') == error, data
            return data

        async def native(operation, arguments=None):
            reply = await asyncio.to_thread(raw.call, operation, arguments=arguments,
                response_options={'include_divination_image': False})
            evidence.append({'native_operation': operation, 'arguments': arguments, 'result': reply})
            report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
            assert reply['ok'], reply
            return reply['state']

        async def choices(label='ready'):
            deadline = time.monotonic() + 15
            while True:
                value = await call('inspect_ancient', label=label)
                if any(o['enabled'] for o in value['ancient']['options']): return value
                button = value['ancient']['continue']
                if button and button['enabled']:
                    await call('advance_dialogue')
                else: await asyncio.sleep(.15)
                assert time.monotonic() < deadline, value

        async def rejection(label, hint, recovery='choose_legal_action'):
            value = await call('inspect_ancient', error='illegal_action', label=label)
            assert hint in value['error']['message'], value
            assert value['error']['recovery'] == recovery, value
            return value

        if args.scenario == 'no_ancient':
            await rejection('cold_wrong_room', 'ancient', 'get_observation')
            await call('end_turn', error='observation_required')
            await call('get_observation')
            await rejection('wrong_room', 'ancient')
            await call('end_turn', label='continue_after_rejected_read')
            return

        initial = await call('inspect_ancient', label='arrival')
        if args.scenario == 'dialogue':
            assert len(initial['ancient']['dialogue']) == 1 and initial['ancient']['continue'], initial
            assert initial['ancient']['options'] == [], initial
        value = await choices()
        original = value['ancient']; ids = [o['id'] for o in original['options']]
        assert value['scene'] == 'ancient' and value['screen'] == {'status': 'visible'}, value
        assert all(type(o['lethal_warning']) is bool for o in original['options']), value
        if args.scenario == 'display':
            first = next(o for o in original['options'] if o['hover_tips'])
            for mode in ('offscreen', 'no_hover', 'disabled', 'controller_only', 'hidden', 'transparent', 'clipped'):
                try:
                    await native('set_test_ancient_display', {'mode': mode})
                    current = await call('inspect_ancient', label=mode + '_full')
                    rows = {o['id']: o for o in current['ancient']['options']}
                    if mode in {'hidden', 'transparent', 'clipped'}:
                        assert first['id'] not in rows, current
                    else:
                        assert first['id'] in rows and rows[first['id']]['description'] == first['description'], current
                        if mode in {'no_hover', 'disabled'}:
                            assert rows[first['id']]['hover_tips'] == [] and not rows[first['id']]['enabled'], current
                            assert current['notes']['hover_tips_unavailable']['sources'] == ['ancient.options.' + str(first['id'])], current
                            filtered = await call('inspect_ancient', {'option_ids': [identifier for identifier in ids if identifier != first['id']]}, label=mode + '_filtered')
                            assert 'hover_tips_unavailable' not in filtered.get('notes', {}), filtered
                        else:
                            assert rows[first['id']]['hover_tips'], current
                            if mode == 'offscreen': assert rows[first['id']]['enabled'] is False, current
                    compact = await call('inspect_ancient', {'preset': 'summary'}, label=mode + '_summary')
                    assert all('hover_tips' not in row for row in compact['ancient']['options']), compact
                    assert 'hover_tips_unavailable' not in compact.get('notes', {}), compact
                    observed = await call('get_observation', label=mode + '_observation')
                    assert [o['id'] for o in observed['ancient']['options']] == list(rows), observed
                finally: await native('set_test_ancient_display', {'mode': 'normal'})
            guards = await native('check_test_dispatch')
            assert guards['test_mode_off'] == guards['suite_and_scenarios_off'] and guards['test_mode_off'] >= 85, guards
            return
        if args.scenario in {'safe', 'lethal'}:
            expected = args.scenario == 'lethal'
            truth = await native('check_test_ancient')
            assert truth['max_hp'] == (9 if expected else 80), truth
            picture = await asyncio.to_thread(raw.call, 'capture_screenshot')
            assert picture['ok'], picture
            report.with_suffix('.png').write_bytes(base64.b64decode(picture['state']['png_base64']))
            cape = next(o for o in original['options'] if o['title'] == 'Distinguished Cape')
            assert cape['lethal_warning'] is expected, value
            default = await call('inspect_ancient', {'preset': 'default'}, label='cape_default')
            assert next(o for o in default['ancient']['options'] if o['id'] == cape['id'])['lethal_warning'] is expected
            for preset in ('full', 'default', 'summary'):
                observed = await call('get_observation', {'preset': preset}, label='cape_observation_' + preset)
                row = next(o for o in observed['ancient']['options'] if o['id'] == cape['id'])
                assert row.get('lethal_warning') is True if expected else 'lethal_warning' not in row, observed
            compact = await call('inspect_ancient', {'preset': 'summary', 'option_ids': [cape['id']]}, label='cape_summary')
            assert compact['ancient']['options'][0].get('lethal_warning') is True if expected else 'lethal_warning' not in compact['ancient']['options'][0], compact
            return

        summary = await call('inspect_ancient', {'preset': 'summary'}, label='summary')
        assert all('hover_tips' not in o and o['description'] for o in summary['ancient']['options']), summary
        if args.scenario == 'basic':
            before = await native('check_test_ancient')
            for preset in ('full', 'default', 'summary'):
                observed = await call('get_observation', {'preset': preset}, label='observation_' + preset)
                assert all('hover_tips' not in o and 'lethal_warning' not in o for o in observed['ancient']['options']), observed
            for requested, expected in ((None, ids), ([], []), ([ids[-1], ids[0], ids[-1]], [ids[0], ids[-1]])):
                filtered = await call('inspect_ancient', {'option_ids': requested}, label='filtered_' + str(requested))
                assert [o['id'] for o in filtered['ancient']['options']] == expected, filtered
            missing = await call('inspect_ancient', {'option_ids': [2147483646, ids[0], 2147483647, 2147483646]}, label='missing')
            assert missing['errors'] == [{'code': 'option_ids_not_found', 'option_ids': [2147483646, 2147483647]}], missing
            await call('inspect_ancient', {'option_ids': [True]}, error='invalid_request', label='local_invalid')
            assert before == await native('check_test_ancient')
            for inspect, close in (('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')):
                await call(inspect)
                await rejection(inspect + '_covered', close)
                await call(close, label='close_after_rejected_read')
            value = await choices('returned_ready')
        if args.scenario == 'touch':
            first = original['options'][0]
            assert first['description'] == 'Replace Burning Blood with Black Blood.', first
            assert {tip['title'] for tip in first['hover_tips']} == {'Burning Blood', 'Black Blood'}, first
        if args.scenario == 'dialogue':
            assert len(original['dialogue']) > 1, original
        receipt = await call('choose_ancient_option', {'option_id': value['ancient']['options'][0]['id']}, label='direct_choice')
        if args.scenario in {'selection', 'bundle'}:
            assert receipt['transition']['stop_reason'] == 'choice_required', receipt
            await rejection('selection_covered', 'inspect_selection')
            await call('inspect_selection', label='selection_details')
        elif args.scenario == 'nested':
            assert receipt['scene'] == 'rewards', receipt
            await rejection('rewards_covered', 'inspect_rewards')
            await call('inspect_rewards')
        else:
            assert receipt['transition']['complete'], receipt
            obtained = await call('inspect_ancient', {'preset': 'summary', 'option_ids': []}, label='obtained')
            assert obtained['ancient']['options'] == [] and obtained['ancient']['proceed']['enabled'], obtained
    print('PASS', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证先古详情预设、筛选和原生UI边界。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
