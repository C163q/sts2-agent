"""Exercise public native card batches and their cross-choice receipts."""
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


SCENARIOS = ('admission', 'ordered', 'native_reject', 'default', 'single_entry', 'autoplay', 'pending_reset', 'after_reset', 'diagnostics', 'atomic', 'partial', 'zero', 'energy', 'stars', 'target',
    'random_exhaust', 'hand_exhaust', 'automatic_hand', 'choose_one', 'immediate_choice',
    'combat_pile', 'victory', 'death', 'immediate_death')


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None):
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert result == json.loads(response.content[0].text)
                if error: assert response.isError and result['error']['code'] == error, result
                else: assert not response.isError, result
                return result

            before = await call('get_observation')
            hand = (await call('inspect_hand'))['hand']
            if args.scenario == 'admission':
                assert before['player']['energy'] == 0
                card = next(c for c in hand if c['name'] == 'Defend')
                for tool in ('play_card', 'play_cards'):
                    armed = await asyncio.to_thread(raw.call, 'arm_test_card_rejection', arguments={'card_id': card['id']})
                    assert armed['ok'], armed
                    result = await call(tool, {'card_id': card['id']} if tool == 'play_card' else
                                        {'cards': [{'card_id': card['id']}]},
                                        error='illegal_action' if tool == 'play_card' else None)
                    reason = result['error']['message'] if tool == 'play_card' else result['card_plays']['results'][0]['reason']
                    assert 'energy' in reason.lower(), result
                    checked = await asyncio.to_thread(raw.call, 'arm_test_card_rejection', arguments={'card_id': card['id']})
                    record({'native_operation': 'arm_test_card_rejection', 'response': checked})
                    assert checked['state']['previous_attempts'] == 1, checked
                    if tool == 'play_cards':
                        assert result['card_plays']['results'][0]['status'] == 'not_submitted'
                        assert result['transition']['events'] == []
                assert (await call('end_turn'))['transition']['stop_reason'] == 'player_ready'
                return
            if args.scenario == 'after_reset':
                result = await call('end_turn')
                assert 'card_plays' not in result
                assert not any(e['type'] == 'card_played' for e in result['transition']['events'])
                return
            if args.scenario == 'diagnostics':
                checks = []
                await call('inspect_deck')
                rejected = await call('play_card', {'card_id': hand[0]['id']}, error='illegal_action')
                checks.append('brows' in rejected['error']['message'].lower())
                await call('close_card_view')
                for card in hand[:3]: await call('play_card', {'card_id': card['id']})
                query = await call('inspect_targets', {'card_id': hand[3]['id']})
                rejected = await call('play_card', {'card_id': hand[3]['id']}, error='illegal_action')
                checks.append('Normality' in rejected['error']['message'] and 'Normality' in query['reason'])
                await call('inspect_map')
                rejected = await call('play_card', {'card_id': hand[3]['id']}, error='illegal_action')
                checks.append('map' in rejected['error']['message'].lower())
                assert all(checks), checks
                return
            target = (min if args.scenario == 'target' else max)(before['enemies'], key=lambda e: e['hp'])['id']
            if args.scenario == 'autoplay':
                dance = next(c for c in hand if c['name'] == 'Blade Dance')
                await call('play_card', {'card_id': dance['id']})
                shivs = [c for c in (await call('inspect_hand'))['hand'] if c['name'] == 'Shiv']
                assert len(shivs) == 3
                for card in shivs: await call('play_card', {'card_id': card['id'], 'target_id': target})
                hand = (await call('inspect_hand'))['hand']
            if args.scenario == 'single_entry': hand = [next(c for c in hand if c['name'] == 'Defend')]
            targeted = {'Strike', 'Bash', 'Headbutt', 'Knife Trap'}
            cards = [{'card_id': c['id'], **({'target_id': target} if c['name'] in targeted else {})} for c in hand]
            if args.scenario == 'native_reject':
                initial = await asyncio.to_thread(raw.call, 'get_state')
                for _ in range(2):
                    armed = await asyncio.to_thread(raw.call, 'arm_test_card_rejection', arguments={'card_id': cards[0]['card_id']})
                    record({'native_operation': 'arm_test_card_rejection', 'response': armed})
                    assert armed['ok'], armed
                    if _ == 0:
                        rejected = await call('play_card', cards[0], error='illegal_action')
                        assert rejected['error']['recovery'] == 'choose_legal_action'
                        assert initial['state'] == (await asyncio.to_thread(raw.call, 'get_state'))['state']
            if args.scenario == 'atomic':
                state = await asyncio.to_thread(raw.call, 'get_state')
                for invalid in ([cards[0], {'card_id': 2147483647}], [cards[0], {'card_id': hand[1]['id'], 'target_id': target}],
                                [cards[0], {'card_id': hand[-1]['id'], 'target_id': 4294967295}]):
                    rejected = await call('play_cards', {'cards': invalid}, error='illegal_action')
                    assert rejected['error']['recovery'] == 'choose_legal_action'
                    assert state['state'] == (await asyncio.to_thread(raw.call, 'get_state'))['state']
                for invalid in ([], [cards[0], cards[0]]):
                    await call('play_cards', {'cards': invalid}, error='invalid_request')
            receipt = await call('play_cards', {'cards': cards, 'preset': 'default' if args.scenario == 'default' else 'full'})

            def results(value):
                detail = value['card_plays']
                assert detail['batch_id'] and len(detail['results']) == len(cards)
                for index, (row, expected) in enumerate(zip(detail['results'], cards, strict=True)):
                    assert row['index'] == index and row['card_id'] == expected['card_id']
                    assert row.get('target_id') == expected.get('target_id')
                    if args.scenario == 'default':
                        assert 'reason' not in row
                        assert ('target_id' in row) == ('target_id' in expected)
                    else: assert set(row) == {'index', 'card_id', 'target_id', 'status', 'reason'}
                return [row['status'] for row in detail['results']]

            statuses = results(receipt)
            if args.scenario == 'pending_reset':
                assert receipt['transition']['stop_reason'] == 'choice_required'
                assert statuses == ['played', 'resolving', 'queued', 'queued']
                return
            if args.scenario == 'autoplay':
                plays = [e for e in receipt['transition']['events'] if e['type'] == 'card_played' and e.get('autoplay')]
                assert len(plays) == 3 and all(e['card']['name'] == 'Shiv' for e in plays)
            choice = args.scenario in {'hand_exhaust', 'choose_one', 'immediate_choice', 'combat_pile'}
            assert receipt['transition']['complete'], receipt
            if choice:
                assert receipt['transition']['stop_reason'] == 'choice_required', receipt
                if args.scenario == 'hand_exhaust': assert statuses == ['resolving', 'not_played', 'not_played'], statuses
                if args.scenario == 'choose_one': assert statuses == ['played', 'resolving', 'queued', 'queued'], statuses
                if args.scenario == 'immediate_choice': assert statuses == ['resolving', 'not_submitted', 'not_submitted'], statuses
                if args.scenario == 'combat_pile': assert statuses == ['played', 'resolving', 'queued', 'queued'], statuses
                batch_id = receipt['card_plays']['batch_id']
                selection = (await call('inspect_selection'))['selection']
                rejected = await call('play_cards', {'cards': [cards[-1]]}, error='illegal_action')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                assert 'selection' in rejected['error']['message'].lower()
                receipt = await call('select_card', {'card_id': selection['cards'][0]['id']})
                if receipt['transition']['stop_reason'] == 'choice_required':
                    pending = (await call('inspect_selection'))['selection']
                    option = next((b for b in pending['options'] if b['id'] == 'confirm' and b['enabled']), None)
                    if option: receipt = await call('selection_option', {'option_id': 'confirm'})
                assert receipt['card_plays']['batch_id'] == batch_id
                statuses = results(receipt)
                assert receipt['transition']['stop_reason'] == 'player_ready', receipt
                if args.scenario == 'hand_exhaust': assert statuses == ['played', 'not_played', 'not_played'], statuses
                elif args.scenario == 'immediate_choice': assert statuses == ['played', 'not_submitted', 'not_submitted'], statuses
                else: assert all(s == 'played' for s in statuses), statuses
            elif args.scenario in {'victory', 'death', 'immediate_death'}:
                expected = {'victory': ['played', 'not_played', 'not_played'],
                    'death': ['played', 'played', 'not_played', 'not_played'],
                    'immediate_death': ['played', 'not_submitted', 'not_submitted']}
                assert statuses == expected[args.scenario], statuses
                assert receipt['transition']['stop_reason'] == ('combat_won' if args.scenario == 'victory' else 'combat_lost')
            elif args.scenario in {'native_reject', 'partial', 'zero', 'energy', 'stars', 'target', 'automatic_hand', 'random_exhaust'}:
                expected = {'native_reject': ['not_submitted', 'played', 'played'],
                    'partial': ['played', 'not_submitted', 'played'], 'zero': ['not_submitted', 'not_submitted'],
                    'energy': ['played', 'played', 'not_played', 'played'],
                    'stars': ['played', 'played', 'not_played', 'played'], 'target': ['played', 'not_played', 'played'],
                    'automatic_hand': ['played', 'not_played']}
                if args.scenario == 'random_exhaust': assert statuses[0] == 'played' and sorted(statuses[1:]) == ['not_played', 'played']
                else: assert statuses == expected[args.scenario], statuses
                assert receipt['transition']['stop_reason'] == 'player_ready'
            else:
                assert all(s == 'played' for s in statuses), statuses
                assert receipt['transition']['stop_reason'] == 'player_ready'
            if receipt['transition']['stop_reason'] == 'player_ready':
                after = await call('get_observation')
                assert 'card_plays' not in after
                # A completed batch is not replayed by the next independent action.
                next_turn = await call('end_turn')
                assert 'card_plays' not in next_turn


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=SCENARIOS)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
