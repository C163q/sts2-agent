from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
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
    before = await asyncio.to_thread(raw.call, 'get_state')
    deadline = time.monotonic() + 30
    while before['state']['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        await asyncio.sleep(.1)
        before = await asyncio.to_thread(raw.call, 'get_state')
    assert before['state']['scene'] == 'main_menu', 'Requires a fresh isolated instance.'
    created = await asyncio.to_thread(raw.call, 'start_test_combat', before['state']['snapshot_id'])
    assert created['ok'], created
    evidence = []
    params = StdioServerParameters(command=str(root / '.tmp/mcp-venv/bin/python'), args=[
        str(root / 'scripts/mcp_server.py'), '--ipc-dir', str(root / '.tmp/roundtrip/ipc'), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                response = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = response.structuredContent
                assert data == json.loads(response.content[0].text)
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert 'error' not in data, data
                return data

            observed = await call('get_observation')
            await call('capture_screenshot', {'filename': 'hand.png'})
            cards = observed['player']['hand']
            expected = {card['id']: card['name'] for card in cards}
            assert list(expected.values()) == ['True Grit+', 'Strike+', 'Defend+', 'Strike', 'Defend'], cards
            inspected = await call('inspect_hand')
            assert {card['id']: card['name'] for card in inspected['hand']} == expected, inspected
            for card in cards:
                targeted = await call('inspect_targets', {'card_id': card['id']})
                assert targeted['card'] == {'id': card['id'], 'name': card['name']}, targeted

            def check_events(result):
                assert result['transition']['complete'], result
                for event in result['transition']['events']:
                    ref = event.get('card')
                    if ref and ref['id'] in expected:
                        assert ref['name'] == expected[ref['id']], event

            await call('get_observation')
            grit = await call('play_card', {'card_id': cards[0]['id']})
            check_events(grit)
            assert grit['transition']['stop_reason'] == 'choice_required', grit
            assert any(e['type'] == 'card_played' and e['card']['name'] == 'True Grit+' for e in grit['transition']['events']), grit
            candidates = await call('inspect_selection')
            assert all(card['name'] == expected[card['id']] for card in candidates['selection']['cards']), candidates
            await call('get_observation')
            selected = await call('select_card', {'card_id': cards[4]['id']})
            if (selected.get('selection') or {}).get('status') == 'visible':
                await call('get_observation')
                selected = await call('selection_option', {'option_id': 'confirm'})
            check_events(selected)
            assert selected['transition']['stop_reason'] == 'player_ready', selected
            assert any(e['type'] == 'card_exhausted' and e['card']['name'] == 'Defend' for e in selected['transition']['events']), selected
            await call('get_observation')
            targets = await call('inspect_targets', {'card_id': cards[1]['id']})
            strike = await call('play_card', {'card_id': cards[1]['id'], 'target_id': targets['targets'][0]['id']})
            check_events(strike)
            assert any(e['type'] == 'card_played' and e['card']['name'] == 'Strike+' for e in strike['transition']['events']), strike
            damage = [e for e in strike['transition']['events'] if e['type'] == 'damage']
            assert damage and all(e['source'] == {'kind': 'card', 'name': 'Strike+'} for e in damage), strike
            await call('get_observation')
            ended = await call('end_turn')
            check_events(ended)
            assert any(e['type'] == 'card_discarded' and e['card']['name'] == 'Defend+' for e in ended['transition']['events']), ended
            await call('capture_screenshot', {'filename': 'after-turn.png'})
    print('PASS: upgraded and base names agree across observation, hand, targets, selection and gameplay events.')


def main():
    parser = argparse.ArgumentParser(description='验证隔离图形实例的卡牌显示名称，需 --play-scenario card_names。')
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
