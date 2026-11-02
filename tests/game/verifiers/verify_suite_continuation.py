"""Continue the existing run through MCP, without fixture edits or a restart."""
from scripts._bootstrap import ROOT
from tests.game.support.verification_actions import full_output_arguments
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tests.game.support.verification_runtime import ipc_directory


async def verify(args):
    root = ROOT
    params = StdioServerParameters(command=sys.executable, args=[str(root / 'scripts/mcp_server.py'),
                                                             '--ipc-dir', str(ipc_directory())])
    evidence = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            async def call(name):
                result = await session.call_tool(name, full_output_arguments(name, {}))
                data = result.structuredContent
                evidence.append({'tool': name, 'result': data})
                args.report.write_text(json.dumps(evidence, indent=2) + '\n')
                assert data == json.loads(result.content[0].text) and not result.isError, data
                return data
            before = await call('get_observation')
            assert before['scene'] == 'combat' and 'end_turn' in before['available_actions'], before
            ended = await call('end_turn')
            assert ended['transition']['complete'] and ended['transition']['stop_reason'] == 'player_ready', ended
            after = await call('get_observation')
            assert after['turn'] == before['turn'] + 1, (before, after)
    print('PASS: a fresh MCP connection continued the same run by one turn.')


def main():
    parser = argparse.ArgumentParser(description='通过公开 MCP 继续当前测试局一个回合')
    parser.add_argument('--report', type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
