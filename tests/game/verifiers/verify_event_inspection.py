"""Check static event presets and visible divination glyphs in an isolated game."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import base64
import json
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    assert not args.report.exists(), 'Use a fresh report.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=120)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, arguments=None):
        reply = await asyncio.to_thread(raw.call, operation, arguments=arguments,
                                        response_options={'include_divination_image': False})
        record({'native_operation': operation, 'arguments': arguments, 'result': reply})
        assert reply['ok'], reply
        return reply['state']

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                response = await session.call_tool(tool, {'preset': 'full', **(arguments or {})})
                result = response.structuredContent
                images = [part for part in response.content if part.type == 'image']
                record({'tool': tool, 'arguments': {'preset': 'full', **(arguments or {})},
                        'result': result, 'label': label, 'image_count': len(images)})
                assert result == json.loads(response.content[0].text), response
                assert result.get('error', {}).get('code') == error, result
                assert response.isError == bool(error), result
                assert len(images) == int(bool((arguments or {}).get('include_image')) and error is None
                                          and result.get('divination', {}).get('status') == 'visible'), result
                if images:
                    path = args.report.parent / f'{len(evidence):03}-{label or tool}.png'
                    path.write_bytes(base64.b64decode(images[0].data))
                return result

            initial = await call('get_observation')
            if args.scenario == 'no_event':
                refused = await call('inspect_event', error='illegal_action')
                assert 'event' in refused['error']['message'].lower(), refused
                assert refused['error']['recovery'] == 'choose_legal_action', refused
                await call('end_turn')
                return
            detail = await call('inspect_event', label='event_full')
            assert detail['event']['description']
            summary = await call('inspect_event', {'preset': 'summary'}, label='event_summary')
            for preset in ('full', 'default', 'summary'):
                observed = await call('get_observation', {'preset': preset})
                expected = dict(summary['event'])
                if preset == 'full': expected.setdefault('proceed', None)
                assert observed['event'] == expected, (observed['event'], expected)
            for page, close in [('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')]:
                await call(page)
                rejected = await call('inspect_event', error='illegal_action', label=page + '_covered')
                assert close in rejected['error']['message']
                assert rejected['error']['recovery'] == 'choose_legal_action'
                await call(close)
            if args.scenario in {'basic', 'display', 'locked'}:
                if args.scenario == 'display':
                    baseline = (await call('inspect_event'))['event']['options']
                    for mode in ('offscreen', 'chosen', 'no_hover', 'hidden', 'transparent', 'clipped'):
                        configured = await native('set_test_event_display', {'mode': mode})
                        inspected = (await call('inspect_event', label='event_' + mode))['event']['options']
                        if mode in {'hidden', 'transparent', 'clipped'}:
                            assert len(inspected) == len(baseline) - 1, (mode, inspected)
                        else:
                            assert [o['id'] for o in inspected] == [o['id'] for o in baseline]
                            if mode in {'offscreen', 'chosen'}:
                                assert [o['hover_tips'] for o in inspected] == [o['hover_tips'] for o in baseline]
                                assert configured['tips'] > 0
                            if mode == 'no_hover':
                                assert sum(bool(o['hover_tips']) for o in inspected) < sum(bool(o['hover_tips']) for o in baseline)
                    await native('set_test_event_display', {'mode': 'normal'})
                if args.scenario == 'basic':
                    option = next(o for o in detail['event']['options'] if o['enabled'])
                    await call('choose_event_option', {'option_id': option['id']})
                    await call('get_observation', label='event_next_page')
                return

            await call('choose_event_option', {'option_id': detail['event']['options'][1]['id']})
            observed = await call('get_observation', label='board_initial')
            assert observed['screen'] == {'status': 'visible', 'view': 'divination'}
            board = observed['divination']['grid']
            await native('check_test_divination')
            assert set(''.join(board['cell_rows'])) == {'#', '.'} and not board['visible_fragments']
            assert 'instructions' not in observed['divination'] and 'image' not in board
            await call('inspect_event', {'include_image': True}, label='board_with_image')
            await native('set_test_capture_failure', {'enabled': True})
            await call('inspect_event', label='text_ignores_png_failure')
            await call('get_observation', label='observation_ignores_png_failure')
            await call('inspect_event', {'include_image': True}, error='screenshot_unavailable')
            await native('set_test_capture_failure', {'enabled': False})
            await call('inspect_event')
            for page, close in [('inspect_map', 'close_map'), ('inspect_deck', 'close_card_view')]:
                await call(page)
                rejected = await call('inspect_event', error='illegal_action')
                assert close in rejected['error']['message']
                await call(close)
            geometry = await native('check_test_divination')
            if args.scenario == 'glyphs':
                seen = set()
                card_tops = set()
                for index, item in sorted(enumerate(geometry['items']), key=lambda pair: pair[1]['kind'] != 'CrystalSpherePotion'):
                    kind = item['kind']; key = (kind, item['width'], item['height'])
                    # Each card rarity uses the same native class; retain all three card icons.
                    if key in seen and kind != 'CrystalSphereCardReward': continue
                    seen.add(key)
                    for dy in range(item['height']):
                        for dx in range(item['width']):
                            await native('set_test_divination_display', {'mode': 'partial', 'index': index, 'x': dx, 'y': dy})
                            result = await call('inspect_event', label=f'partial_{index}_{dx}_{dy}')
                            grid = result['divination']['grid']; fragments = grid['visible_fragments']
                            assert len(fragments) <= 1, (item, grid)
                            if fragments:
                                fragment = fragments[0]
                                assert fragment['x'] == item['x'] + dx and fragment['y'] == item['y'] + dy
                                assert grid['cell_rows'][fragment['y']][fragment['x']] in ('s', 'S')
                                if kind == 'CrystalSpherePotion' and item['width'] == 1:
                                    assert fragment['appearance'] == ['potion.stopper', 'potion.body', 'potion.base'][dy], fragment
                                if kind == 'CrystalSphereCardReward' and dy == 1:
                                    assert fragment['appearance'] == ['card.lower_left', 'card.lower_right'][dx], fragment
                                    await native('set_test_divination_display', {'mode': 'swapped_banner', 'index': index, 'x': dx, 'y': dy})
                                    changed = await call('inspect_event', label='hidden_banner_changed')
                                    assert changed['divination']['grid'] == grid, (changed, grid)
                    await native('set_test_divination_display', {'mode': 'whole', 'index': index})
                    whole = await call('inspect_event', {'include_image': True}, label=f'whole_{index}')
                    grid = whole['divination']['grid']
                    assert grid['visible_fragments'] and 's' not in ''.join(grid['cell_rows']), grid
                    assert 'S' in ''.join(grid['cell_rows']), grid
                    if kind == 'CrystalSphereCardReward':
                        card_tops.update(f['appearance'] for f in grid['visible_fragments'] if f['appearance'].endswith('.upper_left'))
                    summary = await call('inspect_event', {'preset': 'summary'})
                    assert summary['divination']['grid']['visible_fragments'] == grid['visible_fragments']
                await native('set_test_divination_display', {'mode': 'normal'})
                assert len(seen) == 7, seen
                assert card_tops == {'card.common.upper_left', 'card.uncommon.upper_left', 'card.rare.upper_left'}, card_tops
                await call('get_observation')
                return
            # Genuine gameplay uses native clicks; the private fixture only selects coverage targets.
            await call('set_divination_tool', {'tool': 'small'})
            potion = next(i for i in geometry['items'] if i['kind'] == 'CrystalSpherePotion' and i['width'] == 1)
            await call('divine', {'x': potion['x'], 'y': potion['y'] + 2})
            part = await call('inspect_event', label='natural_potion_base')
            assert any(f['appearance'] == 'potion.base' for f in part['divination']['grid']['visible_fragments'])
            await call('set_divination_tool', {'tool': 'big'})
            planned = [(potion['x'], potion['y'] + 1)]
            card = next(i for i in geometry['items'] if i['kind'] == 'CrystalSphereCardReward')
            planned.append((card['x'], card['y']))
            while True:
                state = await call('get_observation')
                if state.get('scene') == 'rewards':
                    reward = next((r for r in state['rewards']['items'] if r['type'] == 'card'), None)
                    if reward:
                        await call('claim_reward', {'reward_id': reward['id']})
                        await call('selection_option', {'option_id': 'skip'})
                    await call('proceed')
                    continue
                if state.get('divination', {}).get('phase') == 'finished': break
                rows = state['divination']['grid']['cell_rows']
                while planned and rows[planned[0][1]][planned[0][0]] != '#': planned.pop(0)
                x, y = planned.pop(0) if planned else next((x, y) for y, row in enumerate(rows) for x, char in enumerate(row) if char == '#')
                await call('divine', {'x': x, 'y': y})
            await call('inspect_event', {'preset': 'summary'}, label='board_finished')
            await call('proceed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=('no_event', 'basic', 'display', 'locked', 'glyphs', 'play'), required=True)
    parser.add_argument('--report', type=__import__('pathlib').Path, required=True)
    asyncio.run(verify(parser.parse_args()))
