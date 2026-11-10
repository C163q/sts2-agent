"""Exercise revised native card/relic effects and receipt-derived permissions."""
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
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/mcp_server.py'),
        '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, **arguments):
                reply = await session.call_tool(tool, {'preset': 'full', **arguments})
                result = reply.structuredContent
                record({'tool': tool, 'arguments': arguments, 'result': result})
                assert not reply.isError and result == json.loads(reply.content[0].text), result
                if 'transition' in result:
                    assert result['transition']['complete'], result
                return result

            async def stable():
                # Diagnostic reads leave the previous MCP permission intact.
                tokens = []
                for _ in range(8):
                    response = await asyncio.to_thread(raw.call, 'get_state')
                    assert response['ok'], response
                    tokens.append(response['state']['snapshot_id'])
                    await asyncio.sleep(.15)
                record({'stable_tokens': tokens})
                assert len(set(tokens)) == 1, tokens

            initial = await call('get_observation')
            if args.scenario == 'toasty_mittens':
                ended = await call('end_turn')
                assert ended['transition']['stop_reason'] == 'choice_required', ended
                selection = (await call('inspect_selection'))['selection']
                assert selection['type'] == 'hand' and selection['min_select'] == selection['max_select'] == 1, selection
                chosen = selection['cards'][0]
                result = await call('select_card', card_id=chosen['id'])
                if result['transition']['stop_reason'] == 'choice_required':
                    result = await call('selection_option', option_id='confirm')
                assert result['transition']['stop_reason'] == 'player_ready', result
                assert any(e['type'] == 'card_exhausted' and e['card']['id'] == chosen['id']
                           for e in result['transition']['events']), result
                assert any(e['type'] == 'power_changed' and e.get('name') == 'Strength'
                           for e in result['transition']['events']), result
            else:
                name = {'outbreak': 'Outbreak', 'well_laid_plans': 'Well-Laid Plans', 'expertise': 'Expertise'}[args.scenario]
                hand = (await call('inspect_hand'))['hand']
                subject = next(c for c in hand if c['name'] == name)
                result = await call('play_card', card_id=subject['id'])
                assert result['transition']['stop_reason'] == 'player_ready', result
                if args.scenario == 'outbreak':
                    damage = [e for e in result['transition']['events'] if e['type'] == 'damage']
                    assert {e['target']['id'] for e in damage} == {e['id'] for e in initial['enemies']}, result
                    assert all(e['hp_loss'] == 9 and e['blocked'] == 0 for e in damage), damage
                    observed = await call('get_observation')
                    for enemy in observed['enemies']:
                        before = next(e for e in initial['enemies'] if e['id'] == enemy['id'])
                        assert enemy['hp'] == before['hp'] - 9 and enemy['hp_preview']['poison_damage'] == 8, enemy
                    details = await call('inspect_combatants')
                    assert [e['hp_preview'] for e in details['enemies']] == [e['hp_preview'] for e in observed['enemies']]
                else:
                    after_play = await call('get_observation')
                    retained = {c['id'] for c in after_play['player']['hand']}
                    drawn = {e['card']['id'] for e in result['transition']['events'] if e['type'] == 'card_drawn'}
                    if args.scenario == 'expertise':
                        assert len(drawn) == 2, result
                        retained = drawn
                        details = (await call('inspect_hand'))['hand']
                        assert drawn <= {c['id'] for c in details}, details
                        assert all('Retain' in c['description'] for c in details if c['id'] in drawn), details
                    ended = await call('end_turn')
                    assert ended['transition']['stop_reason'] == 'player_ready', ended
                    after_turn = await call('get_observation')
                    assert retained <= {c['id'] for c in after_turn['player']['hand']}, after_turn
                    if args.scenario == 'expertise':
                        second = await call('end_turn')
                        assert second['transition']['stop_reason'] == 'player_ready', second
                        final = await call('get_observation')
                        assert not retained & {c['id'] for c in final['player']['hand']}, final

            observed = await call('get_observation')
            defend = next(c for c in observed['player']['hand'] if c['name'] == 'Defend')
            await stable()
            await call('play_card', card_id=defend['id'])
    print(f'PASS v0.111 combat: {args.scenario}', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=('outbreak', 'well_laid_plans', 'expertise', 'toasty_mittens'))
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
