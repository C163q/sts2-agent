"""Verify visible card transfers and end-turn preflight recovery through MCP."""
from scripts._bootstrap import ROOT
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
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                data = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': data})
                assert data == json.loads(response.content[0].text)
                if error: assert response.isError and data['error']['code'] == error, data
                else: assert not response.isError, data
                return data

            def transfers(receipt, card_id, source, target):
                result = [e for e in receipt['transition']['events'] if e['type'] == 'card_moved'
                          and e['card']['id'] == card_id and e['from_pile'] == source and e['to_pile'] == target]
                assert all(set(e) == {'sequence', 'type', 'card', 'from_pile', 'to_pile'} for e in result), result
                return result

            def complete(receipt, reason='player_ready'):
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == reason, receipt
                events = receipt['transition']['events']
                assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), events
                assert all('position' not in e and 'internal_index' not in e for e in events), events

            before = await call('get_observation')
            if args.scenario == 'noncombat':
                rejected = await call('end_turn', error='illegal_action')
                assert 'combat' in rejected['error']['message'].lower(), rejected
                assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                assert before == await call('get_observation')
                option = next(o['id'] for o in before['event']['options'] if o['enabled'])
                await call('end_turn', error='illegal_action')
                await call('choose_event_option', {'option_id': option})
                return
            if args.scenario == 'preflight':
                for tool, keyword in [('inspect_deck', 'card'), ('inspect_map', 'map')]:
                    await call(tool)
                    covered = await call('get_observation')
                    rejected = await call('end_turn', error='illegal_action')
                    assert keyword in rejected['error']['message'].lower(), rejected
                    assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                    assert covered == await call('get_observation')
                    if tool == 'inspect_deck': await call('close_card_view')
                return
            if args.scenario in {'won', 'lost'}:
                receipt = await call('end_turn')
                complete(receipt, 'combat_won' if args.scenario == 'won' else 'combat_lost')
                assert 'inspect_relics' in receipt['available_actions'], receipt
                assert 'end_turn' not in receipt['available_actions'], receipt
                await call('end_turn', error='observation_required')
                await call('inspect_relics')
                return
            if args.scenario == 'checks':
                for operation in ('check_test_end_turn', 'check_test_card_movements'):
                    result = await asyncio.to_thread(raw.call, operation)
                    record({'native_operation': operation, 'response': result})
                    assert result['ok'] and result['state']['passed'], result
                return
            hand = (await call('inspect_hand'))['hand']
            target = max(before['enemies'], key=lambda e: e['hp'])['id']

            async def play(name, target_id=None, preset='full'):
                cards = (await call('inspect_hand'))['hand']
                card = next(c for c in cards if c['name'] == name)
                receipt = await call('play_card', {'card_id': card['id'], 'preset': preset,
                    **({'target_id': target_id} if target_id is not None else {})})
                manual = [e for e in receipt['transition']['events'] if e['type'] == 'card_played' and e['card']['id'] == card['id']]
                assert len(manual) == 1
                assert ('autoplay' not in manual[0] if preset == 'default' else manual[0]['autoplay'] is False), manual
                return card, receipt

            if args.scenario.startswith('headbutt_'):
                count = {'headbutt_empty': 0, 'headbutt_single': 1, 'headbutt_multiple': 2}[args.scenario]
                defend = next(c for c in hand if c['name'] == 'Defend')
                if count: await play('Defend', preset='default')
                if count == 2: await play('Strike', target)
                _, receipt = await play('Headbutt', target)
                if count == 2:
                    complete(receipt, 'choice_required')
                    choosing = (await call('inspect_selection'))['selection']
                    selected = next(c for c in choosing['cards'] if c['name'] == 'Defend')
                    assert selected['id'] == defend['id']
                    rejected = await call('end_turn', error='illegal_action')
                    assert 'selection' in rejected['error']['message'].lower(), rejected
                    assert rejected['error']['recovery'] == 'choose_legal_action', rejected
                    receipt = await call('select_card', {'card_id': selected['id']})
                complete(receipt)
                if count:
                    moved = transfers(receipt, defend['id'], 'discard', 'draw')
                    assert len(moved) == 1 and moved[0]['card']['name'] == 'Defend', receipt
                else: assert not transfers(receipt, defend['id'], 'discard', 'draw'), receipt
                after = await call('get_observation')
                assert after['player']['draw_count'] == int(bool(count)), after
                assert after['player']['discard_count'] == count + 1 - int(bool(count)), after
                return
            if args.scenario == 'shining':
                card, receipt = await play('Shining Strike', target)
                complete(receipt)
                assert len(transfers(receipt, card['id'], 'play', 'draw')) == 1, receipt
                after = await call('get_observation')
                assert after['player']['draw_count'] == 1 and after['player']['stars'] == 2, after
            elif args.scenario in {'hatchet', 'hatchet_draw'}:
                card, receipt = await play('Thrumming Hatchet', target)
                complete(receipt)
                assert len(transfers(receipt, card['id'], 'play', 'discard')) == 1, receipt
                if args.scenario == 'hatchet_draw':
                    _, returned = await play('Headbutt', target)
                    complete(returned)
                    assert len(transfers(returned, card['id'], 'discard', 'draw')) == 1, returned
                ended = await call('end_turn')
                complete(ended)
                assert len(transfers(ended, card['id'], 'draw' if args.scenario == 'hatchet_draw' else 'discard', 'hand')) == 1, ended
                assert not any(e['type'] == 'card_moved' and e['from_pile'] == 'discard' and e['to_pile'] == 'draw'
                               for e in ended['transition']['events']), ended
                assert not any(e['type'] == 'card_drawn' and e['card']['id'] == card['id'] for e in ended['transition']['events']), ended
                assert any(c['id'] == card['id'] for c in (await call('inspect_hand'))['hand'])
            elif args.scenario == 'knife':
                await play('Blade Dance')
                shivs = [c for c in (await call('inspect_hand'))['hand'] if c['name'] == 'Shiv']
                for _ in shivs: await play('Shiv', target)
                _, receipt = await play('Knife Trap', target, preset='default')
                complete(receipt)
                automatic = [e for e in receipt['transition']['events'] if e['type'] == 'card_played' and e['card']['name'] == 'Shiv']
                assert len(automatic) == 3 and all(e['autoplay'] is True for e in automatic), receipt
                assert all(e.get('source') == {'kind': 'card', 'name': 'Knife Trap'} for e in automatic), receipt
                assert any(transfers(receipt, c['id'], 'exhaust', 'play') for c in shivs), receipt
                exhausted = [e for e in receipt['transition']['events'] if e['type'] == 'card_exhausted' and e['card']['id'] in {c['id'] for c in shivs}]
                assert len(exhausted) == 3, receipt
                after = await call('get_observation')
                assert after['player']['exhaust_count'] == 4, after
    print('PASS turn transitions:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=['headbutt_empty', 'headbutt_single', 'headbutt_multiple', 'shining', 'hatchet', 'hatchet_draw', 'knife', 'won', 'lost', 'checks', 'preflight', 'noncombat'])
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
