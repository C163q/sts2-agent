"""Exercise native test gates in the owned graphical test process."""
from scripts._bootstrap import ROOT
import argparse
import json
from pathlib import Path
from sts2_mcp.roundtrip_client import Client
from tests.game.support.verification_runtime import ensure_run, ipc_directory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    client = Client(ipc_directory(), timeout=140)
    ensure_run(client)
    result = client.call('check_test_dispatch')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    assert result['ok'], result
    assert result['state']['test_mode_off'] >= 60, result
    assert result['state']['suite_and_scenarios_off'] == result['state']['test_mode_off'], result
    print('PASS native test dispatch gates', flush=True)


if __name__ == '__main__': main()
