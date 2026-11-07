"""Missing explicit IPC must fail before creating any screenshot verifier state."""
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tests.game.verifiers import verify_screenshots


class ScreenshotVerifierIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_or_blank_ipc_never_constructs_client_or_report(self):
        for value in (None, '', ' \t'):
            with self.subTest(value=value), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory) / 'new-report'
                args = SimpleNamespace(report=folder / 'evidence.json', scenario='menu')
                with mock.patch.dict(os.environ), mock.patch.object(verify_screenshots, 'Client',
                        side_effect=AssertionError('Client constructed before explicit IPC validation')) as client:
                    if value is None: os.environ.pop('STS2_AGENT_VERIFY_IPC_DIR', None)
                    else: os.environ['STS2_AGENT_VERIFY_IPC_DIR'] = value
                    with self.assertRaisesRegex(ValueError, 'STS2_AGENT_VERIFY_IPC_DIR'):
                        await verify_screenshots.verify(args)
                    client.assert_not_called()
                self.assertFalse(folder.exists())
