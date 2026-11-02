"""Public action receipts preserve only supported, visible inventory changes."""
import copy
import unittest

from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


def receipt(events):
    return {**observation(), 'transition': {'stop_reason': 'action_completed', 'complete': True, 'events': events}}


class InventoryEventTests(unittest.TestCase):
    def test_added_cards_preserve_their_public_destination_in_all_action_receipts(self):
        for pile in ('deck', 'hand', 'draw', 'discard', 'exhaust', 'play', None):
            event = {'sequence': 1, 'type': 'card_added', 'card': {'id': 11, 'name': 'Anger'}, 'pile': pile}
            for operation in ('play_card', 'end_turn', 'select_card', 'claim_reward', 'buy_item'):
                raw = {**event, 'hidden_draw_position': 2}
                with self.subTest(pile=pile, operation=operation):
                    state = receipt([raw])
                    if operation == 'claim_reward':
                        state['reward_result'] = {'reward_id': 1, 'status': 'claimed'}
                    public = player_result({'ok': True, 'state': inspection_details(operation, state)})
                    self.assertEqual(public['transition']['events'], [event])

    def test_added_cards_require_a_valid_destination_or_explicit_unknown(self):
        event = {'sequence': 1, 'type': 'card_added', 'card': {'id': 11, 'name': 'Anger'}}
        for invalid in (event, *({**event, 'pile': pile} for pile in ('none', 'top', '', 0, False, [], {}))):
            with self.subTest(event=invalid), self.assertRaises(ValueError):
                inspection_details('play_card', receipt([invalid]))

    def test_unidentified_combat_cards_do_not_gain_a_name_from_the_destination(self):
        event = {'sequence': 1, 'type': 'card_added', 'card': {'id': 11, 'name': None}, 'pile': None}
        public = player_result({'ok': True, 'state': inspection_details('end_turn', receipt([event]))})
        self.assertEqual(public['transition']['events'], [event])
        with self.assertRaises(ValueError):
            inspection_details('end_turn', receipt([{**event, 'pile': 'deck'}]))

    def test_inventory_events_survive_public_receipts_without_model_details(self):
        events = [
            {'sequence': 1, 'type': 'relic_obtained', 'relic': {'name': 'Whetstone'}},
            {'sequence': 2, 'type': 'card_upgraded', 'card': {'id': 9, 'name': 'Bash'}, 'pile': 'deck'},
            {'sequence': 3, 'type': 'relic_removed', 'relic': {'name': 'Burning Blood'}},
            {'sequence': 4, 'type': 'potion_obtained', 'potion': {'slot_index': 0, 'name': 'Block Potion'}},
            {'sequence': 5, 'type': 'card_removed', 'card': {'id': 8, 'name': 'Strike'}, 'pile': 'deck'},
            {'sequence': 6, 'type': 'card_added', 'card': {'id': 11, 'name': 'Anger'}, 'pile': 'deck'},
            {'sequence': 7, 'type': 'card_downgraded', 'card': {'id': 9, 'name': 'Bash+'}, 'pile': 'deck'},
            {'sequence': 8, 'type': 'card_enchantment_changed', 'card': {'id': 11, 'name': 'Anger'}, 'pile': 'deck'},
        ]
        for operation in ('choose_event_option', 'choose_ancient_option', 'selection_option', 'buy_item', 'end_turn'):
            raw = copy.deepcopy(events)
            raw[0]['relic']['model_id'] = 'PRIVATE'
            raw[5]['hidden_draw_position'] = 1
            with self.subTest(operation=operation):
                public = player_result({'ok': True, 'state': inspection_details(operation, receipt(raw))})
                self.assertEqual(public['transition']['events'], events)

    def test_permanent_card_changes_require_deck_scope_and_public_identity(self):
        for kind in ('card_removed', 'card_upgraded', 'card_downgraded', 'card_enchantment_changed'):
            valid = {'sequence': 1, 'type': kind, 'card': {'id': 9, 'name': 'Bash'}, 'pile': 'deck'}
            invalid = [{**valid, 'pile': 'hand'}, {k: v for k, v in valid.items() if k != 'pile'},
                       {**valid, 'card': {'id': -1, 'name': 'Bash'}},
                       {**valid, 'card': {'id': True, 'name': 'Bash'}},
                       {**valid, 'card': {'id': 9, 'name': None}}]
            for event in invalid:
                with self.subTest(kind=kind, event=event), self.assertRaises(ValueError):
                    inspection_details('selection_option', receipt([event]))

    def test_inventory_identity_and_scopes_are_validated(self):
        invalid = [
            {'type': 'relic_obtained'}, {'type': 'relic_removed', 'relic': {}},
            {'type': 'relic_obtained', 'relic': {'name': None}},
            {'type': 'potion_obtained', 'potion': {'slot_index': -1, 'name': 'Block Potion'}},
            {'type': 'potion_obtained', 'potion': {'slot_index': 0, 'name': None}},
            {'type': 'card_added', 'card': {'id': 1, 'name': 'Anger'}, 'pile': 'top'},
        ]
        for event in invalid:
            with self.subTest(event=event), self.assertRaises(ValueError):
                inspection_details('choose_event_option', receipt([{'sequence': 1, **event}]))


if __name__ == '__main__':
    unittest.main()
