import argparse
import json
import time
from pathlib import Path

from inspection_details import inspection_details
from player_output import player_result
from roundtrip_client import Client


def main():
    parser = argparse.ArgumentParser(description='验证隔离实例中的原生药水使用与丢弃。')
    parser.add_argument('--scenario', default='basic')
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    client = Client(root / '.tmp/roundtrip/ipc')
    evidence = []
    actions = {'start_test_combat', 'use_potion', 'discard_potion', 'select_card', 'selection_option'}

    def call(operation, arguments=None, error=None, stale_retries=0, decision=None):
        before = call('get_state') if operation in actions else None
        if decision is not None:
            assert (before['scene'], before['combat_generation'], before['potion_generation']) == decision, before
            if error is None:
                q = call('inspect_targets', {'potion_slot': arguments['potion_slot']})
                assert q['usable'] if operation == 'use_potion' else q['discardable'], q
                if 'target_id' in arguments:
                    assert any(t['id'] == arguments['target_id'] for t in q['targets']), q
        response = client.call(operation, before['snapshot_id'] if before else None, arguments=arguments)
        evidence.append({'operation': operation, 'arguments': arguments, 'response': response})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')
        if (error != 'stale_state' and not response['ok'] and response['error']['code'] == 'stale_state'
                and operation in {'use_potion', 'discard_potion'} and stale_retries < 4):
            # stale_state is a known no-input refusal; revalidate the same decision after observing.
            return call(operation, arguments, error=error, stale_retries=stale_retries + 1,
                        decision=(before['scene'], before['combat_generation'], before['potion_generation']))
        if error:
            assert not response['ok'] and response['error']['code'] == error, response
            return response
        assert response['ok'], response
        if operation not in {'start_test_combat', 'check_test_potion_state', 'replace_test_potion'}:
            inspection_details(operation, response['state'], arguments)
        return response['state']

    state = call('get_state')
    deadline = time.monotonic() + 30
    while state['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        time.sleep(.1)
        state = call('get_state')
    assert state['scene'] == 'main_menu', '只允许新启动的隔离实例。'
    call('start_test_combat')
    state = call('get_state')
    assert 'discard_potion' in state['available_actions'] or args.scenario == 'blocked', 'Native potion actions are missing'

    def query(slot=0):
        return call('inspect_targets', {'potion_slot': slot})

    def use(slot=0):
        q = query(slot)
        assert q['usable'], q
        result = call('use_potion', {'potion_slot': slot,
                                   **({'target_id': q['targets'][0]['id']} if q['requires_target'] else {})})
        assert result['transition']['complete'], result
        if args.scenario != 'cancel':
            assert any(e['type'] == 'potion_used' and e['potion']['slot_index'] == slot
                       for e in result['transition']['events']), result
        return result

    before = call('get_state')
    diagnostic = call('check_test_potion_state')
    if args.scenario == 'noncombat_reward':
        assert diagnostic['reward_visible'], 'The potion reward screen must remain visible'
    q = query()
    assert call('check_test_potion_state') == diagnostic, 'Read-only query changed native state'
    assert call('get_state')['snapshot_id'] == before['snapshot_id'], 'Read-only query changed observation'
    scenario = args.scenario
    if scenario == 'basic':
        assert q['requires_target'] and q['targets'], q
        for invalid in [None, {}, {'potion_slot': True}, {'potion_slot': '0'}, {'potion_slot': -1},
                        {'potion_slot': 0, 'target_id': None}, {'potion_slot': 0, 'card_id': 1}]:
            call('use_potion', invalid, error='invalid_request')
        call('use_potion', {'potion_slot': 0}, error='illegal_action')
        call('use_potion', {'potion_slot': 0, 'target_id': 0}, error='illegal_action')
        call('use_potion', {'potion_slot': 0, 'target_id': 2**32 - 1}, error='illegal_action')
        call('discard_potion', {'potion_slot': 999}, error='illegal_action')
        result = use()
        assert any(e['type'] == 'damage' and e['source']['kind'] == 'potion' for e in result['transition']['events']), result
        assert result['top_bar']['potion_slots'][0] is None
        call('use_potion', {'potion_slot': 0}, error='illegal_action')
        call('use_potion', {'potion_slot': 1, 'target_id': 0}, error='illegal_action')
        result = use(1)
        assert any(e['type'] == 'block_changed' for e in result['transition']['events']), result
        automatic = query(2)
        assert not automatic['usable'] and automatic['discardable'], automatic
        call('use_potion', {'potion_slot': 2}, error='illegal_action')
        result = call('discard_potion', {'potion_slot': 2})
        assert any(e['type'] == 'potion_discarded' for e in result['transition']['events']), result
        assert result['top_bar']['potion_slots'] == [None, None, None]
    elif scenario.startswith('noncombat') or scenario == 'fruit_combat':
        assert not q['requires_target'] and q['target_type'] == 'any_player', q
        if scenario.startswith('noncombat'):
            assert state['player'] is None and state['enemies'] is None and state['turn'] is None, state
            assert q['targets'][0]['id'] == 'self', q
        hp, maximum = state['top_bar']['hp'], state['top_bar']['max_hp']
        result = use()
        assert result['top_bar']['max_hp'] == maximum + 5, result
        result = use(1)
        assert result['top_bar']['hp'] > hp, result
        blocked = query(2)
        assert blocked['discardable'], blocked
        if scenario.startswith('noncombat'):
            assert not blocked['usable'], blocked
            call('use_potion', {'potion_slot': 2}, error='illegal_action')
        call('discard_potion', {'potion_slot': 2})
    elif scenario in {'skill', 'attack', 'power', 'colorless', 'memories', 'gamblers'}:
        result = use()
        assert result['transition']['stop_reason'] == 'choice_required', result
        assert 'use_potion' not in result['available_actions'] and 'discard_potion' not in result['available_actions']
        call('use_potion', {'potion_slot': 1}, error='illegal_action')
        call('discard_potion', {'potion_slot': 1}, error='illegal_action')
        selection = result['selection']
        if selection['can_view_battlefield']:
            call('set_selection_view', {'view': 'battlefield'})
            peek = call('get_state')
            assert 'use_potion' not in peek['available_actions']
            call('inspect_potions')
            call('discard_potion', {'potion_slot': 1}, error='illegal_action')
            call('set_selection_view', {'view': 'selection'})
        deadline = time.monotonic() + 5
        current = call('get_state')
        while 'select_card' not in current['available_actions'] and time.monotonic() < deadline:
            time.sleep(.1)
            current = call('get_state')
        chosen = current['selection']['cards'][0]['id']
        result = call('select_card', {'card_id': chosen})
        if result['selection'] is not None:
            option = next(o for o in result['selection']['options'] if o['id'] == 'confirm' and o['enabled'])
            result = call('selection_option', {'option_id': option['id']})
        assert result['transition']['stop_reason'] == 'player_ready', result
    elif scenario == 'blocked':
        assert not q['usable'] and not q['discardable'], q
        call('use_potion', {'potion_slot': 0}, error='illegal_action')
        call('discard_potion', {'potion_slot': 0}, error='illegal_action')
    elif scenario in {'merchant_map', 'merchant_inventory'}:
        assert not q['usable'] and q['requires_target'] and q['targets'] == [], q
        call('use_potion', {'potion_slot': 0, 'target_id': 'merchant'}, error='illegal_action')
        call('discard_potion', {'potion_slot': 0})
    elif scenario == 'merchant':
        assert q['requires_target'] and q['targets'][0]['id'] == 'merchant', q
        call('use_potion', {'potion_slot': 0}, error='illegal_action')
        gold = state['top_bar']['gold']
        result = use()
        assert result['transition']['stop_reason'] == 'action_completed', result
        assert result['top_bar']['gold'] == gold + 100, result
    elif scenario in {'victory', 'death', 'aoe'}:
        result = use()
        expected = {'victory': 'combat_won', 'death': 'combat_lost', 'aoe': 'player_ready'}[scenario]
        assert result['transition']['stop_reason'] == expected, result
        assert any(e['type'] == 'damage' for e in result['transition']['events']), result
    elif scenario == 'cancel':
        result = use()
        assert result['transition']['stop_reason'] == 'action_canceled', result
    elif scenario == 'fairy_rescue':
        result = use()
        assert result['transition']['stop_reason'] == 'player_ready' and result['player']['hp'] > 0, result
        assert {e['potion']['slot_index'] for e in result['transition']['events'] if e['type'] == 'potion_used'} == {0, 2}, result
    elif scenario == 'replace':
        old = state['snapshot_id']
        call('replace_test_potion')
        changed = call('get_state')
        assert changed['top_bar']['potion_slots'] == state['top_bar']['potion_slots']
        assert changed['snapshot_id'] != old, 'Replacing an identical potion must invalidate the old slot permission'
        result = client.call('discard_potion', old, arguments={'potion_slot': 0})
        assert not result['ok'] and result['error']['code'] == 'stale_state', result
    elif scenario == 'unhittable':
        assert all(t['id'] != state['enemies'][0]['id'] for t in q['targets']), q
        call('use_potion', {'potion_slot': 0, 'target_id': state['enemies'][0]['id']}, error='illegal_action')
        use()
    elif scenario == 'entropic':
        result = use()
        assert all(result['top_bar']['potion_slots']), result
    else:
        raise AssertionError('Unknown scenario: ' + scenario)
    print('PASS native potion scenario:', scenario)


if __name__ == '__main__':
    main()
