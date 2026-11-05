"""Capture exposed treasure details, covered refusals and read-only recovery."""
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

SCENARIOS = ('basic', 'empty', 'extra', 'nested', 'choice', 'no_treasure', 'map_pending')


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def record(row):
        evidence.append(row)
        args.report.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool, arguments=None, error=None, label=None):
                arguments = {'preset': 'full', **(arguments or {})}
                old = set((raw.directory / 'responses').glob('*.json'))
                response = await session.call_tool(tool, arguments)
                result = response.structuredContent
                row = {'tool': tool, 'arguments': arguments, 'result': result, 'label': label,
                    'image_count': sum(part.type == 'image' for part in response.content)}
                added = set((raw.directory / 'responses').glob('*.json')) - old
                if added:
                    assert len(added) == 1, added
                    native = json.loads(added.pop().read_text())
                    row.update(native_error=native.get('error'), execution=native.get('execution'))
                record(row)
                assert result == json.loads(response.content[0].text), response
                assert response.isError == bool(error), result
                assert result.get('error', {}).get('code') == error, result
                return result

            async def reject(label, *, permission=True):
                result = await call('inspect_treasure', error='illegal_action', label=label)
                assert result['error']['message'] == 'The requested action is unavailable.', result
                assert result['error']['recovery'] == ('choose_legal_action' if permission else 'get_observation'), result
                return result

            async def inspect(label):
                value = await call('inspect_treasure', label=label)
                assert set(value) == {'scene', 'screen', 'treasure'}, value
                assert value['scene'] == 'treasure' and value['screen'] == {'status': 'visible'}, value
                assert value['treasure']['status'] == 'visible', value
                return value

            if args.scenario == 'no_treasure':
                await reject('no_initial_permission', permission=False)
                await call('end_turn', error='observation_required')
                await call('get_observation')
                await reject('wrong_scene_with_permission')
                await call('end_turn', label='direct_after_read_refusal')
                return

            closed = await inspect('closed_full')
            assert closed['treasure'] == {'status': 'visible', 'chest': 'closed', 'relic': None, 'proceed': None}, closed
            assert await inspect('repeat_closed_full') == closed
            compact = await call('inspect_treasure', {'preset': 'default'}, label='closed_default')
            assert compact['treasure'] == {'status': 'visible', 'chest': 'closed', 'relic': None}, compact
            observed = await call('get_observation')
            assert observed['treasure'] == closed['treasure'], observed

            if args.scenario == 'basic':
                await call('inspect_deck')
                await reject('deck_covered')
                await call('close_card_view')
                await inspect('after_deck')
                await call('inspect_map')
                await reject('map_covered')
                # Reaching the native refusal proves the read kept existing permission.
                await call('loot_treasure', error='illegal_action', label='native_action_after_read_refusal')
                await call('close_map')
                await call('inspect_treasure', {'preset': 'summary'}, 'invalid_request', 'summary_not_supported')

            receipt = await call('loot_treasure', {'open_only': True})
            if args.scenario == 'extra':
                assert receipt['scene'] == 'rewards', receipt
                rewards = await call('inspect_rewards')
                await reject('extra_rewards_covered')
                claimed = await call('claim_reward', {'reward_id': rewards['rewards']['items'][0]['id']}, label='direct_claim_after_read_refusal')
                if claimed['scene'] == 'rewards':
                    await call('proceed')

            opened = await inspect('opened_full')
            if args.scenario == 'empty':
                assert opened['treasure']['relic'] is None and opened['treasure']['proceed']['enabled'], opened
                value = await call('inspect_treasure', {'preset': 'default'}, label='empty_default')
                assert 'relic' in value['treasure'] and value['treasure']['relic'] is None, value
            else:
                relic = opened['treasure']['relic']
                assert relic and set(relic) == {'name', 'enabled', 'description', 'hover_tips'}, opened
                assert relic['enabled'] is True and relic['description'], opened
                assert all(set(tip) == {'title', 'description'} for tip in relic['hover_tips']), relic
                for preset in ('full', 'default', 'summary'):
                    observation = await call('get_observation', {'preset': preset}, label='observation_' + preset)
                    assert observation['treasure']['relic'] == {'name': relic['name'], 'enabled': True}, observation
                await call('inspect_treasure', {'preset': 'default'}, label='opened_default')
                receipt = await call('loot_treasure')
                if args.scenario == 'nested':
                    assert receipt['scene'] == 'rewards', receipt
                    await reject('nested_rewards_covered')
                    await call('proceed', label='direct_proceed_after_read_refusal')
                elif args.scenario == 'choice':
                    assert receipt['transition']['stop_reason'] == 'choice_required', receipt
                    selection = await call('inspect_selection')
                    await reject('selection_covered')
                    for card in selection['selection']['cards'][:3]:
                        await call('select_card', {'card_id': card['id']})
                    await call('inspect_selection')
                    await call('selection_option', {'option_id': 'confirm'})
                elif args.scenario == 'map_pending':
                    assert receipt['screen']['view'] == 'map', receipt
                    await reject('obtain_map_covered')
                    await call('close_map')

            collected = await inspect('collected_full')
            assert collected['treasure']['chest'] == 'open' and collected['treasure']['relic'] is None, collected
            assert not collected['treasure']['proceed']['skips_remaining'], collected
            await call('proceed')
    print('PASS treasure inspection review:', args.scenario, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))
