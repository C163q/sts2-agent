"""Compare room identity across native observations and selection inspections."""
from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tests.game.support.verification_runtime import ipc_directory


async def verify(args):
    evidence = []
    params = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), '--ipc-dir', str(ipc_directory())])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, full_output_arguments(name, arguments or {}))
                data = reply.structuredContent
                evidence.append({'tool': name, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert not reply.isError and data == json.loads(reply.content[0].text), data
                return data

            state = await call('get_observation')
            if args.scenario == 'ancient_bundle':
                deadline = time.monotonic() + 10
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline, 'Ancient input did not become ready.'
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                receipt = await call('choose_ancient_option', {'option_id': state['ancient']['options'][0]['id']})
                expected_scene, expected_type = 'ancient', 'bundle'
            elif args.scenario == 'rest_smith':
                receipt = await call('choose_rest_option', {'option_id': 'SMITH'})
                expected_scene, expected_type = 'rest_site', 'deck_upgrade'
            elif args.scenario == 'combat_discovery':
                card = next(c for c in state['player']['hand'] if c['name'] == 'Discovery')
                receipt = await call('play_card', {'card_id': card['id']})
                expected_scene, expected_type = 'combat', 'choose_one'
            elif args.scenario == 'shop_remove':
                await call('open_shop')
                state = await call('get_observation')
                item = next(i for i in state['shop']['items'] if i['kind'] == 'card_removal')
                receipt = await call('buy_item', {'item_id': item['id']})
                expected_scene, expected_type = 'shop', 'deck'
            else:
                receipt = None
                expected_scene, expected_type = 'event', 'deck'
            if receipt is not None:
                assert receipt['scene'] == expected_scene, receipt
                assert receipt['transition']['stop_reason'] == 'choice_required', receipt
            before = await call('get_observation')
            details = await call('inspect_selection')
            after = await call('get_observation')
            assert before == after, 'Inspection changed the observed UI.'
            assert before['scene'] == details['scene'] == expected_scene, (before, details)
            assert before['selection']['type'] == details['selection']['type'] == expected_type
            assert before['selection']['status'] == details['selection']['status'] == 'visible'
            cards = details['selection']['cards']
            if expected_type == 'bundle':
                assert len(details['selection']['bundles']) == 2, details
                cards = [c for b in details['selection']['bundles'] for c in b['cards']]
                assert len(cards) == 6, details
            assert cards and all(c['description'] for c in cards), details
            assert isinstance(details['hover_tips'], list), details
            # Leave the choice pending: the suite must clean up native selection tasks.
    print(f'PASS selection scene: {expected_scene}/{expected_type}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', required=True, choices=(
        'ancient_bundle', 'rest_smith', 'combat_discovery', 'event_deck', 'shop_remove'))
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
