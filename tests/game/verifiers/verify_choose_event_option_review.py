"""Verify event preflight reasons and direct continuation through native UI boundaries."""
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
    assert not args.report.exists(), 'Use a fresh evidence path.'
    args.report.parent.mkdir(parents=True, exist_ok=True)
    raw = Client(ipc_directory(), timeout=140)
    await asyncio.to_thread(ensure_run, raw)
    evidence = []

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    async def native(operation, token=None, arguments=None):
        result = await asyncio.to_thread(raw.call, operation, token, arguments=arguments,
                                        response_options={'include_divination_image': False})
        record({'native_operation': operation, 'result': result})
        return result

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
      async with ClientSession(read, write) as session:
        await session.initialize()

        async def call(tool, arguments=None, *, error=None, label=None):
            supplied = {'preset': 'full', **(arguments or {})}
            previous = set((raw.directory / 'responses').glob('*.json'))
            response = await session.call_tool(tool, supplied)
            result = response.structuredContent
            added = set((raw.directory / 'responses').glob('*.json')) - previous
            row = {'tool': tool, 'arguments': supplied, 'label': label, 'result': result,
                   'image_count': sum(part.type == 'image' for part in response.content)}
            if added:
                assert len(added) == 1, added
                original = json.loads(added.pop().read_text())
                row.update(native_error=original.get('error'), execution=original.get('execution'))
            record(row)
            assert result == json.loads(response.content[0].text), response
            assert response.isError == bool(error), result
            assert result.get('error', {}).get('code') == error, result
            return result

        async def reject(label, option_id, hint):
            before = (await native('get_state'))['state']
            result = await call('choose_event_option', {'option_id': option_id}, error='illegal_action', label=label)
            assert result['error']['recovery'] == 'choose_legal_action', result
            assert hint in result['error']['message'], result
            assert evidence[-1]['native_error']['action_submitted'] is False, evidence[-1]
            assert evidence[-1]['execution']['ui_interaction_started'] is False, evidence[-1]
            assert evidence[-1]['execution']['action_submission_observed'] is False, evidence[-1]
            after = (await native('get_state'))['state']
            assert before == after, 'Preflight rejection changed the captured state.'

        async def choose(option_id, label, reason='action_completed', preset='full'):
            result = await call('choose_event_option', {'option_id': option_id, 'preset': preset}, label=label)
            assert result['transition']['complete'] is True and result['transition']['stop_reason'] == reason, result
            assert not {'event', 'top_bar', 'player', 'rewards', 'divination'} & result.keys(), result
            assert evidence[-1]['image_count'] == 0, evidence[-1]
            return result

        await call('choose_event_option', {'option_id': 0}, error='observation_required', label='cold_choice')
        state = await call('get_observation')
        name = args.scenario
        if name == 'no_event':
            await reject('no_event', 0, 'No supported event')
            await call('end_turn', label='legal_turn_after_rejection')
            stale = await native('choose_event_option', 'obsolete', {'option_id': 0})
            assert stale['error']['code'] == 'stale_state', stale
            return
        initial = state['event']['options']
        assert ('choose_event_option' in state['available_actions']) == any(o['enabled'] for o in initial), state
        first = initial[0]['id']
        if name == 'basic':
            await call('choose_event_option', {'option_id': True}, error='invalid_request', label='local_bad_id')
            current = (await native('get_state'))['state']
            bad = await native('choose_event_option', current['snapshot_id'], {'option_id': first, 'extra': True})
            assert bad['error']['code'] == 'invalid_request' and bad['error']['action_submitted'] is False, bad
            assert not bad['execution']['ui_interaction_started'], bad
            stale = await native('choose_event_option', 'obsolete', {'option_id': first})
            assert stale['error']['code'] == 'stale_state' and 'action_submitted' not in stale['error'], stale
            await call('inspect_map')
            await reject('map_covered', first, 'close_map')
            await call('close_map')
            await call('inspect_deck')
            await reject('deck_covered', first, 'close_card_view')
            await call('close_card_view')
            await reject('missing_id', 2147483647, 'inspect_event')
            result = await choose(first, 'next_page_after_rejection')
            assert [e['type'] for e in result['transition']['events']] == ['max_hp_changed', 'hp_changed', 'hp_changed'], result
            state = await call('get_observation', label='next_page_observation')
            await reject('old_page_id', first, 'inspect_event')
            await choose(state['event']['options'][-1]['id'], 'finish_default', preset='default')
            await reject('finished_event', first, 'proceed')
            await call('proceed', label='proceed_after_rejection')
            return
        if name == 'locked':
            locked = next(o for o in initial if not o['enabled'])
            enabled = next(o for o in initial if o['enabled'])
            await reject('locked', locked['id'], 'locked')
            await choose(enabled['id'], 'valid_after_locked', reason='choice_required')
            return
        index = {'upgrade': 1, 'reward': 1, 'trial': 1, 'dense_choice': 1, 'combat': 1}.get(name, 0)
        expected = 'choice_required' if name == 'upgrade' else 'run_lost' if name == 'death' else 'action_completed'
        result = await choose(initial[index]['id'], 'first_choice', reason=expected)
        state = await call('get_observation', label='after_choice')
        if name == 'trial':
            await choose(state['event']['options'][1]['id'], 'confirmation')
            await reject('confirmation_covered', first, 'respond_to_confirmation')
            await call('respond_to_confirmation', {'option': 'cancel'}, label='cancel_after_rejection')
        elif name in {'dense_choice', 'combat'}:
            await choose(state['event']['options'][0]['id'], 'enter_combat_choice' if name == 'dense_choice' else 'enter_combat',
                         reason='choice_required' if name == 'dense_choice' else 'player_ready')
        elif name == 'upgrade':
            await reject('selection_covered', first, 'inspect_selection')
            await call('select_card', {'card_id': state['selection']['cards'][0]['id']}, label='select_after_rejection')
            await call('selection_option', {'option_id': 'confirm'})
        elif name == 'reward':
            await reject('rewards_covered', first, 'inspect_rewards')
            await call('claim_reward', {'reward_id': state['rewards']['items'][0]['id']}, label='claim_after_rejection')
        elif name == 'crystal':
            await reject('divination_covered', first, 'inspect_event')
            await call('set_divination_tool', {'tool': 'small'}, label='tool_after_rejection')
        elif name == 'rescue':
            assert any(e['type'] == 'potion_used' and e['potion']['name'] == 'Fairy in a Bottle'
                       for e in result['transition']['events']), result
        elif name == 'potions':
            await reject('potion_rewards_covered', first, 'inspect_rewards')
            await call('discard_potion', {'potion_slot': 0}, label='discard_after_rejection')
            await call('claim_reward', {'reward_id': state['rewards']['items'][0]['id']}, label='claim_after_discard')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
