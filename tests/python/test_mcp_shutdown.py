"""Exercise process shutdown through the public stdio entry point."""
from scripts._bootstrap import ROOT

import json
import os
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path

from sts2_mcp.controller_lease import ControllerLease


class ShutdownTests(unittest.TestCase):
    @contextmanager
    def server(self):
        with tempfile.TemporaryDirectory() as directory:
            ipc = Path(directory)
            config = ipc / 'config.json'
            config.write_text('{"screenshots":{"enabled":false}}')
            process = subprocess.Popen(
                [sys.executable, str(ROOT / 'scripts/mcp_server.py'),
                 '--ipc-dir', directory, '--config', str(config), '--timeout', '30'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=True,
            )
            try:
                self.send(process, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                    'protocolVersion': '2024-11-05', 'capabilities': {},
                    'clientInfo': {'name': 'shutdown-test', 'version': '1'},
                }})
                self.assertTrue(select.select([process.stdout], [], [], 5)[0], 'MCP handshake timed out')
                self.assertEqual(json.loads(process.stdout.readline())['id'], 1)
                self.send(process, {'jsonrpc': '2.0', 'method': 'notifications/initialized'})
                yield process, ipc
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate(timeout=3)
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()

    @staticmethod
    def send(process, message):
        process.stdin.write((json.dumps(message) + '\n').encode())
        process.stdin.flush()

    def wait_for_request(self, process, ipc):
        self.send(process, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
                            'params': {'name': 'get_observation', 'arguments': {}}})
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            requests = list((ipc / 'requests').glob('*.json'))
            if requests:
                return requests
            time.sleep(0.01)
        self.fail('Tool call did not reach the file transport')

    def finish(self, process, ipc):
        try:
            process.wait(timeout=2)
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            self.fail('MCP server did not finish shutdown within two seconds')
        self.assertEqual(stderr, b'')
        self.assertEqual(process.returncode, 0)
        with ControllerLease(ipc):
            pass
        return stdout

    def test_signals_exit_cleanly_with_stdin_open(self):
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig), self.server() as (process, ipc):
                process.send_signal(sig)
                # Keep stdin open: communicate() would close it and hide a blocked reader.
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.fail('Signal did not stop the server while stdin remained open')
                self.finish(process, ipc)

    def test_shutdown_cancels_pending_file_wait_and_releases_control(self):
        for mode in ('sigint', 'sigterm', 'eof', 'process_group'):
            with self.subTest(mode=mode), self.server() as (process, ipc):
                requests = self.wait_for_request(process, ipc)
                with self.assertRaises(BlockingIOError):
                    with ControllerLease(ipc):
                        pass
                if mode == 'eof':
                    process.stdin.close()
                    process.stdin = None
                elif mode == 'process_group':
                    os.killpg(process.pid, signal.SIGINT)
                else:
                    process.send_signal(signal.SIGINT if mode == 'sigint' else signal.SIGTERM)
                self.finish(process, ipc)
                self.assertEqual(list((ipc / 'requests').glob('*.json')), requests)
                self.assertEqual(list((ipc / 'responses').glob('*.json')), [])

    def test_disconnected_stdout_is_a_clean_disconnect(self):
        with self.server() as (process, ipc):
            process.stdout.close()
            process.stdout = None
            self.send(process, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.fail('Broken stdout did not stop the server')
            self.finish(process, ipc)

    def test_eof_while_idle_exits_cleanly(self):
        with self.server() as (process, ipc):
            process.stdin.close()
            process.stdin = None
            self.finish(process, ipc)

    def test_signal_cancels_output_when_client_stops_reading(self):
        with self.server() as (process, ipc):
            self.send(process, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
            self.assertTrue(select.select([process.stdout], [], [], 2)[0], 'No tool catalog output')
            process.send_signal(signal.SIGINT)
            self.finish(process, ipc)

    def test_unexpected_stream_errors_remain_visible(self):
        with self.server() as (process, ipc):
            process.stdin.write(b'\xff\n')
            process.stdin.flush()
            process.wait(timeout=2)
            _, stderr = process.communicate(timeout=2)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b'UnicodeDecodeError', stderr)


if __name__ == '__main__':
    unittest.main()
