"""Verify rendered combat resources and action-owned combat entry through real MCP."""
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

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = reply.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert not reply.isError and 'error' not in data, data
                assert data == json.loads(reply.content[0].text), reply
                if 'transition' in data:
                    transition = data['transition']
                    assert transition['complete'], data
                    assert [e['sequence'] for e in transition['events']] == list(range(1, len(transition['events']) + 1))
                return data

            async def play(card):
                targets = await call('inspect_targets', {'card_id': card['id']})
                arguments = {'card_id': card['id']}
                if targets['requires_target']:
                    arguments['target_id'] = targets['targets'][0]['id']
                return await call('play_card', arguments)

            state = await call('get_observation')
            missing = []
            if args.scenario == 'fake_merchant':
                details = await call('inspect_targets', {'potion_slot': 0})
                assert details['targets'][0]['id'] == 'merchant', details
                receipt = await call('use_potion', {'potion_slot': 0, 'target_id': 'merchant'})
                assert receipt['scene'] == 'combat' and receipt['transition']['stop_reason'] == 'player_ready', receipt
                events = receipt['transition']['events']
                assert sum(e['type'] == 'potion_used' for e in events) == 1, events
                if not any(e['type'] == 'card_drawn' for e in events):
                    missing.append('combat entry draw events after Foul Potion')
                state = await call('get_observation')
                card = next(c for c in state['player']['hand'] if c['name'] in ('Strike', 'Defend'))
                receipt = await play(card)
                if not any(e['type'] == 'energy_changed' for e in receipt['transition']['events']):
                    missing.append('visible energy payment')
                # The first turn must continue with a valid receipt-derived permission.
                await call('end_turn')
                assert not missing, missing
            elif args.scenario in ('visibility', 'reveal_visibility', 'selection_entry'):
                result = await asyncio.to_thread(raw.call, 'check_test_star_reveal' if args.scenario == 'reveal_visibility'
                                                 else 'check_test_combat_resources') if args.scenario != 'selection_entry' else None
                if result:
                    record({'checks': result})
                    assert result['ok'] and result['state']['passed'], result
                else:
                    choice = (await call('inspect_selection', {'preset': 'summary'}))['selection']
                    receipt = await call('select_card', {'card_id': choice['cards'][0]['id']})
                    if receipt['transition']['stop_reason'] == 'choice_required':
                        receipt = await call('selection_option', {'option_id': 'confirm'})
                    assert receipt['scene'] == 'combat' and receipt['transition']['stop_reason'] == 'player_ready', receipt
                    assert any(e['type'] == 'card_drawn' for e in receipt['transition']['events']), receipt
                    await call('end_turn')
            else:
                name = {'spend': 'Strike', 'gain': 'Bloodletting', 'stars': 'Gather Light', 'star_spend': 'Strike',
                        'turbo': 'TURBO', 'choice': 'Armaments'}[args.scenario]
                card = next(c for c in state['player']['hand'] if c['name'] == name)
                receipt = await play(card)
                after = await call('get_observation')
                events = receipt['transition']['events']
                for kind, field in [('energy_changed', 'energy'), ('stars_changed', 'stars')]:
                    before_value, after_value = state['player'][field], (after.get('player') or {}).get(field)
                    changes = [e for e in events if e['type'] == kind]
                    if args.scenario == 'choice':
                        continue
                    if before_value != after_value and after_value is not None:
                        assert changes, (kind, state, receipt, after)
                        assert changes[-1]['after'] == after_value, (kind, events, after)
                        if before_value is not None:
                            assert changes[0]['before'] == before_value, (kind, state, events)
                if args.scenario == 'choice':
                    assert receipt['transition']['stop_reason'] == 'choice_required', receipt
                    choice = (await call('inspect_selection', {'preset': 'summary'}))['selection']
                    await call('select_card', {'card_id': choice['cards'][0]['id']})
                    await call('selection_option', {'option_id': 'confirm'})
                await call('end_turn')
    print(f'PASS combat resources: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证可见能量／星星与战斗交接日志。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
