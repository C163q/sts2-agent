"""Compare displayed relics with native labels and exercise fixture-only missing hover help."""
from scripts._bootstrap import ROOT
from tests.game.support.relic_assertions import STATIC_FIELDS
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
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(value):
        evidence.append(value)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    checked = await asyncio.to_thread(raw.call, 'check_test_display_readers')
    record({'native_checks': checked})
    assert checked['ok'], checked
    assert all(item['passed'] for item in checked['state']['results'])
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
                                   '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None):
                result = await session.call_tool(tool, arguments or {})
                data = result.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': data})
                assert not result.isError and 'error' not in data, data
                return data

            before = await asyncio.to_thread(raw.call, 'get_state')
            full = await call('inspect_relics', {'preset': 'full'})
            summary = await call('inspect_relics', {'preset': 'summary'})
            observation = await call('get_observation', {'preset': 'full'})
            assert [{k: v for k, v in r.items() if k in STATIC_FIELDS}
                    for r in full['relics']] == observation['top_bar']['relics']
            assert len(summary['relics']) == len(full['relics'])
            assert 'notes' not in summary and 'hover_tips' not in summary
            assert before['state'] == (await asyncio.to_thread(raw.call, 'get_state'))['state']
            for tool, field, collection in (
                ('inspect_relics', 'relic_indices', 'relics'),
                ('inspect_hand', 'card_ids', 'hand'),
                ('inspect_ui', 'sources', 'hover_tips'),
                ('inspect_combatants', 'sources', None),
            ):
                all_items = await call(tool, {'preset': 'full'})
                null_filter = await call(tool, {'preset': 'full', field: None})
                assert null_filter == all_items, (tool, null_filter, all_items)
                empty = await call(tool, {'preset': 'full', field: []})
                if collection: assert empty[collection] == [], (tool, empty)
                else: assert not {'player', 'enemies', 'allies'} & empty.keys(), empty
            await call('inspect_targets', {'preset': 'full', 'card_id': observation['player']['hand'][0]['id']})
            lantern = next(i for i, relic in enumerate(full['relics']) if relic['name'] == 'Lantern')
            filtered = await call('inspect_relics', {'preset': 'full', 'relic_indices': [lantern]})
            assert filtered['relic_indices'] == [lantern]
            assert filtered['hover_tips'] and all(tip['relic_indices'] == [lantern] for tip in filtered['hover_tips'])
            changed = await asyncio.to_thread(raw.call, 'set_test_relic_hover', arguments={'enabled': False})
            record({'fixture_injection': changed})
            assert changed['ok'], changed
            source = changed['state']['source']
            index = int(source.split('.')[1])
            try:
                full = await call('inspect_relics', {'preset': 'full'})
                default = await call('inspect_relics')
                summary = await call('inspect_relics', {'preset': 'summary'})
                assert full['relics'][index]['description'] is None
                assert 'description' not in default['relics'][index]
                assert full['notes']['hover_tips_unavailable']['sources'] == [source]
                assert default['notes'] == full['notes']
                assert 'notes' not in summary and 'hover_tips' not in summary
                assert len(full['relics']) == len(summary['relics']) == len(observation['top_bar']['relics'])
                selected = await call('inspect_relics', {'preset': 'full', 'relic_indices': [index, 0, index]})
                assert selected['relic_indices'] == [0, index]
                assert selected['notes']['hover_tips_unavailable']['sources'] == [source]
                assert all(index not in tip['relic_indices'] for tip in selected['hover_tips'])
                for indices in ([], [0]):
                    selected = await call('inspect_relics', {'relic_indices': indices})
                    assert 'notes' not in selected
                static_native = await asyncio.to_thread(raw.call, 'inspect_relics', arguments={'level': 'summary'})
                record({'native_summary': static_native})
                assert static_native['ok']
                assert static_native['state']['unavailable_hover_sources'] == []
                assert all(r['description'] is None and r['hover_tips'] == [] for r in static_native['state']['relics'])
            finally:
                restored = await asyncio.to_thread(raw.call, 'set_test_relic_hover', arguments={'enabled': True})
                assert restored['ok'], restored
            await call('inspect_map')
            await call('inspect_relics')
            await call('inspect_potions')
            await call('inspect_ui')
            page = await call('get_observation')
            if 'close_map' in page['available_actions']: await call('close_map')
            await call('inspect_deck')
            await call('inspect_relics')
            await call('inspect_potions')
            await call('inspect_ui')
            await call('close_card_view')
            page = await call('get_observation')
            if 'end_turn' in page['available_actions']: await call('end_turn')
    print('PASS shared display readers and fixture-only missing relic hover help', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
