"""Verify relic summaries, original-index filters and action continuation over real MCP."""
from scripts._bootstrap import ROOT
from tests.game.support.relic_assertions import STATIC_FIELDS
from tests.game.support.verification_actions import full_output_arguments
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
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
                                  '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = {t.name: t for t in (await session.list_tools()).tools}
            assert set(listed['inspect_relics'].inputSchema['properties']) == {'preset', 'relic_indices'}

            async def call(name, arguments=None):
                reply = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = reply.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert not reply.isError and 'error' not in data, data
                assert data == json.loads(reply.content[0].text), reply
                return data

            async def presets(label):
                before = await asyncio.to_thread(raw.call, 'get_state')
                observed = await call('get_observation')
                full = await call('inspect_relics')
                assert full == await call('inspect_relics', {'preset': 'full'})
                summary = await call('inspect_relics', {'preset': 'summary'})
                basic = [{k: v for k, v in r.items() if k in STATIC_FIELDS} for r in full['relics']]
                assert summary == {**{k: full[k] for k in ('scene', 'screen')}, 'relics': [{k: v for k, v in r.items() if v is not None and not (v is False and k in {'grayed_out', 'pulsing'})} for r in basic]}, summary
                assert basic == observed['top_bar']['relics'], (basic, observed['top_bar']['relics'])
                assert len(basic) >= 2, 'Fixture must exercise multiple relic positions.'
                ordinary = [r for r in basic if r['name'] in {'Burning Blood', 'Anchor', 'Lantern', 'Pen Nib'}]
                assert ordinary and all(r['melted'] is None for r in ordinary), ordinary
                missing = len(basic) + 1000
                requested = [len(basic) - 1, 0, len(basic) - 1, missing, missing]
                for preset, source in (('full', full), ('summary', summary)):
                    for indices in (requested, []):
                        result = await call('inspect_relics', {'preset': preset, 'relic_indices': indices})
                        retained = [i for i in range(len(basic)) if i in indices]
                        assert result['relic_indices'] == retained
                        assert result['relics'] == [source['relics'][i] for i in retained]
                        assert result.get('errors') == ([{'code': 'relic_indices_out_of_range',
                                                         'relic_indices': [missing]}] if indices else None)
                        if preset == 'full':
                            links = {(i, t['title'], t['description'])
                                     for t in full['hover_tips'] for i in t['relic_indices'] if i in retained}
                            assert {(i, t['title'], t['description']) for t in result['hover_tips']
                                    for i in t['relic_indices']} == links
                        else:
                            assert 'hover_tips' not in result
                after = await asyncio.to_thread(raw.call, 'get_state')
                record({'label': label, 'native_before': before, 'native_after': after})
                assert before['ok'] and after['ok'] and before['state'] == after['state'], 'Inspection changed native state.'
                return observed, summary

            if args.scenario == 'shop':
                await call('get_observation')
                await call('open_shop')
                await presets('shop')
                result = await call('close_shop')
                assert result['transition']['complete'], result
            else:
                state, summary = await presets('before-melt')
                wax = next(r for r in summary['relics'] if r['name'] == "Wax Philosopher's Stone")
                assert wax['melted'] is False, wax
                card = next(c for c in state['player']['hand'] if c['name'] == 'Defend')
                receipt = await call('play_card', {'card_id': card['id']})
                assert receipt['transition']['complete'], receipt
                _, summary = await presets('after-melt')
                assert any(r['name'] == "Wax Philosopher's Stone" and r['melted'] is True
                           for r in summary['relics']), summary
                result = await call('end_turn')
                assert result['transition']['complete'], result
    print('PASS relic presets:', args.scenario, 'basic fields, original indices, tip links and direct actions')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证遗物预设与下标筛选。')
    parser.add_argument('--scenario', choices=('wax_melt', 'shop'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
