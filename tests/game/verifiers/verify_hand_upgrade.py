from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
from tests.game.support.verification_actions import observe_after_action
from sts2_mcp.output.available_tools import GAME_ACTIONS
import argparse
import asyncio
import json
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from sts2_mcp.roundtrip_client import Client


async def verify(args):
    root = ROOT
    report = args.report.resolve()
    report.parent.mkdir(parents=True, exist_ok=True)
    config = report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(report.parent / report.stem)}}))
    raw = Client(root / '.tmp/roundtrip/ipc')
    observed = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while observed['state']['scene'] == 'unrecognized' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        observed = await asyncio.to_thread(raw.call, 'get_state')
    assert observed['state']['scene'] == 'main_menu', 'Requires a fresh isolated game instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', observed['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, *, error=None):
                response = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = response.structuredContent
                assert data == json.loads(response.content[0].text), response
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                if error:
                    assert data.get('error', {}).get('code') == error, data
                else:
                    assert 'error' not in data, data
                return data

            async def action(name, arguments, **kwargs):
                await call('get_observation')
                return await call(name, arguments, **kwargs)

            async def capture(name):
                await call('capture_screenshot', {'filename': name + '.png'})

            initial = await call('get_observation')
            armaments = next(card for card in initial['player']['hand'] if card['name'] == 'Armaments')
            played = await observe_after_action(call, await call('play_card', {'card_id': armaments['id']}))
            await capture('initial')
            selection = played['selection']
            assert selection['status'] == 'visible' and selection['type'] == 'hand_upgrade', played
            assert selection['can_view_battlefield'] and selection['selected_ids'] == [], selection
            assert selection['upgrade_preview'] is None, selection
            assert not any(option['id'] == 'confirm' and option['enabled'] for option in selection['options']), selection
            assert played['transition']['stop_reason'] == 'choice_required' and played['transition']['complete'], played
            await action('selection_option', {'option_id': 'confirm'}, error='illegal_action')
            await action('select_card', {'card_id': armaments['id']}, error='illegal_action')
            detail = await call('inspect_selection')
            cards = detail['selection']['cards']
            assert len(cards) >= 2 and all(card['name'] in {'Defend', 'Strike'} for card in cards), detail
            first, other = cards[:2]

            async def preview(card):
                selected = await observe_after_action(call, await action('select_card', {'card_id': card['id']}))
                assert selected['transition']['stop_reason'] == 'choice_required' and selected['transition']['complete'], selected
                current = selected['selection']
                assert current['selected_ids'] == [card['id']], current
                assert len(current['cards']) == len(cards) and len({c['id'] for c in current['cards']}) == len(cards), current
                shown = current['upgrade_preview']
                assert shown['before']['id'] == shown['after']['id'] == card['id'], shown
                assert shown['before']['name'] == card['name'] and shown['after']['name'] == card['name'] + '+', shown
                expected = ('Gain 5 Block.', 'Gain 8 Block.') if card['name'] == 'Defend' else ('Deal 6 damage.', 'Deal 9 damage.')
                assert (shown['before']['description'], shown['after']['description']) == expected, shown
                assert next(o for o in current['options'] if o['id'] == 'confirm')['enabled'], current
                return selected

            await preview(first)
            await capture('preview')
            detail = await call('inspect_selection')
            assert detail['selection']['upgrade_preview']['after']['description'], detail
            peek = await call('set_selection_view', {'view': 'battlefield'})
            assert peek['selection']['status'] == 'battlefield' and peek['selection']['cards'] is None, peek
            assert peek['selection']['upgrade_preview'] is None and not set(peek['available_actions']) & GAME_ACTIONS, peek
            await capture('battlefield')
            hand = await call('inspect_hand')
            assert all(card['name'] == candidate['name'] for candidate in cards
                       for card in hand['hand'] if card['id'] == candidate['id']), hand
            await action('play_card', {'card_id': other['id']}, error='illegal_action')
            await action('select_card', {'card_id': first['id']}, error='illegal_action')
            await action('selection_option', {'option_id': 'confirm'}, error='illegal_action')
            await call('inspect_selection', error='illegal_action')
            await call('inspect_deck')
            covered = await call('get_observation')
            assert covered['selection']['status'] == 'covered' and covered['selection']['upgrade_preview'] is None, covered
            await call('close_card_view')
            restored = await call('set_selection_view', {'view': 'selection'})
            assert restored['selection']['selected_ids'] == [first['id']], restored
            await preview(other)
            await capture('replaced')
            canceled = await observe_after_action(call, await action('select_card', {'card_id': other['id']}))
            assert canceled['selection']['selected_ids'] == [] and canceled['selection']['upgrade_preview'] is None, canceled
            assert not any(o['id'] == 'confirm' and o['enabled'] for o in canceled['selection']['options']), canceled
            await preview(first)
            finished = await observe_after_action(call, await action('selection_option', {'option_id': 'confirm'}))
            assert finished['transition']['stop_reason'] == 'player_ready' and finished['transition']['complete'], finished
            assert finished['selection'] is None, finished
            await capture('confirmed')
            hand = await call('inspect_hand')
            upgraded = next(card for card in hand['hand'] if card['id'] == first['id'])
            assert upgraded['name'] == first['name'] + '+', hand
            await call('get_observation')
            targeted = await call('inspect_targets', {'card_id': upgraded['id']})
            assert targeted['card'] == {'id': upgraded['id'], 'name': upgraded['name']}, targeted
            assert all(card['name'] == other['name'] for card in hand['hand'] if card['id'] == other['id']), hand
    print('PASS: native hand upgrade candidates, preview, replace, deselect, eye, cover, confirm and stable card IDs.')


def main():
    parser = argparse.ArgumentParser(description='验证隔离图形实例的武装升级选择，需 --play-scenario armaments、armaments_free 或 armaments_filtered。')
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
