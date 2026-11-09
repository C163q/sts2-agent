"""Check combatant levels, canonical object selection and recovery through real MCP."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.mcp_server import SERVER_VERSION
from sts2_mcp.output.presets import apply_preset
from sts2_mcp.roundtrip_client import Client
from tests.game.support.combatant_assertions import assert_combatant_inspection
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory(), timeout=110)
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    if args.scenario == 'basic':
        commands = [
            ['tests.game.verifiers.verify_combatants', '--output', str(args.report.parent / 'file.full.json')],
            ['tests.game.verifiers.verify_mcp_combatants', '--output', str(args.report.parent / 'stdio.full.json')]]
        for module, *extra in commands:
            completed = await asyncio.to_thread(subprocess.run,
                [sys.executable, '-m', module, '--ipc-dir', str(raw.directory), *extra,
                 '--report', str(args.report.parent / (module.rsplit('.', 1)[-1] + '.json'))],
                cwd=ROOT, capture_output=True, text=True, timeout=100)
            assert completed.returncode == 0, completed.stdout + completed.stderr
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
                      'directory': str(args.report.parent / 'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory), '--config', str(config)])
    evidence = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            assert (await session.initialize()).serverInfo.version == SERVER_VERSION

            async def call(name, options=None, error=None):
                arguments = {'preset': 'full', **(options or {})}
                if name == 'capture_screenshot': arguments = options
                response = await session.call_tool(name, arguments)
                result = response.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': result})
                args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
                assert result == json.loads(response.content[0].text)
                if error: assert response.isError and result['error']['code'] == error, result
                else: assert not response.isError and 'error' not in result, result
                return result

            observed = await call('get_observation')
            before = await asyncio.to_thread(raw.call, 'get_state')
            full = await call('inspect_combatants')
            assert_combatant_inspection(full, observed)
            default = await call('inspect_combatants', {'preset': 'default'})
            assert default == apply_preset(full, 'default')
            summary = await call('inspect_combatants', {'preset': 'summary'})
            summary_observed = await call('get_observation', {'preset': 'summary'})
            for group in ('player', 'enemies', 'allies'):
                units = [summary[group]] if group == 'player' else summary[group]
                observed_units = [summary_observed[group]] if group == 'player' else summary_observed[group]
                for unit, other in zip(units, observed_units, strict=True):
                    assert unit['health'] == other['health']
                    assert unit.get('block') == other.get('block')
                    assert not {'hp', 'max_hp', 'hp_display'} & unit.keys()
            assert 'hover_tips' not in summary
            assert await call('inspect_combatants', {'sources': None}) == full
            enemies = await call('inspect_combatants', {'preset': 'summary', 'sources': ['enemies']})
            assert set(enemies) <= {'scene', 'screen', 'enemies', 'notes'}
            assert enemies['enemies'] == summary['enemies']
            hp_only = await call('inspect_combatants', {'sources': ['enemies.0.hp', 'enemies.0.block']})
            assert hp_only['enemies'] == [{k: full['enemies'][0][k] for k in ('id', 'name', 'hp', 'block')}]
            assert hp_only['hover_tips'] == []
            health_only = await call('inspect_combatants', {'preset': 'summary', 'sources': ['enemies.0.health']})
            assert health_only['enemies'] == [{k: summary['enemies'][0][k] for k in ('id', 'name', 'health')}]
            empty = await call('inspect_combatants', {'sources': []})
            assert set(empty) == {'scene', 'screen'}, empty
            last = len(full['enemies']) - 1
            path = f'enemies.{last}.intents.0'
            selected = await call('inspect_combatants', {'sources': [path]})
            assert [e['id'] for e in selected['enemies']] == [full['enemies'][last]['id']]
            assert set(selected['enemies'][0]) == {'id', 'name', 'intents'}
            assert selected['enemies'][0]['intents'] == [full['enemies'][last]['intents'][0]]
            assert all(t['sources'] == [path] for t in selected['hover_tips'])
            if len(full['enemies']) > 1: assert selected['source_indices']['enemies'] == [last]
            partial = await call('inspect_combatants', {'sources': ['enemies.0', 'enemies.999', 'enemies.999']})
            assert partial['errors'] == [{'code': 'combatant_sources_unavailable', 'sources': ['enemies.999']}]
            assert [e['id'] for e in partial['enemies']] == [full['enemies'][0]['id']]
            assert (await asyncio.to_thread(raw.call, 'get_state'))['state'] == before['state']

            if args.scenario == 'orbs':
                slots = full['player']['orb_slots']
                assert len(slots) == 5 and slots[0] is None
                slot = await call('inspect_combatants', {'preset': 'summary', 'sources': ['player.orb_slots.0']})
                assert slot['player'] == {'orb_slots': [None]}
                assert slot['source_indices'] == {'player.orb_slots': [0]}
                assert 'hover_tips' not in slot
            elif args.scenario == 'osty':
                ally = await call('inspect_combatants', {'preset': 'summary', 'sources': ['allies']})
                assert [a['name'] for a in ally['allies']] == ['Osty']
                assert not {'player', 'enemies', 'hover_tips'} & ally.keys()
            elif args.scenario == 'blade':
                blade = await call('inspect_combatants', {'sources': ['player.sovereign_blades']})
                assert blade['player']['sovereign_blades'] == full['player']['sovereign_blades']
                assert set(blade['player']) == {'sovereign_blades'}
                assert any('15' in tip['description'] for tip in blade['hover_tips'])
            elif args.scenario == 'selection':
                card = next(c for c in observed['player']['hand'] if c['name'] == 'Armaments')
                receipt = await call('play_card', {'card_id': card['id']})
                assert receipt['transition']['stop_reason'] == 'choice_required'
                await call('inspect_combatants', {'preset': 'summary'}, error='illegal_action')
                await call('set_selection_view', {'view': 'battlefield'})
                choosing = await call('inspect_combatants', {'preset': 'summary', 'sources': []})
                assert set(choosing) == {'scene', 'screen', 'notes'}
                assert set(choosing['notes']) == {'selection'}
                assert 'hover_tips' not in choosing
                await call('set_selection_view', {'view': 'selection'})
            else:
                changed = await asyncio.to_thread(raw.call, 'set_test_combatant_hover',
                                                  arguments={'enabled': False})
                assert changed['ok'], changed
                disabled = changed['state']['source']
                try:
                    detailed = await call('inspect_combatants')
                    note = detailed['notes']['hover_tips_unavailable']
                    assert note['sources'] == [disabled], note
                    assert not any(disabled in tip['sources'] for tip in detailed['hover_tips'])
                    static = await call('inspect_combatants', {'preset': 'summary'})
                    assert 'hover_tips' not in static and 'hover_tips_unavailable' not in static['notes']
                    assert static['enemies'] == summary['enemies']
                    filtered = await call('inspect_combatants', {'sources': ['player']})
                    assert 'hover_tips_unavailable' not in filtered.get('notes', {})
                    await call('capture_screenshot', {'filename': 'disabled-hover.png'})
                finally:
                    restored = await asyncio.to_thread(raw.call, 'set_test_combatant_hover',
                                                       arguments={'enabled': True})
                    assert restored['ok'], restored
                invalid = await call('inspect_combatants', {'sources': [False]}, error='invalid_request')
                assert 'sources' in invalid['error']['message']
                missing = max(c['id'] for c in observed['player']['hand']) + 100000
                rejected = await call('play_card', {'card_id': missing}, error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                await call('inspect_deck')
                rejected = await call('inspect_combatants', error='illegal_action')
                assert 'covered' in rejected['error']['message']
                assert rejected['error']['recovery'] == 'choose_legal_action'
                await call('end_turn', error='illegal_action')
                await call('close_card_view')
                assert (await call('end_turn'))['transition']['stop_reason'] == 'player_ready'
            await call('capture_screenshot', {'filename': args.scenario + '.png'})
    print('PASS combatant presets:', args.scenario)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=('basic', 'orbs', 'osty', 'blade', 'selection'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
