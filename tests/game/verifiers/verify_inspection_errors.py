"""Verify inspection rejection recovery and an unsubmitted play over real MCP."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from sts2_mcp.roundtrip_client import Client
from sts2_mcp.mcp_server import SERVER_VERSION
from tests.game.support.verification_runtime import ensure_run, ipc_directory


async def verify(args):
    raw = Client(ipc_directory())
    await asyncio.to_thread(ensure_run, raw)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    evidence = []
    config = args.report.with_suffix('.config.json')
    config.write_text(json.dumps({'screenshots': {'enabled': True,
                      'directory': str(args.report.parent / 'screenshots')}}))
    params = StdioServerParameters(command=sys.executable, args=[
        str(ROOT / 'scripts/mcp_server.py'), '--ipc-dir', str(raw.directory), '--config', str(config)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.version == SERVER_VERSION

            async def call(tool, arguments=None, error=None, message=None):
                supplied = {'preset': 'full', **(arguments or {})} if tool != 'capture_screenshot' else arguments
                response = await session.call_tool(tool, supplied)
                result = response.structuredContent
                evidence.append({'tool': tool, 'arguments': supplied, 'result': result})
                args.report.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + '\n')
                assert result == json.loads(response.content[0].text)
                if error:
                    assert response.isError and result['error']['code'] == error, result
                    if message: assert message in result['error']['message'], result
                else:
                    assert not response.isError and 'error' not in result, result
                assert 'snapshot_id' not in result
                assert 'action_submitted' not in result.get('error', {})
                assert 'public_message' not in result.get('error', {})
                return result

            observed = await call('get_observation')
            original_turn = observed['turn']
            hand = await call('inspect_hand')
            await call('inspect_ui')
            attack = next(card for card in hand['hand'] if card['name'] == 'Strike')
            missing = max(card['id'] for card in hand['hand']) + 100000
            query = await call('inspect_targets', {'card_id': attack['id']})
            target = query['targets'][0]['id']
            if args.scenario == 'energy':
                assert observed['player']['energy'] == 0, observed
                assert not query['playable'] and query['targets'] and query['reason'] == 'Not enough Energy.'
                rejected = await call('play_card', {'card_id': attack['id'], 'target_id': target},
                                      error='illegal_action', message='Not enough Energy.')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                ended = await call('end_turn')
                assert ended['transition']['stop_reason'] == 'player_ready', ended
            else:
                invalid = [
                    ('get_observation', {'extra': True}, 'preset'),
                    ('inspect_hand', {'card_ids': [True]}, 'card_ids'),
                    ('inspect_ui', {'sources': False}, 'sources'),
                    ('inspect_targets', {'card_id': attack['id'], 'preset': 'summary'}, 'preset'),
                ]
                for tool, arguments, field in invalid:
                    await call(tool, arguments, error='invalid_request', message=field)
                    # A native rejection proves the previous read's permission survived.
                    rejected = await call('play_card', {'card_id': missing}, error='illegal_action',
                                          message='No supported visible hand card has that ID.')
                    assert rejected['error']['recovery'] == 'choose_legal_action', rejected

                rejected = await call('inspect_targets', {'card_id': missing}, error='illegal_action',
                                      message='No supported visible hand card has that ID.')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                rejected = await call('inspect_targets', {'potion_slot': 100000}, error='illegal_action',
                                      message='No supported visible potion occupies that slot.')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                await call('play_card', {'card_id': attack['id']}, error='illegal_action', message='requires target_id')
                defense = next(card for card in hand['hand'] if card['name'] == 'Defend')
                await call('play_card', {'card_id': defense['id'], 'target_id': target},
                           error='illegal_action', message='does not accept target_id')
                await call('play_card', {'card_id': attack['id'], 'target_id': 4294967295},
                           error='illegal_action', message='not currently available')
                ended = await call('end_turn')
                assert ended['transition']['stop_reason'] == 'player_ready', ended

                await call('inspect_deck')
                rejected = await call('inspect_hand', error='illegal_action', message='Hand details are unavailable')
                assert rejected['error']['recovery'] == 'choose_legal_action'
                await call('end_turn', error='illegal_action')
                await call('inspect_targets', {'card_id': attack['id']}, error='illegal_action',
                           message='Normal card play is unavailable')
                await call('get_observation')
                await call('inspect_ui')
                await call('close_card_view')

            final = await call('get_observation')
            assert final['turn'] == original_turn + 1, final
            await call('capture_screenshot', {'filename': f'{args.scenario}-recovered.png'})
            assert sum(item['tool'] == 'end_turn' and 'error' not in item['result'] for item in evidence) == 1
    print(f'PASS: {args.scenario} inspection diagnostics, preserved rejection permission and native end_turn.')


def main():
    from pathlib import Path
    parser = argparse.ArgumentParser(description='隔离图形实例的查看错误与未提交出牌恢复验证。')
    parser.add_argument('--scenario', choices=('basic', 'energy'), required=True)
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
