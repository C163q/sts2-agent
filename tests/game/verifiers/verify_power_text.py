"""Compare live countdown tips with native UI and record a real Hopper turn."""
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

    def record(value):
        evidence.append(value)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name):
                result = await session.call_tool(name, {})
                data = result.structuredContent
                record({'tool': name, 'result': data})
                assert not result.isError and data == json.loads(result.content[0].text), result
                return data

            initial = await call('get_observation')
            assert initial['turn'] == 1, initial
            assert [enemy['name'] for enemy in initial['enemies']] == ['Thieving Hopper'], initial
            for amount in (5, 4, 3, 2, 1):
                detail = await call('inspect_combatants')
                enemy = detail['enemies'][0]
                assert next(power['amount'] for power in enemy['powers'] if power['name'] == 'Escape Artist') == amount, detail
                text = 'Tries to escape the combat ' + ('this turn.' if amount == 1 else f'after {amount} turns.')
                assert next(tip['description'] for tip in detail['hover_tips'] if tip['title'] == 'Escape Artist') == text, detail
                if amount in (5, 4, 1):
                    native = await asyncio.to_thread(raw.call, 'capture_test_power_tips')
                    record({'native_ui': native})
                    assert native['ok'], native
                    native_tips = native['state']['results']
                    english = next(result for result in native_tips if result['locale'] == 'eng')
                    chinese = next(result for result in native_tips if result['locale'] == 'zhs')
                    assert english['tips'][0]['description'] == text, native
                    assert str(amount) in chinese['tips'][0]['description'], native
                    # Restore the locale and hover state before comparing the real read again.
                    assert await call('inspect_combatants') == detail
                receipt = await call('end_turn')
                transition = receipt['transition']
                assert transition['complete'], receipt
                assert transition['stop_reason'] == ('combat_won' if amount == 1 else 'player_ready'), receipt
                if amount == 5:
                    (args.report.parent / 'hopper-first-end-turn.json').write_text(
                        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
                    events = transition['events']
                    assert any(event['type'] == 'power_changed' and event['name'] == 'Swipe'
                               and event['change'] == 'applied' for event in events), receipt
                    assert any(event['type'] == 'power_changed' and event['name'] == 'Escape Artist'
                               and (event['before'], event['after']) == (5, 4) for event in events), receipt
                    assert any(event['type'] == 'damage' and event.get('actor', {}).get('name') == 'Thieving Hopper'
                               and event['hp_loss'] + event['blocked'] == 17 for event in events), receipt
                    after = await call('get_observation')
                    assert after['top_bar']['deck_count'] == initial['top_bar']['deck_count'] - 1, after
            assert all(item['result']['scene'] == 'combat' for item in evidence if item.get('tool') == 'inspect_combatants')
    print('PASS Hopper countdown 5/4/3/2/1, bilingual native UI parity and first-turn receipt', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证原生草蜢倒计时及偷牌首回合回执。')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
