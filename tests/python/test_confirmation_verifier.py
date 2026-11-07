"""Pin terminal inspection coverage in the maintained graphical verifier."""
import copy
import json
from pathlib import Path
import unittest

from tests.game.verifiers.verify_confirmation import validate_confirmation_outcome


class ConfirmationVerifierTests(unittest.TestCase):
    def outcome(self):
        sample = Path(__file__).resolve().parents[2] / 'docs/research/2026-11-07-confirmation-response-fixed-examples/confirm.full.json'
        return json.loads(sample.read_text())

    def test_actual_terminal_receipt_is_accepted(self):
        validate_confirmation_outcome(self.outcome())

    def test_empty_tools_gameplay_actions_and_wrong_scene_are_rejected(self):
        for mutation in ({'available_actions': []},
                         {'available_actions': ['inspect_run_result', 'respond_to_confirmation']},
                         {'scene': 'event'}):
            with self.subTest(mutation=mutation):
                result = copy.deepcopy(self.outcome()); result.update(mutation)
                with self.assertRaises(AssertionError):
                    validate_confirmation_outcome(result)
