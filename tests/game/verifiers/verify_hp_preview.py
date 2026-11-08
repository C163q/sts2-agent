"""Compare shared health previews with native rendered poison and doom states."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import base64
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

            async def call(tool, **arguments):
                reply = await session.call_tool(tool, arguments)
                result = reply.structuredContent
                evidence.append({'tool': tool, 'arguments': arguments, 'result': result})
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert not reply.isError, result
                assert result == json.loads(reply.content[0].text)
                return result

            cases = [
                ('normal', None),
                ('poison', {'poison_damage': 7, 'doom_threshold': None, 'lethal': None}),
                ('poison_lethal', {'poison_damage': 20, 'doom_threshold': None, 'lethal': 'poison'}),
                ('doom', {'poison_damage': None, 'doom_threshold': 10, 'lethal': None}),
                ('doom_lethal', {'poison_damage': None, 'doom_threshold': 20, 'lethal': 'doom'}),
                ('combined', {'poison_damage': 7, 'doom_threshold': 15, 'lethal': 'doom'}),
                ('accelerated', {'poison_damage': 18, 'doom_threshold': None, 'lethal': None}),
                ('hidden_poison', {'poison_damage': None, 'doom_threshold': 15, 'lethal': 'doom'}),
                ('hidden_doom', {'poison_damage': 7, 'doom_threshold': None, 'lethal': None}),
                ('hidden_bar', None), ('hidden_label', None),
                ('player', {'poison_damage': 7, 'doom_threshold': None, 'lethal': None}),
            ]
            try:
                for mode, expected in cases:
                    fixture = await asyncio.to_thread(raw.call, 'set_test_health_preview', arguments={'mode': mode})
                    assert fixture['ok'], fixture
                    target = fixture['state']['target_id']
                    evidence.append({'fixture': mode, 'target_id': target, 'expected': expected})
                    def unit(result):
                        return result['player'] if mode == 'player' else next(e for e in result['enemies'] if e['id'] == target)
                    for preset in ('full', 'default', 'summary'):
                        for tool in ('get_observation', 'inspect_combatants'):
                            result = await call(tool, preset=preset)
                            actual = unit(result)
                            want = expected if preset == 'full' or expected is None else {
                                k: v for k, v in expected.items() if v is not None}
                            assert actual.get('hp_preview') == want, (mode, preset, tool, actual, want)
                            if preset == 'full': assert 'hp_preview' in actual, actual
                            elif expected is None: assert 'hp_preview' not in actual, actual
                    if mode != 'player' and expected is not None:
                        index = next(i for i, e in enumerate(result['enemies']) if e['id'] == target)
                        selected = await call('inspect_combatants', preset='full', sources=[f'enemies.{index}.hp_preview'])
                        assert selected['enemies'][0]['hp_preview'] == expected, selected
                        assert 'powers' not in selected['enemies'][0], selected
                    if mode in {'poison_lethal', 'combined', 'accelerated'}:
                        screenshot = await asyncio.to_thread(raw.call, 'capture_screenshot')
                        assert screenshot['ok'], screenshot
                        (args.report.parent / f'{mode}.png').write_bytes(base64.b64decode(screenshot['state']['png_base64']))
            finally:
                restored = await asyncio.to_thread(raw.call, 'set_test_health_preview', arguments={'mode': 'normal'})
                assert restored['ok'], restored
    print('PASS health previews: 12 native display cases through both MCP tools', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
