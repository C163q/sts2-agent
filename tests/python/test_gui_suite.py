import json
import subprocess
import sys
from unittest.mock import patch
import tempfile
import unittest
from pathlib import Path

import tests.game.suite as gui_suite


class SessionDouble:
    def __init__(self, fail_step=None, wrong_run=False):
        self.current = 0
        self.fail_step = fail_step
        self.wrong_run = wrong_run
        self.executed = []
        self.resets = 0

    def begin_run(self, scenarios):
        self.current += 1
        return self.identity()

    def identity(self):
        return {'process_id': 123, 'session': 'game-one', 'run_id': self.current}

    def run_step(self, step, directory):
        self.executed.append(step['name'])
        directory.mkdir()
        if self.wrong_run:
            self.current += 1
        if step['name'] == self.fail_step:
            raise RuntimeError('Verifier failed')
        return {'returncode': 0}

    def reset_run(self):
        self.resets += 1


class GuiSuiteTests(unittest.TestCase):
    def test_discard_fixture_names_are_not_use_verifier_arguments(self):
        for verifier in ('verify_potion_recovery.py', 'verify_use_potion_review.py'):
            with self.subTest(verifier=verifier), self.assertRaises(ValueError):
                self.load([{'name': 'discard_fixture', 'scenarios': {'potion': 'discard_fault'},
                    'steps': [{'name': 'check', 'verifier': verifier, 'args': ['--scenario', 'discard_fault']}]}])

    def fake_verifier(self, root, name, source):
        directory = root / 'tests/game/verifiers'
        directory.mkdir(parents=True)
        for package in (root / 'tests', root / 'tests/game', directory):
            (package / '__init__.py').write_text('')
        script = directory / name
        script.write_text(source)
        return script

    def test_selection_metadata_does_not_change_run_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            session = gui_suite.GameSession(Path(directory), sys.executable)
            reply = {'state': {'process_id': 123, 'session': 'game-one', 'run_id': 'run-one'}}
            with patch.object(session, 'request', return_value=reply):
                self.assertEqual(session.identity(), {'process_id': 123, 'session': 'game-one', 'run_id': 'run-one'})
                reply['state']['selection_view'] = 'visible'
                self.assertEqual(session.identity(), {'process_id': 123, 'session': 'game-one', 'run_id': 'run-one'})

    def load(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'suite.json'
            path.write_text(json.dumps(value))
            return gui_suite.load_cases(path)

    def cases(self):
        return [
            {'name': 'first', 'scenarios': {'play': 'basic'}, 'steps': [
                {'name': 'a', 'verifier': 'verify_action_observations.py', 'args': []},
                {'name': 'b', 'verifier': 'verify_suite_continuation.py', 'args': []}]},
            {'name': 'second', 'scenarios': {'rest': 'smith'}, 'steps': [
                {'name': 'c', 'verifier': 'verify_rest_site.py', 'args': ['--scenario', 'smith']}]}]

    def test_new_runs_and_explicit_steps_preserve_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SessionDouble()
            result = gui_suite.execute_cases(self.cases(), session, Path(directory))
            self.assertEqual(result['status'], 'passed')
            self.assertEqual([c['identity']['run_id'] for c in result['cases']], [1, 2])
            self.assertEqual(session.executed, ['a', 'b', 'c'])
            self.assertEqual(session.resets, 2)
            saved = json.loads((Path(directory) / 'report.json').read_text())
            self.assertEqual(saved['status'], 'passed')
            self.assertIn('duration_seconds', saved['cases'][0]['steps'][0])

    def test_failure_stops_later_steps_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SessionDouble(fail_step='a')
            result = gui_suite.execute_cases(self.cases(), session, Path(directory))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(session.executed, ['a'])
            self.assertEqual(session.resets, 0)
            self.assertIn('Verifier failed', result['cases'][0]['error'])
            self.assertTrue((Path(directory) / 'first/a').is_dir())

    def test_unexpected_run_change_fails_same_run_group(self):
        with tempfile.TemporaryDirectory() as directory:
            session = SessionDouble(wrong_run=True)
            result = gui_suite.execute_cases(self.cases(), session, Path(directory))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(session.executed, ['a'])

    def test_keyboard_interrupt_is_recorded_and_stops_later_cases(self):
        class Interrupted(SessionDouble):
            def run_step(self, step, directory):
                self.executed.append(step['name'])
                raise KeyboardInterrupt()
        with tempfile.TemporaryDirectory() as directory:
            session = Interrupted()
            result = gui_suite.execute_cases(self.cases(), session, Path(directory))
            self.assertEqual(result['status'], 'interrupted')
            self.assertEqual(session.executed, ['a'])
            self.assertEqual(session.resets, 0)
            self.assertEqual(json.loads((Path(directory) / 'report.json').read_text())['status'], 'interrupted')

    def test_cleanup_failure_stops_before_next_run(self):
        class BrokenCleanup(SessionDouble):
            def reset_run(self):
                raise RuntimeError('Cleanup incomplete')
        with tempfile.TemporaryDirectory() as directory:
            session = BrokenCleanup()
            result = gui_suite.execute_cases(self.cases(), session, Path(directory))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(session.executed, ['a', 'b'])
            self.assertIn('Cleanup incomplete', result['cases'][0]['error'])

    def test_rejects_ambiguous_or_unsafe_manifests(self):
        invalid = [[], [{'name': '../outside', 'scenarios': {}, 'steps': []}],
                   [{'name': 'x', 'scenarios': {'rest': 'unknown'}, 'steps': []}],
                   [{'name': 'x', 'scenarios': {'ending': 'death'}, 'steps': []}],
                   [{'name': 'x', 'scenarios': {}, 'steps': [
                       {'name': 'step', 'verifier': '../mcp_server.py', 'args': []}]}]]
        invalid.append([{'name': 'x', 'scenarios': {}, 'steps': [
            {'name': 'step', 'verifier': 'verify_run_ending.py', 'args': []}]}])
        cases = self.cases()
        invalid.append([cases[0], cases[0]])
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.load(value)
        self.assertEqual(len(self.load(self.cases())), 2)

    def test_timed_out_verifier_and_its_children_are_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = self.fake_verifier(root, 'verify_owned.py', """import argparse, subprocess, sys, time
p=argparse.ArgumentParser(); p.add_argument('--report'); args=p.parse_args()
child=subprocess.Popen([sys.executable, '-c', 'import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(30)'])
open(args.report,'w').write(str(child.pid))
time.sleep(30)
""")
            session = gui_suite.GameSession(root / 'game', sys.executable, step_timeout=1)
            step_dir = root / 'step'
            with patch.object(gui_suite, 'ROOT', root), self.assertRaises(subprocess.TimeoutExpired):
                session.run_step({'name': 'owned', 'verifier': script.name, 'args': []}, step_dir)
            child = int((step_dir / 'evidence.json').read_text())
            # Reparented killed children may briefly remain zombies until init reaps them.
            status = Path(f'/proc/{child}/stat')
            import time
            deadline = time.monotonic() + 2
            def running():
                try:
                    return status.read_text().split()[2] != 'Z'
                except (FileNotFoundError, ProcessLookupError):
                    return False
            while running() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertFalse(running())

    def test_reserved_names_and_cli_shortcuts_are_rejected(self):
        for name, args in [('game', []), ('safe', ['--help']), ('safe', ['--rep', '/tmp/other.json'])]:
            case = {'name': name, 'scenarios': {}, 'steps': [
                {'name': 'step', 'verifier': 'verify_action_observations.py', 'args': args}]}
            with self.subTest(name=name, args=args), self.assertRaises(ValueError):
                self.load([case])

    def test_zero_exit_without_evidence_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            script = self.fake_verifier(root, 'verify_empty.py', "print('No test executed')")
            session = gui_suite.GameSession(root / 'game', sys.executable)
            with patch.object(gui_suite, 'ROOT', root), self.assertRaises(RuntimeError):
                session.run_step({'name': 'empty', 'verifier': script.name, 'args': []}, root / 'step')

    def test_existing_report_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            path.write_text('old evidence')
            with self.assertRaises(FileExistsError):
                gui_suite.execute_cases(self.cases(), SessionDouble(), Path(directory))
            self.assertEqual(path.read_text(), 'old evidence')


if __name__ == '__main__':
    unittest.main()
