"""Public companion identities, hover sources and redirected-damage receipts."""
import copy
import unittest

from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.player_output import player_result
from tests.python.test_output_boundaries import observation


def details():
    return {'scene': 'combat', 'player': {'powers': [], 'sovereign_blades': [{'id': 7, 'name': 'Sovereign Blade'}]},
            'allies': [{'id': 4, 'name': 'Osty', 'powers': [{'name': 'Die For You', 'amount': None}]}],
            'enemies': [], 'hover_tips': [
                {'title': 'Die For You', 'description': 'Absorb attack damage.', 'sources': ['allies.0.powers.0']},
                {'title': 'Sovereign Blade', 'description': 'Deal 15 damage.', 'sources': ['player.sovereign_blades.0']}]}


class CompanionTests(unittest.TestCase):
    def test_observation_preserves_visible_allies_without_exposing_body_text(self):
        state = observation()
        ally = {'id': 4, 'name': 'Osty', 'hp': 8, 'max_hp': 8, 'hp_display': 'numeric',
                'block': 3, 'block_shared_with': 'player', 'powers': []}
        state['allies'] = [{**ally, 'hidden_next_move': 'secret', 'description': 'Hover only.'}]
        state['player']['sovereign_blades'] = [{'id': 7, 'name': 'Sovereign Blade', 'damage': 15,
                                               'description': 'Hover only.', 'pile': 'draw'}]
        clean = player_result({'ok': True, 'state': inspection_details('get_state', state)})
        self.assertEqual(clean.get('allies'), [ally])
        self.assertEqual(clean['player'].get('sovereign_blades'), [{'id': 7, 'name': 'Sovereign Blade'}])

    def test_unknown_allies_differ_from_a_visible_empty_battlefield(self):
        for allies in (None, []):
            with self.subTest(allies=allies):
                clean = inspection_details('get_state', {**observation(), 'allies': allies})
                self.assertIn('allies', clean)
                self.assertEqual(clean['allies'], allies)

    def test_detail_sources_resolve_to_allied_powers_and_visible_blades(self):
        self.assertEqual(inspection_details('inspect_combatants', details()), details())

    def test_detail_sources_reject_missing_or_malformed_companions(self):
        for source in ('allies.1.powers.0', 'allies.0.powers.1', 'allies.-1.powers.0',
                       'allies.0.intents.0', 'player.sovereign_blades.1', 'player.sovereign_blades.-1'):
            invalid = details()
            invalid['hover_tips'][0]['sources'] = [source]
            with self.subTest(source=source), self.assertRaises(ValueError):
                inspection_details('inspect_combatants', invalid)

    def test_companion_identity_validation_rejects_bool_negative_and_duplicate_ids(self):
        for key, invalid_id in (('allies', True), ('allies', -1), ('allies', 4294967296),
                                ('sovereign_blades', True), ('sovereign_blades', -1)):
            state = details()
            items = state['allies'] if key == 'allies' else state['player'][key]
            items[0]['id'] = invalid_id
            with self.subTest(key=key, invalid_id=invalid_id), self.assertRaises(ValueError):
                inspection_details('inspect_combatants', state)
        for key in ('allies', 'sovereign_blades'):
            state = details()
            items = state['allies'] if key == 'allies' else state['player'][key]
            items.append(copy.deepcopy(items[0]))
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspection_details('inspect_combatants', state)

    def test_allied_max_health_events_survive_validated_receipts(self):
        event = {'sequence': 1, 'type': 'max_hp_changed', 'target': {'id': 4, 'kind': 'ally', 'name': 'Osty'},
                 'before': 8, 'after': 13}
        state = {**observation(), 'transition': {'complete': True, 'stop_reason': 'player_ready', 'events': [event]}}
        self.assertEqual(inspection_details('play_card', state)['transition']['events'], [event])
        for change in ({'after': True}, {'before': None}, {'after': -1},
                       {'target': {'id': 4, 'kind': 'enemy', 'name': 'Enemy'}}):
            invalid = copy.deepcopy(state)
            invalid['transition']['events'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspection_details('play_card', invalid)


if __name__ == '__main__':
    unittest.main()
