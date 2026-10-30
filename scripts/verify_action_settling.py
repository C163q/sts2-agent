import argparse
import asyncio
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    before = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while before['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        before = await asyncio.to_thread(raw.call, 'get_state')
    assert before['state']['scene'] == 'main_menu', 'Requires a fresh isolated game instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', before['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                result = await session.call_tool(name, arguments or {})
                assert result.structuredContent == json.loads(result.content[0].text)
                data = result.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert 'error' not in data, data
                return data

            for index, name in enumerate(('Strike', 'Defend')):
                observation = await call('get_observation')
                card = next(c for c in observation['player']['hand'] if c['name'] == name)
                query = await call('inspect_targets', {'card_id': card['id']})
                assert query['playable'], query
                played = await call('play_card', {'card_id': card['id'], **(
                    {'target_id': query['targets'][0]['id']} if query['requires_target'] else {})})
                assert played['transition']['stop_reason'] == 'player_ready' and played['transition']['complete'], played
                await call('capture_screenshot', {'filename': f'{index}-returned.png'})
                await asyncio.sleep(2)
                later = await call('get_observation')
                await call('capture_screenshot', {'filename': f'{index}-later.png'})
                expected = observation['player']['discard_count'] + 1
                print(name, 'returned', played['player']['discard_count'], 'later', later['player']['discard_count'], flush=True)
                assert played['player']['discard_count'] == later['player']['discard_count'] == expected, (
                    'player_ready returned before visible discard count settled', played['player'], later['player'])
                assert played['player'] == later['player'] and played['enemies'] == later['enemies'], (
                    'Public gameplay state changed after a completed action without another input', played, later)
            observed = await call('get_observation')
            ended = await call('end_turn')
            assert ended['transition']['stop_reason'] == 'player_ready' and ended['transition']['complete'], ended
            assert ended['turn'] == observed['turn'] + 1
            await call('capture_screenshot', {'filename': 'turn-returned.png'})
            await asyncio.sleep(2)
            later = await call('get_observation')
            await call('capture_screenshot', {'filename': 'turn-later.png'})
            assert ended['player'] == later['player'] and ended['enemies'] == later['enemies'], (
                'Public state changed after a completed turn without another input', ended, later)
    print('PASS: real MCP normal card returns include settled visible pile counts and remain unchanged without input.')


def main():
    parser = argparse.ArgumentParser(description='验证隔离图形实例的出牌返回及稍后可见牌堆计数；会打出打击与防御。')
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
