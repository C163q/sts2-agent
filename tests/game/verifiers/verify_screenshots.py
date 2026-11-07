"""Verify optional screenshot files and permission in an explicitly owned game."""
from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from tests.game.support.verification_runtime import ensure_run, ipc_directory
import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.mcp_catalog import tool_definitions
from sts2_mcp.output.media import png_data
from sts2_mcp.roundtrip_client import Client


async def verify(args):
    report = args.report.resolve()
    capture_dir = report.parent / 'captures'
    config = report.parent / 'screenshot-config.json'
    if report.exists() or capture_dir.exists() or config.exists():
        raise FileExistsError('Use a fresh screenshot report directory.')
    report.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(capture_dir)}}))
    client = Client(ipc_directory(), timeout=100)
    evidence = []

    def location(path):
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    def record(row):
        evidence.append(row)
        report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native():
        value = await asyncio.to_thread(client.call, 'get_state', response_options={'include_divination_image': False})
        record({'native_operation': 'get_state', 'result': value})
        assert value['ok'], value
        return value['state']

    if args.scenario == 'gui':
        assert (await asyncio.to_thread(ensure_run, client))['ok']
    else:
        deadline = time.monotonic() + 35
        while (await native())['scene'] != 'main_menu':
            assert time.monotonic() < deadline, 'Requires a fresh owned game at the menu.'
            await asyncio.sleep(.2)

    parameters = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(client.directory), '--config', str(config)])
    async with stdio_client(parameters) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()
        listed = {tool.name for tool in (await session.list_tools()).tools}
        assert listed == {tool.name for tool in tool_definitions(screenshots_enabled=True)}
        record({'registered_tools': sorted(listed), 'screenshots_enabled': True})

        async def call(name, arguments=None, *, label=None, error=None):
            supplied = full_output_arguments(name, arguments or {})
            before = set((client.directory / 'responses').glob('*.json'))
            reply = await session.call_tool(name, supplied)
            value = reply.structuredContent
            paths = set((client.directory / 'responses').glob('*.json')) - before
            row = {'tool': name, 'arguments': supplied, 'label': label, 'result': value,
                   'native_files': [location(p) for p in sorted(paths)]}
            if paths:
                assert len(paths) == 1
                packet = json.loads(next(iter(paths)).read_text())
                row.update(execution=packet.get('execution'))
                if name == 'capture_screenshot' and packet['ok']:
                    row['capture_snapshot_id'] = packet['state']['snapshot_id']
            record(row)
            assert value == json.loads(reply.content[0].text)
            assert reply.isError == bool(error) and value.get('error', {}).get('code') == error, value
            return value

        async def capture(label, filename=None):
            value = await call('capture_screenshot', {} if filename is None else {'filename': filename}, label=label)
            assert set(value) == {'path', 'width', 'height'}, value
            packet = json.loads((ROOT / evidence[-1]['native_files'][0]).read_text())
            pixels, width, height = png_data(packet['state'])
            image = Path(value['path'])
            assert image.parent == capture_dir and image.read_bytes() == pixels
            assert (value['width'], value['height']) == (width, height)
            record({'saved_file': location(image), 'label': label,
                    'sha256': hashlib.sha256(pixels).hexdigest(), 'bytes': len(pixels), 'dimensions': [width, height]})
            return value

        if args.scenario == 'headless':
            await call('capture_screenshot', label='headless_cold', error='screenshot_unavailable')
            await call('end_turn', label='cold_no_permission', error='observation_required')
            await call('get_observation')
            await call('capture_screenshot', label='headless_warm', error='screenshot_unavailable')
            await call('end_turn', label='headless_revokes_permission', error='observation_required')
            assert not capture_dir.exists()
            return
        if args.scenario == 'menu':
            await capture('menu', 'menu.png')
            await call('end_turn', label='menu_no_permission', error='observation_required')
        else:
            await call('capture_screenshot', label='cold_capture')
            await call('end_turn', label='cold_no_permission', error='observation_required')
            await call('get_observation')
            await capture('combat', 'combat.png')
            before = await native()
            error = await call('capture_screenshot', {'filename': 'combat.png'}, label='duplicate', error='file_exists')
            assert error['error']['recovery'] == 'change_filename'
            assert before['snapshot_id'] == evidence[-1]['capture_snapshot_id'] == (await native())['snapshot_id']
            await call('end_turn', label='direct_after_duplicate')
            await call('get_observation')
            backup = capture_dir.with_name('captures-before-error')
            assert not backup.exists()
            capture_dir.rename(backup)
            capture_dir.write_text('not a directory')
            try:
                before = await native()
                error = await call('capture_screenshot', label='directory_is_file', error='screenshot_save_failed')
                assert 'file' in error['error']['message'].lower()
                assert error['error']['recovery'] == 'check_screenshot_directory'
                assert before['snapshot_id'] == evidence[-1]['capture_snapshot_id'] == (await native())['snapshot_id']
                await call('end_turn', label='direct_after_directory_error')
            finally:
                capture_dir.unlink()
                backup.rename(capture_dir)
            await call('get_observation')
            error = await call('capture_screenshot', {'filename': '界' * 90 + '.png'}, label='long_filename', error='screenshot_save_failed')
            assert 'long' in error['error']['message'].lower() and error['error']['recovery'] == 'change_filename'
            await call('end_turn', label='direct_after_long_name')
            await call('get_observation')
            for label, bad in (('bad_path', {'filename': '../escape.png'}), ('bad_preset', {'preset': 'full'})):
                await call('capture_screenshot', bad, label=label, error='invalid_request')
            automatic = await capture('automatic')
            assert Path(automatic['path']).name != 'combat.png'
            await call('end_turn', label='direct_after_local_errors')
            await call('get_observation')
            result = await call('use_potion', {'potion_slot': 0})
            assert result['transition']['stop_reason'] == 'choice_required', result
            await capture('selection', 'selection.png')
            await call('set_selection_view', {'view': 'battlefield'})
            await capture('battlefield', 'battlefield.png')
            await call('set_selection_view', {'view': 'selection'})
            await call('capture_screenshot', {'filename': 'selection.png'}, label='selection_duplicate', error='file_exists')
            await call('selection_option', {'option_id': 'skip'}, label='direct_selection_skip')
            await call('inspect_map')
            await capture('map', 'map.png')
            await call('inspect_deck')
            await capture('deck', 'deck.png')
            closed = await call('close_card_view')
            if 'close_map' in closed['available_actions']: await call('close_map')
            assert not list(capture_dir.glob('.capture-*'))

    disabled_config = report.parent / 'disabled-config.json'
    disabled_config.write_text(json.dumps({'screenshots': {'enabled': False}}))
    parameters = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(client.directory), '--config', str(disabled_config)])
    async with stdio_client(parameters) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()
        names = {tool.name for tool in (await session.list_tools()).tools}
        assert names == {tool.name for tool in tool_definitions(screenshots_enabled=False)}
        before = set((client.directory / 'responses').glob('*.json'))
        reply = await session.call_tool('capture_screenshot', {})
        record({'tool': 'capture_screenshot', 'arguments': {}, 'label': 'disabled', 'result': reply.structuredContent})
        error = reply.structuredContent['error']
        assert reply.isError and error['code'] == 'invalid_request'
        assert error['recovery'] == 'check_configuration' and 'restart' in error['message'].lower()
        unknown = await session.call_tool('unknown_screenshot_tool', {})
        record({'tool': 'unknown_screenshot_tool', 'arguments': {}, 'label': 'unknown_tool', 'result': unknown.structuredContent})
        assert unknown.structuredContent['error']['recovery'] == 'correct_request'
        assert before == set((client.directory / 'responses').glob('*.json'))
    print('PASS screenshot', args.scenario, flush=True)


def main():
    parser = argparse.ArgumentParser(description='验证独立游戏的截图、文件错误和许可；gui会使用药水并结束回合。')
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--scenario', choices=('gui', 'menu', 'headless'), default='gui')
    parser.add_argument('--headless', action='store_true', help='旧命令兼容，等同--scenario headless')
    args = parser.parse_args()
    if args.headless:
        if args.scenario != 'gui': parser.error('Use either --headless or --scenario.')
        args.scenario = 'headless'
    asyncio.run(verify(args))


if __name__ == '__main__':
    main()
