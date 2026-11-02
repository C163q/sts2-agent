"""Verify visible Osty and Sovereign Blade support through real MCP."""
from scripts._bootstrap import ROOT
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
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
                                                               '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = reply.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert not reply.isError and 'error' not in data, data
                return data

            state = await call('get_observation')
            if args.scenario == 'first':
                assert state['allies'] == [], state
                guard = next(c for c in state['player']['hand'] if c['name'] == 'Bodyguard')
                receipt = await call('play_card', {'card_id': guard['id']})
                added = [e for e in receipt['transition']['events'] if e['type'] == 'creature_added']
                assert len(added) == 1 and added[0]['target']['name'] == 'Osty' and added[0]['target']['kind'] == 'ally', receipt
                state = await call('get_observation')
                assert len(state['allies']) == 1 and state['allies'][0]['hp'] == state['allies'][0]['max_hp'] == 5, state
                await call('end_turn')
                return
            if args.scenario in {'checks', 'blade_checks'}:
                checked = await asyncio.to_thread(raw.call, 'check_test_blades' if args.scenario == 'blade_checks' else 'check_test_companions')
                evidence.append({'native_checks': checked})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert checked['ok'] and checked['state']['passed'], checked
                return
            if args.scenario == 'blade':
                blades = state['player'].get('sovereign_blades')
                assert blades and len(blades) == 1, state
                cards = {card['name']: card['id'] for card in state['player']['hand']}
                assert blades == [{'id': cards['Sovereign Blade'], 'name': 'Sovereign Blade'}], blades
                target = state['enemies'][0]['id']
                details = await call('inspect_combatants')
                tip = next(t for t in details['hover_tips'] if 'player.sovereign_blades.0' in t['sources'])
                assert '15' in tip['description'], tip
                await call('play_card', {'card_id': cards['Wrought in War'], 'target_id': target})
                await call('play_card', {'card_id': cards['Refine Blade']})
                details = await call('inspect_combatants')
                tip = next(t for t in details['hover_tips'] if 'player.sovereign_blades.0' in t['sources'])
                assert '31' in tip['description'], tip
                receipt = await call('play_card', {'card_id': cards['Sovereign Blade'], 'target_id': target})
                hits = [e for e in receipt['transition']['events'] if e['type'] == 'damage']
                assert len(hits) == 1 and hits[0]['source'] == {'kind': 'card', 'name': 'Sovereign Blade'}, hits
                assert hits[0]['actor']['kind'] == 'player' and hits[0]['hp_loss'] == 31, hits
                details = await call('inspect_combatants')
                assert details['player']['sovereign_blades'] == blades, details
                tip = next(t for t in details['hover_tips'] if 'player.sovereign_blades.0' in t['sources'])
                assert '31' in tip['description'], tip
                first = await asyncio.to_thread(raw.call, 'get_state')
                await asyncio.sleep(1.1)
                second = await asyncio.to_thread(raw.call, 'get_state')
                assert first['state']['snapshot_id'] == second['state']['snapshot_id'], (first, second)
                await call('end_turn')
            else:
                assert 'allies' in state, 'Missing public ally observations.'
                assert [ally['name'] for ally in state['allies']] == ['Osty'], state
                assert all(enemy['name'] != 'Osty' for enemy in state['enemies']), state
                osty = state['allies'][0]
                assert osty['hp'] == osty['max_hp'] == 1 and osty['block_shared_with'] == 'player', osty
                cards = state['player']['hand']
                unleash = next(card['id'] for card in cards if card['name'] == 'Unleash')
                bodyguards = [card['id'] for card in cards if card['name'] == 'Bodyguard']
                target = state['enemies'][0]['id']
                details = await call('inspect_combatants')
                assert details['allies'][0]['id'] == osty['id'], details
                assert any(any(s.startswith('allies.0.powers.') for s in t['sources']) for t in details['hover_tips']), details
                receipt = await call('play_card', {'card_id': unleash, 'target_id': target})
                hits = [e for e in receipt['transition']['events'] if e['type'] == 'damage']
                assert len(hits) == 1 and hits[0]['actor'] == {'id': osty['id'], 'kind': 'ally', 'name': 'Osty'}, hits
                assert hits[0]['source'] == {'kind': 'card', 'name': 'Unleash'}, hits
                receipt = await call('end_turn')
                life = [e['type'] for e in receipt['transition']['events']
                        if e.get('target', {}).get('id') == osty['id'] and e['type'] in {'died', 'revived'}]
                assert life == ['died', 'revived'], receipt
                for card_id, before in zip(bodyguards, (1, 6), strict=True):
                    receipt = await call('play_card', {'card_id': card_id})
                    growth = [e for e in receipt['transition']['events'] if e['type'] == 'max_hp_changed']
                    assert len(growth) == 1 and growth[0]['target']['kind'] == 'ally', receipt
                    assert (growth[0]['before'], growth[0]['after']) == (before, before + 5), growth
                await call('end_turn')
    print(f'PASS companions: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['osty', 'blade', 'checks', 'blade_checks', 'first'])
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
