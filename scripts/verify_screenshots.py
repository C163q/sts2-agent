import argparse
import asyncio
import json
import struct
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from roundtrip_client import Client


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    capture_dir = report.parent / ('captures-headless' if args.headless else 'captures')
    config = report.parent / ('headless-config.json' if args.headless else 'graphical-config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(capture_dir)}}))
    client = Client(root / '.tmp/roundtrip/ipc')
    state = await asyncio.to_thread(client.call, 'get_state')
    deadline = time.monotonic() + 30
    while state['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        state = await asyncio.to_thread(client.call, 'get_state')
    assert state['ok'] and state['state']['scene'] == 'main_menu', 'Requires a fresh isolated instance.'
    evidence = []
    parameters = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'),
        args=[str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.version == '0.16.0'
            assert len((await session.list_tools()).tools) == 21

            async def call(name, arguments=None):
                result = await session.call_tool(name, arguments or {})
                assert json.loads(result.content[0].text) == result.structuredContent
                data = result.structuredContent
                assert 'png_base64' not in data and 'snapshot_id' not in data
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                return data

            async def capture(name):
                before = await asyncio.to_thread(client.call, 'get_state')
                deadline, stable_since = time.monotonic() + 5, time.monotonic()
                while time.monotonic() < deadline:
                    await asyncio.sleep(.1)
                    sampled = await asyncio.to_thread(client.call, 'get_state')
                    if sampled['state']['snapshot_id'] != before['state']['snapshot_id']:
                        stable_since = time.monotonic()
                    before = sampled
                    if time.monotonic() - stable_since >= .3:
                        break
                data = await call('capture_screenshot', {'filename': name})
                assert set(data) == {'path', 'width', 'height'}, data
                image = Path(data['path'])
                assert image.parent == capture_dir and image.is_file()
                raw = image.read_bytes()
                assert raw[:8] == b'\x89PNG\r\n\x1a\n'
                assert struct.unpack('>II', raw[16:24]) == (data['width'], data['height'])
                assert (data['width'], data['height']) == (1280, 720)
                after = await asyncio.to_thread(client.call, 'get_state')
                assert after['state']['snapshot_id'] == before['state']['snapshot_id'], 'Capture changed the UI or model.'
                return data

            if args.headless:
                unavailable = await call('capture_screenshot')
                assert unavailable['error']['code'] == 'screenshot_unavailable', unavailable
                assert not capture_dir.exists()
                assert (await call('end_turn'))['error']['code'] == 'observation_required'
                print('PASS: headless explicitly refuses capture; no output file or action permission.')
                return

            await capture('01-menu.png')
            assert (await call('end_turn'))['error']['code'] == 'observation_required'
            result = await asyncio.to_thread(client.call, 'start_test_combat', state['state']['snapshot_id'])
            assert result['ok'], result
            # Allow the fixture's initial visual entrance animations to complete.
            await asyncio.sleep(1)
            await call('get_observation')
            await capture('02-battle.png')
            data = await call('use_potion', {'potion_slot': 0})
            assert data['transition']['stop_reason'] == 'choice_required', data
            await capture('03-selection.png')
            before = Path(capture_dir / '03-selection.png').read_bytes()
            duplicate = await call('capture_screenshot', {'filename': '03-selection.png'})
            assert duplicate['error']['code'] == 'file_exists', duplicate
            assert Path(capture_dir / '03-selection.png').read_bytes() == before
            await call('set_selection_view', {'view': 'battlefield'})
            peek = await call('get_observation')
            assert peek['selection']['status'] == 'battlefield'
            await capture('04-battlefield.png')
            await call('set_selection_view', {'view': 'selection'})
            selection = await call('get_observation')
            assert selection['selection']['status'] == 'visible'
            await capture('05-return-selection.png')
            await call('get_observation')
            result = await call('selection_option', {'option_id': 'skip'})
            assert result['transition']['stop_reason'] == 'player_ready', result
            await call('get_observation')
            await capture('06-return-battle.png')
            result = await call('end_turn')
            assert result['transition']['stop_reason'] == 'player_ready', result
            await capture('07-next-turn.png')
            assert (await call('end_turn'))['error']['code'] == 'observation_required'
            await call('inspect_map')
            await capture('08-map.png')
            await call('inspect_deck')
            await capture('09-deck.png')
            await call('close_card_view')
            await capture('10-return-map.png')
            invalid = await call('capture_screenshot', {'filename': '../escape.png'})
            assert invalid['error']['code'] == 'invalid_request'
            generated = await call('capture_screenshot')
            assert Path(generated['path']).is_file()
    print('PASS: 21 tools; main menu, combat, selection, battlefield, map, deck; native actions and capture permissions.')


def main():
    parser = argparse.ArgumentParser(description='验证隔离游戏的可选截图 MCP 工具；会使用药水并结束一个回合。')
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--headless', action='store_true')
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
