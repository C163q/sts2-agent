"""Shared bootstrap for standalone verifiers and the graphical suite."""
from scripts._bootstrap import ROOT
import os
import time
from pathlib import Path

from sts2_mcp.roundtrip_client import Client


def ipc_directory():
    return Path(os.environ.get('STS2_AGENT_VERIFY_IPC_DIR',
                               str(ROOT / '.tmp/roundtrip/ipc')))


def ensure_run(client):
    state = client.call('get_state')
    if os.environ.get('STS2_AGENT_VERIFY_REUSE_RUN') == '1':
        identity = client.call('get_test_session')
        assert identity.get('ok') and identity['state']['run_id'], identity
        assert state.get('ok') and state['state']['scene'] != 'main_menu', state
        return state
    deadline = time.monotonic() + 30
    while state['state']['scene'] == 'unrecognized' and time.monotonic() < deadline:
        time.sleep(.1)
        state = client.call('get_state')
    assert state['state']['scene'] == 'main_menu', 'Requires an isolated game at the main menu.'
    result = Client(client.directory, timeout=140).call('start_test_combat', state['state']['snapshot_id'])
    assert result.get('ok'), result
    return result
