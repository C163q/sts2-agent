"""Verify player resources against visible UI through real MCP actions."""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from roundtrip_client import Client
from verification_runtime import ensure_run, ipc_directory


def verify_changes(before, receipt, after, required):
    events = receipt['transition']['events']
    assert receipt['transition']['complete'], receipt
    assert [e['sequence'] for e in events] == list(range(1, len(events) + 1)), events
    assert set(required) <= {e['type'] for e in events}, ('Missing resource events', receipt)
    values = {key: before['top_bar'][key] for key in ('hp', 'max_hp', 'gold')}
    fields = {'hp_changed': 'hp', 'max_hp_changed': 'max_hp', 'gold_changed': 'gold'}
    for event in events:
        if event.get('target', {}).get('kind') != 'player':
            continue
        if event['type'] in fields:
            key = fields[event['type']]
            assert values[key] == event['before'], (key, values, event)
            values[key] = event['after']
        elif event['type'] == 'damage':
            values['hp'] -= event['hp_loss']
    assert values == {key: after['top_bar'][key] for key in values}, (values, after['top_bar'], events)


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []

    def record(item):
        evidence.append(item)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')

    async def state():
        reply = await asyncio.to_thread(raw.call, 'get_state')
        assert reply['ok'], reply
        record({'native': reply})
        return reply['state']

    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name('mcp_server.py')),
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
                return data

            async def change(name, arguments, required):
                before = await state()
                receipt = await call(name, arguments)
                after = await state()
                verify_changes(before, receipt, after, required)
                return receipt

            observed = await call('get_observation')
            scenario = args.scenario
            if scenario in ('event', 'rescue'):
                option = next(o for o in observed['event']['options'] if o['enabled'])
                receipt = await change('choose_event_option', {'option_id': option['id']}, ['max_hp_changed', 'hp_changed'])
                if scenario == 'event':
                    events = receipt['transition']['events']
                    assert [(e['type'], e['before'], e['after']) for e in events] == [
                        ('max_hp_changed', 80, 82), ('hp_changed', 40, 42), ('hp_changed', 42, 39)], events
                    # Native options have new IDs after the event page updates.
                    details = await call('inspect_event')
                    await change('choose_event_option', {'option_id': details['event']['options'][0]['id']},
                                 ['max_hp_changed', 'hp_changed'])
            elif scenario == 'rest':
                receipt = await change('choose_rest_option', {'option_id': 'HEAL'}, ['hp_changed'])
                assert len(receipt['transition']['events']) == 1, receipt
            elif scenario == 'cook':
                await call('choose_rest_option', {'option_id': 'COOK'})
                details = await call('inspect_selection', {'preset': 'summary'})
                for card in details['selection']['cards'][:2]:
                    await call('select_card', {'card_id': card['id']})
                await change('selection_option', {'option_id': 'confirm'}, ['max_hp_changed', 'hp_changed'])
            elif scenario == 'shop':
                assert (await call('open_shop'))['transition']['events'] == []
                details = await call('inspect_shop')
                card = next(i for i in details['shop']['items'] if i['kind'] == 'card' and i['enabled'])
                receipt = await change('buy_item', {'item_id': card['id']}, ['gold_changed'])
                assert receipt['purchase_result']['status'] == 'success', receipt
                assert (await call('close_shop'))['transition']['events'] == []
            elif scenario == 'reward':
                details = await call('inspect_rewards')
                gold = next(r for r in details['rewards']['items'] if r['type'] == 'gold')
                await change('claim_reward', {'reward_id': gold['id']}, ['gold_changed'])
                details = await call('inspect_rewards')
                card = next(r for r in details['rewards']['items'] if r['type'] == 'card')
                await call('claim_reward', {'reward_id': card['id']})
                choices = await call('inspect_selection', {'preset': 'summary'})
                await call('select_card', {'card_id': choices['selection']['cards'][0]['id']})
                await call('proceed')
            elif scenario == 'ancient':
                deadline = time.monotonic() + 10
                while not {'advance_dialogue', 'choose_ancient_option'} & set(observed['available_actions']):
                    assert time.monotonic() < deadline
                    await asyncio.sleep(.1)
                    observed = await call('get_observation')
                while 'advance_dialogue' in observed['available_actions']:
                    await call('advance_dialogue')
                    observed = await call('get_observation')
                option = next(o for o in observed['ancient']['options'] if o['enabled'])
                await change('choose_ancient_option', {'option_id': option['id']}, ['max_hp_changed', 'hp_changed'])
            elif scenario in ('potion_combat', 'potion_rest'):
                details = await call('inspect_potions')
                index = next(i for i, p in enumerate(details['potion_slots']) if p and p['name'] == 'Fruit Juice')
                receipt = await change('use_potion', {'potion_slot': index},
                                       ['potion_used', 'max_hp_changed', 'hp_changed'])
                assert sum(e['type'] == 'hp_changed' for e in receipt['transition']['events']) == 1, receipt
            elif scenario == 'combat':
                receipt = await change('end_turn', None, ['damage'])
                assert not any(e['type'] == 'hp_changed' for e in receipt['transition']['events']), receipt
                await call('end_turn')
            elif scenario == 'entry':
                await call('inspect_rewards')
                details = await call('inspect_map', {'preset': 'selectable'})
                receipt = await change('travel_to_node', {'node_id': details['selectable_nodes'][0]}, ['card_drawn'])
                assert receipt['scene'] == 'combat' and receipt['transition']['stop_reason'] == 'player_ready', receipt
                await call('end_turn')
            elif scenario in ('visibility', 'masks'):
                result = await asyncio.to_thread(raw.call, 'check_test_resources' if scenario == 'visibility'
                                                 else 'check_test_resource_masks')
                record({'checks': result})
                assert result['ok'] and result['state']['passed'], result
            else:
                raise ValueError('Unknown resource event scenario.')
    print(f'PASS resource events: {scenario}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='验证动作期间玩家 HP、最大生命和金币事件。')
    parser.add_argument('--scenario', required=True)
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))
