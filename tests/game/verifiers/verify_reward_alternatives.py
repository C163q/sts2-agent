"""Verify native sacrifice/reroll buttons and effects without touching a live run."""
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
from tests.game.support.verification_actions import completed_action_state
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True, 'directory': str(args.report.parent / 'screenshots')}}))
    evidence = []
    stable_results = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                result = await session.call_tool(name, arguments or {})
                data = result.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert data == json.loads(result.content[0].text), result
                if error:
                    assert result.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not result.isError and 'error' not in data, data
                return data

            async def fixture():
                result = await asyncio.to_thread(raw.call, 'check_test_rewards')
                record({'fixture': result})
                assert result['ok'], result
                return result['state']

            def completed(receipt, reason):
                assert receipt['transition']['complete'] and receipt['transition']['stop_reason'] == reason, receipt

            async def choices(label, index):
                overview = await call('get_observation')
                detail = await call('inspect_selection')
                selection = detail['selection']
                assert selection['type'] == 'reward' and selection['status'] == 'visible', detail
                assert overview['selection']['options'] == selection['options'], (overview, detail)
                option = next(o for o in selection['options'] if o['text'].replace('-', '').casefold() == label)
                assert option['enabled'] and option['id'].startswith('alternative:'), option
                await call('capture_screenshot', {'filename': f'{args.scenario}-{index}-options.png'})
                return selection, option

            async def stable(receipt):
                returned = completed_action_state(raw.directory, receipt)
                start = time.monotonic()
                unchanged = True
                for delay in (0, .5, 1.25, 2.5):
                    await asyncio.sleep(max(0, start + delay - time.monotonic()))
                    current = await asyncio.to_thread(raw.call, 'get_state')
                    record({'sample_seconds': time.monotonic() - start, 'returned_state': returned, 'sample': current})
                    assert current['ok'], current
                    unchanged &= current['state']['snapshot_id'] == returned['snapshot_id']
                stable_results.append(unchanged)

            rewards = await call('inspect_rewards')
            rows = [r for r in rewards['rewards']['items'] if r['type'] == 'card']
            assert len(rows) == 2, rewards
            before = await fixture()
            relic_id = 'PAELS_WING' if args.scenario == 'paels_wing' else 'DRIFTWOOD'
            assert relic_id in before['relics'], before

            if args.scenario == 'paels_wing':
                for index, row in enumerate(rows, 1):
                    receipt = await call('claim_reward', {'reward_id': row['id']})
                    completed(receipt, 'choice_required')
                    selection, option = await choices('sacrifice', index)
                    assert any(o['id'] == 'skip' for o in selection['options']), selection
                    receipt = await call('selection_option', {'option_id': option['id']})
                    completed(receipt, 'action_completed')
                    await stable(receipt)
                    after = await fixture()
                    assert after['deck'] == before['deck'] and after['sacrifices'] == index, after
                    assert len(after['relics']) == len(before['relics']) + (index // 2), after
                # Diagnostics did not refresh the permission saved by the second sacrifice.
                completed(await call('proceed'), 'action_completed')
            else:
                for index, row in enumerate(rows, 1):
                    receipt = await call('claim_reward', {'reward_id': row['id']})
                    completed(receipt, 'choice_required')
                    old, option = await choices('reroll', index)
                    receipt = await call('selection_option', {'option_id': option['id']})
                    completed(receipt, 'choice_required')
                    await stable(receipt)
                    overview = await call('get_observation')
                    detail = await call('inspect_selection')
                    selection = detail['selection']
                    assert overview['selection']['options'] == selection['options'], (overview, detail)
                    assert [o['id'] for o in selection['options']] == ['skip'], selection
                    assert {c['id'] for c in old['cards']}.isdisjoint(c['id'] for c in selection['cards']), selection
                    assert len((await fixture())['deck']) == len(before['deck']) + index - 1
                    await call('capture_screenshot', {'filename': f'driftwood-{index}-rerolled.png'})
                    await call('selection_option', {'option_id': option['id']}, error='illegal_action')
                    await call('inspect_selection')
                    await call('select_card', {'card_id': old['cards'][0]['id']}, error='illegal_action')
                    selection = (await call('inspect_selection'))['selection']
                    if index == 2:
                        completed(await call('selection_option', {'option_id': 'skip'}), 'action_completed')
                        completed(await call('claim_reward', {'reward_id': row['id']}), 'choice_required')
                        selection = (await call('inspect_selection'))['selection']
                        assert [o['id'] for o in selection['options']] == ['skip'], selection
                    receipt = await call('select_card', {'card_id': selection['cards'][0]['id']})
                    completed(receipt, 'action_completed')
                    after = await fixture()
                    assert len(after['deck']) == len(before['deck']) + index, after
                completed(await call('proceed'), 'action_completed')
            assert not (await call('inspect_rewards', error='illegal_action')).get('rewards')
            assert all(stable_results), 'A completed reward action changed state without input.'
    print('PASS native reward alternatives:', args.scenario, 'visible buttons, actual effects and state freshness', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证佩尔之翼献祭与浮木重掷的原生卡牌奖励按钮。')
    parser.add_argument('--scenario', choices=('paels_wing', 'driftwood'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
