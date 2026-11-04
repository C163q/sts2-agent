"""Capture current potion actions and verify rejection and choice boundaries."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory

SCENARIOS = ('basic', 'default', 'aoe', 'victory', 'death', 'fairy_rescue', 'cancel',
    'skill', 'attack', 'power', 'colorless', 'memories', 'gamblers', 'fruit_combat',
    'noncombat_event', 'noncombat_rest', 'noncombat_shop', 'noncombat_map', 'noncombat_reward',
    'merchant', 'merchant_inventory', 'merchant_map', 'blocked', 'entropic', 'replace',
    'unhittable', 'covered', 'slot_boundary', 'journal_boundary', 'fake_merchant')


async def verify(args):
    raw = Client(ipc_directory(), timeout=75)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    async def native(operation, arguments=None, expected=None):
        response = await asyncio.to_thread(raw.call, operation, expected, arguments=arguments)
        record({'native_operation': operation, 'arguments': arguments, 'response': response})
        return response

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
                else: assert not response.isError and 'error' not in result, result
                return result

            if args.scenario == 'fake_merchant':
                await call('use_potion', {'potion_slot': 0, 'target_id': 'merchant'}, error='observation_required')
            before = await call('get_observation')
            scenario = args.scenario

            if scenario == 'journal_boundary':
                changed = await native('set_test_potion_display', {'mode': 'disabled', 'index': 1})
                assert changed['ok'], changed
                try:
                    observed = await call('get_observation')
                    assert observed['player']['hp'] == 1
                    assert observed['top_bar']['potion_slots'][2]['name'] == 'Fairy in a Bottle'
                    result = await call('end_turn')
                    assert result['transition']['stop_reason'] == 'player_ready', result
                    after = await call('get_observation')
                    assert after['player']['hp'] > 0 and after['top_bar']['potion_slots'][2] is None, after
                    # Current defect: an unrelated disabled slot prevents remembering the fairy.
                    assert not any(e['type'] == 'potion_used' for e in result['transition']['events']), result
                finally:
                    restored = await native('set_test_potion_display', {'mode': 'normal'})
                    assert restored['ok'], restored
                return

            if scenario == 'fake_merchant':
                targets = await call('inspect_targets', {'potion_slot': 0})
                assert targets['targets'][0]['id'] == 'merchant', targets
                result = await call('use_potion', {'potion_slot': 0, 'target_id': 'merchant'})
                assert result['scene'] == 'combat' and result['transition']['stop_reason'] == 'player_ready', result
                # Entry from outside combat has no previous combat namespace to separate.
                assert not any(e['type'] == 'combat_started' for e in result['transition']['events']), result
                assert any(e['type'] == 'card_drawn' for e in result['transition']['events']), result
                assert sum(e['type'] == 'potion_used' for e in result['transition']['events']) == 1, result
                return

            async def query(slot=0):
                return await call('inspect_targets', {'potion_slot': slot})

            async def use(slot=0, preset='full'):
                q = await query(slot)
                assert q['usable'], q
                return await call('use_potion', {'potion_slot': slot, 'preset': preset,
                    **({'target_id': q['targets'][0]['id']} if q['requires_target'] else {})})

            if scenario == 'basic':
                await query()
                for invalid in ({'potion_slot': True}, {'potion_slot': -1},
                        {'potion_slot': 0, 'target_id': None}, {'potion_slot': 0, 'unknown': True},
                        {'potion_slot': 0, 'preset': 'summary'}):
                    await call('use_potion', invalid, error='invalid_request')
                for invalid in ({'potion_slot': 99}, {'potion_slot': 0},
                        {'potion_slot': 0, 'target_id': 4294967295},
                        {'potion_slot': 1, 'target_id': before['enemies'][0]['id']}, {'potion_slot': 2}):
                    await call('get_observation')
                    prior = (await native('get_state'))['state']
                    rejected = await call('use_potion', invalid, error='illegal_action')
                    assert rejected['error']['message'] == 'The requested action is unavailable.', rejected
                    assert (await native('get_state'))['state'] == prior
                    await call('end_turn', error='observation_required')
                fire = await use()
                assert fire['transition']['stop_reason'] == 'player_ready', fire
                assert any(e['type'] == 'damage' and e['source']['kind'] == 'potion'
                    for e in fire['transition']['events']), fire
                # A successful action receipt authorizes the next potion without a new read.
                block = await call('use_potion', {'potion_slot': 1})
                assert any(e['type'] == 'block_changed' for e in block['transition']['events']), block
                await query(2)
                await call('use_potion', {'potion_slot': 2}, error='illegal_action')
                return
            if scenario in {'covered', 'slot_boundary'}:
                if scenario == 'covered':
                    # The basic fixture has empty piles; make a real discard page available.
                    defend = next(card for card in before['player']['hand'] if card['name'] == 'Defend')
                    await call('play_card', {'card_id': defend['id']})
                    assert (await call('get_observation'))['player']['discard_count'] > 0
                    for opener, closer, params in (('inspect_deck', 'close_card_view', {}),
                            ('inspect_pile', 'close_card_view', {'pile': 'discard'}), ('inspect_map', 'close_map', {})):
                        await call(opener, params)
                        covered = await call('get_observation')
                        expected_view = {'inspect_deck': 'deck', 'inspect_pile': 'discard_pile', 'inspect_map': 'map'}[opener]
                        assert covered['screen'].get('view') == expected_view, covered
                        await call('use_potion', {'potion_slot': 1}, error='illegal_action')
                        await call('end_turn', error='observation_required')
                        if closer in covered['available_actions']:
                            # Closing a view does not require gameplay action permission.
                            await call(closer)
                else:
                    filtered = await call('inspect_potions', {'slot_indices': [1]})
                    assert filtered['slot_indices'] == [1]
                    assert filtered['potion_slots'][0]['name'] == 'Block Potion'
                    prior = (await native('get_state'))['state']
                    refused = await native('use_potion', {'potion_slot': 99}, prior['snapshot_id'])
                    assert not refused['ok'] and refused['error']['code'] == 'illegal_action', refused
                    assert refused['execution'] == {'ui_interaction_started': False,
                        'action_submission_observed': False, 'state_captured': True}, refused
                    assert 'action_submitted' not in refused['error'] and 'public_message' not in refused['error']
                    for mode in ('offscreen', 'disabled', 'no_hover'):
                        changed = await native('set_test_potion_display', {'mode': mode, 'index': 2})
                        assert changed['ok'], changed
                        try:
                            observed = await call('get_observation')
                            assert len(observed['top_bar']['potion_slots']) == 3
                            assert not {'use_potion', 'discard_potion'} & set(observed['available_actions'])
                            # An untouched slot is rejected because the entire belt is gated.
                            await call('inspect_targets', {'potion_slot': 1}, error='illegal_action')
                            await call('use_potion', {'potion_slot': 1}, error='illegal_action')
                        finally:
                            restored = await native('set_test_potion_display', {'mode': 'normal'})
                            assert restored['ok'], restored
                    # Visible enemy IDs work without a successful potion target inspection.
                    await call('get_observation')
                    direct = await call('use_potion', {'potion_slot': 0, 'target_id': before['enemies'][0]['id']})
                    assert direct['transition']['stop_reason'] == 'player_ready', direct
                return
            if scenario == 'replace':
                old = (await native('get_state'))['state']['snapshot_id']
                changed = await native('replace_test_potion')
                assert changed['ok'], changed
                current = (await native('get_state'))['state']
                assert current['snapshot_id'] != old
                stale = await native('use_potion', {'potion_slot': 0, 'target_id': before['enemies'][0]['id']}, old)
                assert not stale['ok'] and stale['error']['code'] == 'stale_state', stale
                await call('use_potion', {'potion_slot': 1}, error='stale_state')
                await call('use_potion', {'potion_slot': 1}, error='observation_required')
                return
            if scenario in {'blocked', 'merchant_inventory', 'merchant_map'}:
                q = await query()
                assert not q['usable'] and q['reason'], q
                await call('use_potion', {'potion_slot': 0,
                    **({'target_id': 'merchant'} if scenario != 'blocked' else {})}, error='illegal_action')
                return
            if scenario == 'unhittable':
                q = await query()
                assert all(t['id'] != before['enemies'][0]['id'] for t in q['targets']), q
                await call('use_potion', {'potion_slot': 0, 'target_id': before['enemies'][0]['id']}, error='illegal_action')
            result = await use(preset='default' if scenario == 'default' else 'full')
            expected = {'victory': 'combat_won', 'death': 'combat_lost', 'cancel': 'action_canceled'}
            if scenario in {'skill', 'attack', 'power', 'colorless', 'memories', 'gamblers'}:
                expected[scenario] = 'choice_required'
            if scenario.startswith('noncombat') or scenario == 'merchant':
                expected[scenario] = 'action_completed'
            assert result['transition']['stop_reason'] == expected.get(scenario, 'player_ready'), result
            assert result['transition']['complete'], result
            if scenario == 'cancel':
                assert not any(e['type'] == 'potion_used' for e in result['transition']['events']), result
                await call('use_potion', {'potion_slot': 1}, error='observation_required')
                return
            assert any(e['type'] == 'potion_used' and e['potion']['slot_index'] == 0
                for e in result['transition']['events']), result
            if scenario == 'merchant':
                after = await call('get_observation')
                assert after['top_bar']['gold'] == before['top_bar']['gold'] + 100
            elif scenario == 'entropic':
                after = await call('get_observation')
                assert all(after['top_bar']['potion_slots']), after
            elif scenario == 'fairy_rescue':
                slots = {e['potion']['slot_index'] for e in result['transition']['events'] if e['type'] == 'potion_used'}
                assert slots == {0, 2}, result
            elif scenario.startswith('noncombat') or scenario == 'fruit_combat':
                after = await call('get_observation')
                assert after['top_bar']['max_hp'] == before['top_bar']['max_hp'] + 5
                await use(1)
                if scenario.startswith('noncombat'):
                    q = await query(2)
                    assert not q['usable'] and q['discardable'], q
                    await call('use_potion', {'potion_slot': 2}, error='illegal_action')
                if scenario == 'noncombat_reward':
                    # Finish the native reward task before the suite resets this run.
                    await call('get_observation')
                    await call('proceed')
            elif expected.get(scenario) == 'choice_required':
                selection = await call('inspect_selection')
                chosen = selection['selection']['cards'][0]['id']
                await call('use_potion', {'potion_slot': 1}, error='illegal_action')
                await call('select_card', {'card_id': chosen}, error='observation_required')
                await call('inspect_selection')
                selected = await call('select_card', {'card_id': chosen})
                if selected['transition']['stop_reason'] == 'choice_required':
                    pending = await call('inspect_selection')
                    if any(b['id'] == 'confirm' and b['enabled'] for b in pending['selection']['options']):
                        selected = await call('selection_option', {'option_id': 'confirm'})
                assert selected['transition']['stop_reason'] == 'player_ready', selected
            if scenario in {'victory', 'death'}:
                deadline, quiet, previous = time.monotonic() + 12, time.monotonic(), None
                while time.monotonic() < deadline:
                    current = (await native('get_state'))['state']['snapshot_id']
                    if current != previous: previous, quiet = current, time.monotonic()
                    if time.monotonic() - quiet >= 2: break
                    await asyncio.sleep(.1)
                else: raise AssertionError('Terminal UI did not settle before cleanup.')
    print('PASS use_potion current behavior:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
