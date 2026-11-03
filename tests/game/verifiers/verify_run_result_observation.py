"""Verify displayed result text, compact cards, and unchanged native UI."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory(), timeout=120)
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
        'directory': str(args.report.parent / 'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            def record(entry):
                evidence.append(entry)
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

            async def call(tool, arguments=None):
                arguments = arguments or {}
                if tool != 'capture_screenshot': arguments = {'preset': 'full', **arguments}
                reply = await session.call_tool(tool, arguments)
                result = reply.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert result == json.loads(reply.content[0].text)
                assert not reply.isError and 'error' not in result, (tool, result)
                return result

            async def native(operation):
                result = await asyncio.to_thread(raw.call, operation)
                record({'native': operation, 'result': result})
                assert result['ok'], result
                return result['state']

            async def capture(label):
                result = await call('get_observation')
                evidence[-1]['label'] = label
                await call('capture_screenshot', {'filename': label + '.png'})
                return result

            def english(result):
                texts = result['run_result']['texts']
                assert not any(re.search('[\u4e00-\u9fff]', text) for text in texts), ('Non-English visible result text', texts)

            data = await call('get_observation')
            if args.scenario != 'death':
                assert data['scene'] == 'rewards', data
                await call('proceed')
                for _ in range(12):
                    data = await call('get_observation')
                    if data['scene'] == 'run_result': break
                    assert data['scene'] == 'epilogue', data
                    await call('advance_dialogue' if 'advance_dialogue' in data['available_actions'] else 'proceed')
                else: raise AssertionError('Epilogue did not finish')
            outcome = await capture('outcome')
            english(outcome)
            assert outcome['run_result']['phase'] == 'outcome'
            if args.scenario == 'history':
                await native('prepare_test_browsable_result')
                await call('get_observation')
            await call('run_result_option', {'option_id': 'continue'})
            data = await capture('summary')
            if args.scenario == 'history':
                await native('prepare_test_browsable_history')
                data = await capture('history')
            english(data)
            before = await native('check_test_run_result_text')
            assert before['texts'] and any(re.search('[\u4e00-\u9fff]', t) for t in before['texts']), before
            for preset in ('full', 'default', 'summary', 'actions_only', 'top_bar'):
                current = await call('get_observation', {'preset': preset})
                if 'run_result' in current:
                    english(current)
                    assert current['run_result']['texts'] == data['run_result']['texts'], (preset, current, data)
            detail = await call('inspect_run_result')
            english(detail)
            assert detail['run_result']['texts'] == data['run_result']['texts']
            assert await native('check_test_run_result_text') == before, 'Observation changed native text or locale'
            assert await call('get_observation') == data, 'Repeated observation changed the result'
    print(f'PASS: {args.scenario}; {len(evidence)} calls/checks', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('death', 'history'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
