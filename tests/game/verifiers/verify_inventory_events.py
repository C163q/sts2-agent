"""Verify native inventory and permanent card changes through public MCP receipts."""
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
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    changes = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    params = StdioServerParameters(command=sys.executable, args=[str((ROOT / "scripts/mcp_server.py")),
                                  '--ipc-dir', str(raw.directory)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None):
                reply = await session.call_tool(name, arguments or {})
                data = reply.structuredContent
                record({'tool': name, 'arguments': arguments, 'result': data})
                assert not reply.isError and 'error' not in data, data
                assert data == json.loads(reply.content[0].text), reply
                if 'transition' in data:
                    events = data['transition']['events']
                    assert data['transition']['complete'], data
                    assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), data
                    changes.extend(events)
                return data

            async def choose_cards():
                for _ in range(20):
                    state = await call('get_observation')
                    if not state.get('selection'):
                        return
                    choice = (await call('inspect_selection', {'preset': 'summary'}))['selection']
                    if len(choice['selected_ids']) < choice['min_select']:
                        card = next(c for c in choice['cards'] if c['id'] not in choice['selected_ids'])
                        await call('select_card', {'card_id': card['id']})
                    else:
                        await call('selection_option', {'option_id': 'confirm'})
                raise AssertionError('Selection did not resolve.')

            state = await call('get_observation')
            scenario = args.scenario
            if scenario in ('smith', 'cook'):
                await call('choose_rest_option', {'option_id': 'SMITH' if scenario == 'smith' else 'COOK'})
                await choose_cards()
                required = ['card_upgraded'] if scenario == 'smith' else ['card_removed', 'max_hp_changed']
            elif scenario in ('upgrade', 'transform', 'enchant', 'remove'):
                options = state['event']['options']
                index = 1 if scenario in ('upgrade', 'remove') else 0
                await call('choose_event_option', {'option_id': options[index]['id']})
                assert not any(e['type'].startswith('card_') for e in changes), changes
                await choose_cards()
                required = {'upgrade': ['card_upgraded'], 'transform': ['card_removed', 'card_added'],
                            'enchant': ['card_enchantment_changed'], 'remove': ['card_removed']}[scenario]
            elif scenario == 'shop':
                await call('open_shop')
                for kind in ('potion', 'relic', 'card'):
                    details = await call('inspect_shop')
                    item = next(i for i in details['shop']['items'] if i['kind'] == kind and i['enabled'])
                    await call('buy_item', {'item_id': item['id']})
                required = ['gold_changed', 'potion_obtained', 'relic_obtained', 'card_added']
            elif scenario == 'reward':
                for kind in ('potion', 'relic', 'special_card', 'card', 'gold'):
                    details = await call('inspect_rewards')
                    for row in details['rewards']['items']:
                        if row['type'] == kind:
                            await call('claim_reward', {'reward_id': row['id']})
                            await choose_cards()
                # Complete all native offers before the suite resets this run.
                details = await call('inspect_rewards')
                for row in details['rewards']['items']:
                    if row['enabled']:
                        await call('claim_reward', {'reward_id': row['id']})
                        await choose_cards()
                await call('proceed')
                required = ['potion_obtained', 'relic_obtained', 'card_upgraded', 'card_added']
            elif scenario == 'ancient':
                deadline = time.monotonic() + 10
                while not {'advance_dialogue', 'choose_ancient_option'} & set(state['available_actions']):
                    assert time.monotonic() < deadline
                    await asyncio.sleep(.1)
                    state = await call('get_observation')
                while 'advance_dialogue' in state['available_actions']:
                    await call('advance_dialogue')
                    state = await call('get_observation')
                await call('choose_ancient_option', {'option_id': next(o['id'] for o in state['ancient']['options'] if o['enabled'])})
                required = ['relic_obtained']
            elif scenario == 'rescue':
                await call('choose_event_option', {'option_id': state['event']['options'][0]['id']})
                required = ['potion_used', 'hp_changed']
            elif scenario == 'temporary':
                card = next(c for c in state['player']['hand'] if c['name'] == 'Armaments')
                await call('play_card', {'card_id': card['id']})
                await choose_cards()
                assert not any(e['type'] in ('card_upgraded', 'card_downgraded', 'card_enchantment_changed',
                                            'card_stats_changed', 'card_energy_cost_changed') for e in changes), changes
                required = ['card_played']
            else:
                result = await asyncio.to_thread(raw.call, 'check_test_inventory')
                record({'checks': result})
                assert result['ok'] and result['state']['passed'], result
                required = []
            assert set(required) <= {e['type'] for e in changes}, ('Missing inventory changes', required, changes)
            for event in changes:
                if event['type'] in ('card_removed', 'card_upgraded', 'card_downgraded', 'card_enchantment_changed',
                                     'card_stats_changed', 'card_energy_cost_changed'):
                    assert event['pile'] == 'deck' and event['card']['name'], event
            record({'changes': changes})
    print(f'PASS inventory events: {args.scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证物品与永久牌组动作事件。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
