"""Audit native potion discard receipts, slot identity and rejection recovery."""
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


SCENARIOS = ('basic', 'default', 'automatic', 'fruit', 'blocked', 'replace', 'covered',
             'display', 'skill', 'noncombat_event', 'noncombat_rest', 'noncombat_shop',
             'noncombat_map', 'noncombat_reward', 'merchant_inventory')


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
                if error:
                    assert response.isError and result['error']['code'] == error, result
                else:
                    assert not response.isError and 'error' not in result, result
                return result

            await call('discard_potion', {'potion_slot': 0}, error='observation_required')
            before = await call('get_observation')
            scenario = args.scenario
            if scenario == 'noncombat_map':
                deadline = time.monotonic() + 8
                while 'inspect_map' not in before['available_actions']:
                    assert time.monotonic() < deadline, 'Fixture map did not become ready.'
                    await asyncio.sleep(.1)
                    before = (await native('get_state'))['state']
                before = await call('get_observation')

            async def unchanged_rejection(arguments, message):
                prior = (await native('get_state'))['state']
                result = await call('discard_potion', arguments, error='illegal_action')
                assert message in result['error']['message'], result
                assert result['error']['recovery'] == 'choose_legal_action', result
                assert (await native('get_state'))['state'] == prior
                return result

            async def discard(slot, preset='full', stop=None):
                prior = (await native('get_state'))['state']
                potion = prior['top_bar']['potion_slots'][slot]
                result = await call('discard_potion', {'potion_slot': slot, 'preset': preset})
                transition = result['transition']
                assert transition['complete'], result
                expected = stop or ('player_ready' if prior['scene'] == 'combat' else 'action_completed')
                assert transition['stop_reason'] == expected, result
                removed = [e['potion'] for e in transition['events'] if e['type'] == 'potion_discarded']
                assert removed == [{'slot_index': slot, 'name': potion['name']}], result
                assert not any(e['type'] == 'potion_used' for e in transition['events']), result
                after = (await native('get_state'))['state']
                for index, old in enumerate(prior['top_bar']['potion_slots']):
                    assert after['top_bar']['potion_slots'][index] == (None if index == slot else old)
                for key in ('hp', 'max_hp', 'gold'):
                    assert after['top_bar'][key] == prior['top_bar'][key], (prior, after)
                return result

            if scenario == 'basic':
                for invalid in ({}, {'potion_slot': True}, {'potion_slot': -1},
                        {'potion_slot': 0.0}, {'potion_slot': '0'}, {'potion_slot': None},
                        {'potion_slot': 2147483648}, {'potion_slot': 0, 'target_id': 1},
                        {'potion_slot': 0, 'preset': 'summary'}, {'potion_slot': 0, 'unknown': True}):
                    await call('discard_potion', invalid, error='invalid_request')
                await unchanged_rejection({'potion_slot': 99}, 'out of range')
                selected = await call('inspect_potions', {'slot_indices': [1]})
                assert selected['slot_indices'] == [1]
                await discard(1)
                await unchanged_rejection({'potion_slot': 1}, 'empty')
                await discard(0)
                await discard(2)
                after = await call('get_observation')
                assert 'discard_potion' not in after['available_actions'], after
                await call('end_turn')
            elif scenario == 'replace':
                old = (await native('get_state'))['state']['snapshot_id']
                assert (await native('replace_test_potion'))['ok']
                stale = await native('discard_potion', {'potion_slot': 0}, old)
                assert not stale['ok'] and stale['error']['code'] == 'stale_state', stale
                await call('discard_potion', {'potion_slot': 0}, error='stale_state')
                await call('end_turn', error='observation_required')
                await call('get_observation')
                await discard(0)
            elif scenario == 'blocked':
                assert 'discard_potion' not in before['available_actions'], before
                await unchanged_rejection({'potion_slot': 0}, 'cannot be removed')
                await call('end_turn')
            elif scenario == 'covered':
                defend = next(c for c in before['player']['hand'] if c['name'] == 'Defend')
                await call('play_card', {'card_id': defend['id']})
                for opener, closer, arguments, view in (
                        ('inspect_deck', 'close_card_view', {}, 'deck'),
                        ('inspect_pile', 'close_card_view', {'pile': 'discard'}, 'discard_pile'),
                        ('inspect_map', 'close_map', {}, 'map')):
                    await call(opener, arguments)
                    observed = await call('get_observation')
                    assert observed['screen']['view'] == view, observed
                    assert 'discard_potion' not in observed['available_actions'], observed
                    await unchanged_rejection({'potion_slot': 0}, 'Close')
                    if closer in observed['available_actions']:
                        await call(closer)
                    else:
                        # The debug combat has no visited map node; native opening can
                        # become the mandatory first-node map, with no Back button.
                        assert opener == 'inspect_map', observed
            elif scenario == 'display':
                for mode in ('disabled', 'no_hover', 'hidden', 'offscreen'):
                    assert (await native('set_test_potion_display', {'mode': mode, 'index': 2}))['ok']
                    try:
                        await call('get_observation')
                        if mode != 'offscreen':
                            await unchanged_rejection({'potion_slot': 2},
                                'hidden' if mode == 'hidden' else 'interacted with')
                        # A different slot remains operable even if the entire belt is unreadable.
                        if mode == 'hidden':
                            result = await call('discard_potion', {'potion_slot': 0})
                            assert result['transition']['events'][0]['potion']['slot_index'] == 0, result
                        elif mode == 'offscreen':
                            await discard(2)
                    finally:
                        assert (await native('set_test_potion_display', {'mode': 'normal'}))['ok']
                await call('get_observation')
                await discard(1)
            elif scenario == 'skill':
                result = await call('use_potion', {'potion_slot': 0})
                assert result['transition']['stop_reason'] == 'choice_required', result
                selection = await call('inspect_selection')
                await unchanged_rejection({'potion_slot': 1}, 'selection')
                chosen = await call('select_card', {'card_id': selection['selection']['cards'][0]['id']})
                assert chosen['transition']['stop_reason'] == 'player_ready', chosen
                await discard(1)
            elif scenario == 'noncombat_reward':
                reward = (await call('inspect_rewards'))['rewards']['items'][0]['id']
                await call('claim_reward', {'reward_id': reward})
                assert (await call('get_observation'))['top_bar']['potion_slots'] == before['top_bar']['potion_slots']
                await discard(1)
                claimed = await call('claim_reward', {'reward_id': reward})
                assert any(e['type'] == 'potion_obtained' for e in claimed['transition']['events']), claimed
                after = await call('get_observation')
                if after['scene'] == 'rewards':
                    await call('proceed')
                else:
                    # Claiming the last item can close this native reward screen.
                    assert after['scene'] == 'event', after
            else:
                slot = 2 if scenario == 'automatic' else 0
                await discard(slot, preset='default' if scenario == 'default' else 'full')
                if scenario == 'noncombat_map':
                    await discard(1)
                    await discard(2)
                else:
                    await discard(1)
    print('PASS discard_potion review:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
