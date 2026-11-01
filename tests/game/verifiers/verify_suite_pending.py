"""Leave a supported native selection open to exercise run cleanup."""
from scripts._bootstrap import ROOT
import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tests.game.support.verification_runtime import ipc_directory


async def verify(args):
    params = StdioServerParameters(command=sys.executable, args=[
        str((ROOT / "scripts/mcp_server.py")), '--ipc-dir', str(ipc_directory())])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('get_observation', {})
            data = result.structuredContent
            args.report.write_text(json.dumps(data, indent=2) + '\n')
            assert data == json.loads(result.content[0].text) and not result.isError, data
            assert data['selection']['status'] == 'visible', data
            assert data['selection']['type'] == 'deck', data
    print('PASS: native selection remains open for suite cleanup.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True, type=Path)
    asyncio.run(verify(parser.parse_args()))


if __name__ == '__main__':
    main()
