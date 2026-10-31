import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client
from verification_actions import completed_action_snapshot


async def verify(args):
    root = Path(__file__).resolve().parents[1]
    report = args.report.resolve()
    if report.exists() or report.with_suffix('').exists():
        raise ValueError('Use a fresh report and screenshot directory.')
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.with_suffix(''))}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    initial = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while initial['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        initial = await asyncio.to_thread(raw.call, 'get_state')
    assert initial['state']['scene'] == 'main_menu', 'Requires a fresh isolated test game.'
    created = await asyncio.to_thread(Client(raw.directory, timeout=120).call,
                                      'start_test_combat', initial['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[str(root / 'scripts/mcp_server.py'),
                                  '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, *, error=None):
                start = time.monotonic()
                result = await session.call_tool(name, arguments or {})
                data = result.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'elapsed': time.monotonic() - start, 'result': data})
                report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert data == json.loads(result.content[0].text), result
                if error:
                    assert data.get('error', {}).get('code') == error, data
                elif result.isError:
                    await session.call_tool('capture_screenshot', {'filename': 'failure.png'})
                    raise AssertionError(data)
                return data

            state = await call('get_observation')
            defend = next(c for c in state['player']['hand'] if c['name'] == 'Defend')
            if args.scenario == 'choice':
                for discovery in (c for c in state['player']['hand'] if c['name'] == 'Discovery'):
                    choosing = await call('play_card', {'card_id': discovery['id']})
                    assert choosing['transition']['stop_reason'] == 'choice_required' and choosing['transition']['complete'], choosing
                    choices = await call('inspect_selection')
                    candidate = choices['selection']['cards'][0]['id']
                    # The native choose-one UI has a brief click delay; do not refresh permission.
                    await asyncio.sleep(1)
                    resolved = await call('select_card', {'card_id': candidate})
                    assert resolved['transition']['stop_reason'] == 'player_ready' and resolved['transition']['complete'], resolved
                    assert 'select_card' in choosing['available_actions'], choosing
                await call('play_card', {'card_id': defend['id']})
                assert sum(e.get('tool') == 'get_observation' for e in evidence) == 1
                print('PASS choice native click readiness and continuation')
                return
            victim = state['enemies'][0]['id']
            if args.scenario == 'ui':
                settled = await call('use_potion', {'potion_slot': 1})
            elif args.scenario == 'potion':
                settled = await call('use_potion', {'potion_slot': 0, 'target_id': victim})
            else:
                strike = next(c for c in state['player']['hand'] if c['name'] == 'Strike')
                settled = await call('play_card', {'card_id': strike['id'], 'target_id': victim})
            assert settled['transition']['stop_reason'] == 'player_ready' and settled['transition']['complete'], settled
            settled_snapshot = completed_action_snapshot(raw.directory, settled)
            if args.scenario != 'ui':
                assert any(e['type'] == 'died' and e['target']['id'] == victim for e in settled['transition']['events']), settled
            # Cross the original native death/fade window without refreshing MCP permission.
            await asyncio.sleep(4)
            following = await call('play_card', {'card_id': defend['id']})
            assert following['transition']['stop_reason'] == 'player_ready' and following['transition']['complete'], following
            assert completed_action_snapshot(raw.directory, following)['player']['block'] >= 5, following
            if args.scenario not in {'phase', 'ui'}:
                assert all(e['id'] != victim for e in settled_snapshot['enemies']), settled_snapshot
            if args.scenario == 'phase':
                assert any(e['id'] == victim and e['hp_display'] == 'hidden' for e in settled_snapshot['enemies']), settled_snapshot
            await call('capture_screenshot', {'filename': 'continued.png'})

            # External actions must still invalidate the last returned permission.
            current = await asyncio.to_thread(raw.call, 'get_state')
            external = await asyncio.to_thread(raw.call, 'end_turn', current['state']['snapshot_id'])
            evidence.append({'external_test_action': 'end_turn', 'response': external})
            report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
            assert external['ok'], external
            if args.scenario == 'phase':
                assert any(e['type'] == 'revived' and e['target']['id'] == victim
                           for e in external['state']['transition']['events']), external
                assert any(e['id'] == victim and e['hp'] > 1 for e in external['state']['enemies']), external
            await call('end_turn', error='stale_state')
            await call('end_turn', error='observation_required')
            assert sum(e.get('tool') == 'get_observation' for e in evidence) == 1
    print('PASS', args.scenario, 'native boundary, delayed continuation, and stale-state protection')


def main():
    parser = argparse.ArgumentParser(description='验证击杀退场后直接续接动作，不刷新或重试。')
    parser.add_argument('--scenario', choices=('card', 'potion', 'phase', 'ui', 'choice'), default='card')
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
