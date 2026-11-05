"""Audit native eye views, public observations and current rejection recovery."""
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


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable,
        args=[str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None, interacted=None):
                files = set((raw.directory / 'responses').glob('*.json'))
                arguments = {'preset': 'full', **(arguments or {})}
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                record({'tool': tool, 'arguments': arguments, 'label': label, 'result': result})
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                if interacted is not None:
                    added = set((raw.directory / 'responses').glob('*.json')) - files
                    assert len(added) == 1, added
                    native = json.loads(added.pop().read_text())
                    record({'label': label, 'native_response': native})
                    assert native['execution']['ui_interaction_started'] is interacted, native
                return result

            async def view(value, label, interacted):
                result = await call('set_selection_view', {'view': value}, label=label, interacted=interacted)
                assert 'transition' not in result, result
                assert result['selection']['status'] == ('battlefield' if value == 'battlefield' else 'visible'), result
                if value == 'battlefield':
                    assert result['selection']['cards'] is None and result['selection']['selected_ids'] is None, result
                    assert not {'play_card', 'play_cards', 'end_turn', 'select_card', 'selection_option'} & set(result['available_actions']), result
                return result

            async def rejected(label):
                result = await call('set_selection_view', {'view': 'selection'}, error='illegal_action',
                                    label=label, interacted=False)
                assert result['error']['message'] == 'The requested action is unavailable.', result
                assert result['error']['recovery'] == 'get_observation', result
                return result

            if args.scenario == 'no_selection':
                await rejected('without_permission')
                await call('end_turn', error='observation_required', label='still_without_permission')
                await call('get_observation')
                await call('set_selection_view', {'view': 'invalid'}, error='invalid_request', label='malformed')
                await call('end_turn', label='after_local_rejection')
                await call('get_observation')
                await rejected('no_selection')
                await call('end_turn', error='observation_required', label='after_uninteracted_rejection')
                return

            if args.scenario != 'overlay':
                state = await call('get_observation', label='initial')
            if args.scenario == 'hand_upgrade':
                card = next(c for c in state['player']['hand'] if c['name'] == 'Armaments')
                await call('play_card', {'card_id': card['id']})
            elif args.scenario == 'noncombat':
                await call('choose_rest_option', {'option_id': 'SMITH'})
            elif args.scenario == 'results':
                deadline = time.monotonic() + 15
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline, state
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                option = next(o for o in state['ancient']['options'] if o['enabled'])
                await call('choose_ancient_option', {'option_id': option['id']})

            if args.scenario == 'overlay':
                # This view tool can supply the first valid observation itself.
                shown = await view('battlefield', 'without_prior_read', True)
                original = None
            else:
                original = (await call('inspect_selection', label='candidates'))['selection']
                if args.scenario in {'noncombat', 'results'}:
                    assert not original['can_view_battlefield'], original
                    await rejected('no_native_eye')
                    tool, arguments = ('selection_option', {'option_id': 'confirm'}) if args.scenario == 'results' else (
                        'select_card', {'card_id': original['cards'][0]['id']})
                    await call(tool, arguments, error='observation_required', label='legal_action_blocked')
                    await call('inspect_selection')
                    await call(tool, arguments, label='after_refresh')
                    if args.scenario == 'noncombat':
                        await call('selection_option', {'option_id': 'confirm'})
                    return
                if args.scenario in {'grid', 'hand_upgrade'}:
                    await call('select_card', {'card_id': original['cards'][0]['id']})
                # Compare the same static format on both sides; inspection expands hidden hand text.
                original = (await call('get_observation', label='before_view'))['selection']
                shown = await view('battlefield', 'battlefield', True)

            if args.scenario in {'covered_deck', 'covered_map'}:
                await call('inspect_deck' if args.scenario == 'covered_deck' else 'inspect_map')
                await rejected('covered')
                card_id = original['cards'][0]['id']
                await call('select_card', {'card_id': card_id}, error='observation_required', label='permission_lost')
                await call('close_card_view' if args.scenario == 'covered_deck' else 'close_map')
            else:
                repeated = await view('battlefield', 'battlefield_again', False)
                assert repeated == shown, (shown, repeated)

            restored = await view('selection', 'selection', True)
            assert 'set_selection_view' in restored['available_actions'], restored
            repeated = await view('selection', 'selection_again', False)
            assert repeated == restored, (restored, repeated)
            current = restored['selection']
            if original is not None:
                for key in ('selected_ids', 'cards', 'upgrade_preview'):
                    assert current.get(key) == original.get(key), (key, original, current)
            if args.scenario in {'grid', 'hand_upgrade'}:
                assert current['selected_ids'], current
                if args.scenario == 'grid':
                    await call('select_card', {'card_id': current['cards'][1]['id']})
                await call('selection_option', {'option_id': 'confirm'}, label='continue_without_read')
            else:
                await call('select_card', {'card_id': current['cards'][0]['id']}, label='continue_without_read')

    print(json.dumps({'scenario': args.scenario, 'records': len(evidence)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
