"""Exercise process shutdown through the public stdio entry point."""
from scripts._bootstrap import ROOT

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, Queue
from threading import Thread

from sts2_mcp.controller_lease import ControllerLease


WINDOWS = os.name == 'nt'


def console_signals():
    if not WINDOWS:
        return (signal.SIGINT, signal.SIGTERM)
    import ctypes
    return (signal.CTRL_BREAK_EVENT,) if ctypes.windll.kernel32.GetConsoleCP() else ()


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
                bufsize=0,
                **({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP}
                   if WINDOWS else {'start_new_session': True}),
            )
            try:
                self.send(process, {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
                    'protocolVersion': '2024-11-05', 'capabilities': {},
                    'clientInfo': {'name': 'shutdown-test', 'version': '1'},
                }})
                line = self.read_stdout(process.stdout.readline)
                self.assertTrue(line, process.stderr.read() if process.poll() is not None else line)
                self.assertEqual(json.loads(line)['id'], 1)
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

    def read_stdout(self, read):
        result = Queue(maxsize=1)
        Thread(target=lambda: result.put(read()), daemon=True).start()
        try:
            return result.get(timeout=5)
        except Empty:
            self.fail('MCP stdout read timed out')

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
        if not console_signals():
            self.skipTest('Windows console signal delivery requires an attached console.')
        for sig in console_signals():
            with self.subTest(signal=sig), self.server() as (process, ipc):
                process.send_signal(sig)
                # Keep stdin open: communicate() would close it and hide a blocked reader.
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.fail('Signal did not stop the server while stdin remained open')
                self.finish(process, ipc)

    def test_shutdown_cancels_pending_file_wait_and_releases_control(self):
        modes = ('eof', *console_signals()) if WINDOWS else ('sigint', 'sigterm', 'eof', 'process_group')
        for mode in modes:
            with self.subTest(mode=mode), self.server() as (process, ipc):
                requests = self.wait_for_request(process, ipc)
                with self.assertRaises(BlockingIOError):
                    with ControllerLease(ipc):
                        pass
                if mode == 'eof':
                    process.stdin.close()
                    process.stdin = None
                elif WINDOWS:
                    process.send_signal(mode)
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
        if not console_signals():
            self.skipTest('Windows console signal delivery requires an attached console.')
        with self.server() as (process, ipc):
            self.send(process, {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
            self.assertTrue(self.read_stdout(lambda: process.stdout.read(1)), 'No tool catalog output')
            process.send_signal(console_signals()[0])
            self.finish(process, ipc)

    def test_unexpected_stream_errors_remain_visible(self):
        with self.server() as (process, ipc):
            process.stdin.write(b'\xff\n')
            process.stdin.flush()
            _, stderr = process.communicate(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b'UnicodeDecodeError', stderr)


if __name__ == '__main__':
    unittest.main()
