"""Continue native actions from inspections and view results without basic observations."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from roundtrip_client import Client
from verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    evidence = []
    args.report.parent.mkdir(parents=True, exist_ok=True)
    params = StdioServerParameters(command=sys.executable, args=[
        str(Path(__file__).with_name('mcp_server.py')), '--ipc-dir', str(ipc_directory())])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments=None, error=None):
                response = await session.call_tool(name, arguments or {})
                data = response.structuredContent
                evidence.append({'tool': name, 'arguments': arguments, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert data == json.loads(response.content[0].text), response
                if error:
                    assert response.isError and data.get('error', {}).get('code') == error, data
                else:
                    assert not response.isError and 'error' not in data, data
                return data

            def completed(data, reason):
                assert data['transition']['complete'] and data['transition']['stop_reason'] == reason, data

            if args.scenario == 'map':
                await call('inspect_rewards')
                completed(await call('proceed'), 'action_completed')
                for _ in range(2):
                    details = await call('inspect_map')
                    assert details['can_travel'] and details['selectable_nodes'], details
                # A non-selectable node must still be rejected by the native action validator.
                await call('travel_to_node', {'node_id': details['current_node']}, error='illegal_action')
                details = await call('inspect_map')
                destination = details['selectable_nodes'][0]
                completed(await call('travel_to_node', {'node_id': destination}), 'action_completed')
                arrived = await call('inspect_map')
                assert arrived['current_node'] == destination, arrived
            elif args.scenario == 'views':
                for tool, arguments in (('inspect_deck', {}), ('inspect_pile', {'pile': 'draw'})):
                    await call(tool, arguments)
                    await call('end_turn', error='illegal_action')
                    closed = await call('close_card_view')
                    assert closed['screen'] == {'status': 'visible'}, closed
                    completed(await call('end_turn'), 'player_ready')
                hand = await call('inspect_hand')
                defend = next(c for c in hand['hand'] if c['name'] == 'Defend')
                completed(await call('play_card', {'card_id': defend['id']}), 'player_ready')
            else:
                hand = await call('inspect_hand')
                card = next(c for c in hand['hand'] if c['name'] == 'Discovery')
                completed(await call('play_card', {'card_id': card['id']}), 'choice_required')
                details = await call('inspect_selection')
                choice = details['selection']['cards'][0]['id']
                assert details['selection']['can_view_battlefield'], details
                await call('set_selection_view', {'view': 'battlefield'})
                await call('select_card', {'card_id': choice}, error='illegal_action')
                shown = await call('set_selection_view', {'view': 'selection'})
                assert shown['selection']['status'] == 'visible', shown
                completed(await call('select_card', {'card_id': choice}), 'player_ready')
                hand = await call('inspect_hand')
                assert any(c['id'] == choice for c in hand['hand']), hand
            assert all(item['tool'] != 'get_observation' for item in evidence)
    print('PASS observation sources:', args.scenario, 'native continuation without get_observation', flush=True)


def main():
    parser = argparse.ArgumentParser(description='验证详情及切换视图后直接行动，不额外调用基础观察。')
    parser.add_argument('--scenario', choices=('map', 'views', 'selection'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
