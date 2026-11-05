import copy
import unittest

from sts2_mcp.output.null_fields import apply_preset
from sts2_mcp.output.transition_details import end_turn_details
from tests.python.test_selection import state


class SelectionEventTests(unittest.TestCase):
    def result(self, events):
        value = state()
        value['transition'] = {'stop_reason': 'choice_required', 'complete': True, 'events': events}
        return end_turn_details(value)['transition']['events']

    def test_selection_changes_keep_only_public_card_identity_and_order(self):
        events = [
            {'sequence': 1, 'type': 'card_deselected', 'card': {'id': 5, 'name': 'Defend'}},
            {'sequence': 2, 'type': 'card_selected', 'card': {'id': 8, 'name': 'Strike'}},
        ]
        self.assertEqual(self.result(events), events)

    def test_unknown_selected_card_does_not_acquire_a_name_under_default(self):
        event = {'sequence': 1, 'type': 'card_selected', 'card': {'id': 5, 'name': None}}
        actual = {'transition': {'events': self.result([event])}}
        self.assertEqual(apply_preset(actual, 'default'), actual)

    def test_selection_events_reject_unrelated_gameplay_fields(self):
        for kind in ('card_selected', 'card_deselected'):
            for extra in ({'pile': 'deck'}, {'target': {'id': 0, 'kind': 'player', 'name': 'The Ironclad'}},
                          {'before': 0, 'after': 1}, {'autoplay': False}):
                event = {'sequence': 1, 'type': kind, 'card': {'id': 5, 'name': 'Defend'}, **extra}
                with self.subTest(kind=kind, extra=extra), self.assertRaises(ValueError):
                    self.result([event])

    def test_selection_events_reject_missing_identity_and_bad_order(self):
        base = {'sequence': 1, 'type': 'card_selected', 'card': {'id': 5, 'name': 'Defend'}}
        for invalid in ({'sequence': 1, 'type': 'card_selected'},
                        {**base, 'card': {'id': -1, 'name': 'Defend'}}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.result([invalid])
        with self.assertRaises(ValueError):
            self.result([base, copy.deepcopy(base)])

    def test_selection_events_filter_private_card_fields(self):
        event = {'sequence': 1, 'type': 'card_selected', 'card': {'id': 5, 'name': 'Defend', 'seed': 'private'}}
        self.assertEqual(self.result([event]), [
            {'sequence': 1, 'type': 'card_selected', 'card': {'id': 5, 'name': 'Defend'}}])
