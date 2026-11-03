"""Check shared scene context and UI help across exposed regions and covering pages."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.output.presets import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory(), timeout=140)
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
            initialized = await session.initialize()
            assert initialized.serverInfo.version == '0.51.0'
            schema = next(t.inputSchema for t in (await session.list_tools()).tools if t.name == 'inspect_ui')
            assert schema['properties']['preset']['enum'] == ['default', 'full', 'summary']
            assert set(schema['properties']) == {'preset', 'sources'}

            async def call(tool, arguments=None, error=None, label=None):
                arguments = arguments or {}
                if tool != 'capture_screenshot': arguments = {'preset': 'full', **arguments}
                reply = await session.call_tool(tool, arguments)
                data = reply.structuredContent
                evidence.append({'tool': tool, 'arguments': arguments, 'label': label, 'result': data,
                                 'images': sum(c.type == 'image' for c in reply.content)})
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert data == json.loads(reply.content[0].text)
                if error: assert reply.isError and data.get('error', {}).get('code') == error, (tool, data)
                else: assert not reply.isError and 'error' not in data, (tool, data)
                return data

            def context(value): return {k: value[k] for k in ('scene', 'screen')}

            async def check(label):
                state = await call('get_observation')
                before = await asyncio.to_thread(raw.call, 'get_state')
                allowed = 'inspect_ui' in state['available_actions']
                full = await call('inspect_ui', error=None if allowed else 'illegal_action', label=label)
                if allowed:
                    assert context(full) == context(state), (full, state)
                    assert not any('\u4e00' <= c <= '\u9fff' for c in json.dumps(full, ensure_ascii=False))
                    summary = await call('inspect_ui', {'preset': 'summary'}, label=label + '-summary')
                    expected = apply_preset({**full, 'hover_tips': [
                        {k: v for k, v in tip.items() if k != 'description'} for tip in full['hover_tips']]}, 'default')
                    assert summary == expected, (summary, expected)
                    default = await call('inspect_ui', {'preset': 'default'})
                    assert default == apply_preset(full, 'default')
                    assert (await call('inspect_ui', {'sources': []}))['hover_tips'] == []
                    if full['hover_tips']:
                        source = full['hover_tips'][0]['sources'][0]
                        filtered = await call('inspect_ui', {'sources': [source, 'missing.ui', source]}, label=label + '-filtered')
                        assert all(t['sources'] == [source] for t in filtered['hover_tips'])
                        assert filtered['errors'] == [{'code': 'ui_sources_unavailable', 'sources': ['missing.ui']}]
                        assert all('description' in t for t in filtered['hover_tips'])
                    sources = {s for tip in full['hover_tips'] for s in tip['sources']}
                    if state['top_bar'] is not None:
                        assert 'top_bar.hp' in sources and 'player.hp' not in sources, sources
                    if state['scene'] != 'combat' or state['screen']['status'] != 'visible':
                        assert not any(s.startswith('player.') and s != 'player.character' for s in sources), sources
                    assert await call('inspect_ui') == full
                after = await asyncio.to_thread(raw.call, 'get_state')
                # Board PNGs include visual animation; compare the native logical state.
                logical_before = {k: v for k, v in before['state'].items() if k != 'divination_image'}
                logical_after = {k: v for k, v in after['state'].items() if k != 'divination_image'}
                assert logical_before == logical_after, ('UI inspection mutated native observation', logical_before, logical_after)
                await call('capture_screenshot', {'filename': label + '.png'})
                print('Checked', args.scenario, label, state['scene'], state['screen'], flush=True)
                return state

            async def inspect(tool, arguments=None):
                result = await call(tool, arguments)
                observed = await call('get_observation')
                assert context(result) == context(observed), (tool, result, observed)
                return observed

            async def act(tool, arguments=None):
                await call('get_observation')
                result = await call(tool, arguments)
                assert result['transition']['complete'], result
                return await call('get_observation')

            if args.scenario == 'ancient':
                deadline = time.monotonic() + 10
                while True:
                    ready = await call('get_observation')
                    if {'choose_ancient_option', 'advance_dialogue'} & set(ready['available_actions']): break
                    assert time.monotonic() < deadline, ready
                    await asyncio.sleep(.1)
            state = await check('initial')
            for tool in ('inspect_combatants', 'inspect_selection', 'inspect_rewards', 'inspect_rest_site',
                         'inspect_treasure', 'inspect_shop', 'inspect_ancient', 'inspect_event', 'inspect_run_result'):
                if tool in state['available_actions']: state = await inspect(tool)
            if args.scenario == 'ending':
                state = await act('proceed')
                await check('epilogue')
                if 'inspect_combatants' in state['available_actions']: await inspect('inspect_combatants')
                await inspect('inspect_deck')
                await check('epilogue-deck')
                await call('close_card_view')
                await inspect('inspect_map')
                await check('epilogue-map')
                await call('close_map')
                state = await call('get_observation')
                for _ in range(20):
                    if state['scene'] == 'run_result': break
                    state = await act('advance_dialogue' if 'advance_dialogue' in state['available_actions'] else 'proceed')
                else: raise AssertionError('Ending did not finish')
                state = await check('outcome')
                await inspect('inspect_run_result')
                await act('run_result_option', {'option_id': 'continue'})
                await check('summary')
                await inspect('inspect_run_result')
            elif args.scenario == 'rewards':
                await act('proceed')
            elif args.scenario == 'confirmation':
                state = await act('choose_event_option', {'option_id': state['event']['options'][1]['id']})
                option = next(o for o in state['event']['options'] if o['lethal_warning'])
                await act('choose_event_option', {'option_id': option['id']})
                await check('confirmation')
                await act('respond_to_confirmation', {'option': 'cancel'})
            elif args.scenario == 'selection':
                card = next(c for c in state['player']['hand'] if c['name'] == 'Armaments')
                await act('play_card', {'card_id': card['id']})
                await check('selection')
                await inspect('inspect_selection')
                await call('set_selection_view', {'view': 'battlefield'})
                await check('battlefield')
                await call('set_selection_view', {'view': 'selection'})
            elif args.scenario == 'shop':
                await act('open_shop')
                await check('shop-inventory')
                await inspect('inspect_shop')
            elif args.scenario == 'divination':
                await act('choose_event_option', {'option_id': state['event']['options'][0]['id']})
                await check('divination')
                await inspect('inspect_event')
            else:
                if args.scenario == 'combat':
                    card = next(c for c in state['player']['hand'] if c['name'] == 'Defend')
                    await act('play_card', {'card_id': card['id']})
                    await inspect('inspect_pile', {'pile': 'discard', 'detail_level': 'full'})
                    await check('discard-view')
                    await call('close_card_view')
                if 'inspect_deck' in (await call('get_observation'))['available_actions']:
                    await inspect('inspect_deck')
                    await check('deck-view')
                    await call('close_card_view')
                if 'inspect_map' in (await call('get_observation'))['available_actions']:
                    await inspect('inspect_map')
                    await check('map-view')
    print('PASS UI context:', args.scenario, len(evidence), 'MCP calls', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=('combat', 'orbs', 'event', 'rest', 'treasure',
        'ancient', 'shop', 'rewards', 'selection', 'confirmation', 'divination', 'ending'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
