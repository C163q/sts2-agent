import argparse
import json
import os
import time
from pathlib import Path

from roundtrip_client import Client
from inspection_details import inspection_details


def main():
    parser = argparse.ArgumentParser(description='验证隔离游戏实例中的原生手动出牌。')
    parser.add_argument('--scenario', default='basic')
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    client = Client(root / '.tmp/roundtrip/ipc')
    evidence = []

    def call(op, arguments=None, *, error=None, stale_retries=0, decision=None):
        observed = call('get_state') if op in {'start_test_combat', 'play_card', 'end_turn', 'select_card', 'selection_option'} else None
        token = observed['snapshot_id'] if observed else None
        if decision is not None:
            assert (observed['combat_generation'], observed['turn']) == decision, observed
            assert any(card['id'] == arguments['card_id'] for card in observed['player']['hand']), observed
            query = call('inspect_targets', {'card_id': arguments['card_id']})
            assert query['playable'], query
            if query['requires_target']:
                assert any(target['id'] == arguments['target_id'] for target in query['targets']), query
        response = client.call(op, token, arguments=arguments)
        evidence.append({'operation': op, 'arguments': arguments, 'response': response})
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(evidence, indent=2) + '\n')
        if (not error and not response['ok'] and response['error']['code'] == 'stale_state'
                and op == 'play_card' and stale_retries < 4):
            # The Mod guarantees no input on stale_state; preserve and revalidate the same decision.
            return call(op, arguments, stale_retries=stale_retries + 1,
                        decision=(observed['combat_generation'], observed['turn']))
        if os.environ.get('PLAY_WINDOWED') and op == 'get_state':
            capture = root / '.tmp/roundtrip/observation.png'
            if capture.is_file():
                view = ((response.get('state') or {}).get('selection') or {}).get('status', 'combat')
                args.report.with_name(args.report.stem + '-' + view + '.png').write_bytes(capture.read_bytes())
        if error:
            assert not response['ok'] and response['error']['code'] == error, response
            return response
        assert response['ok'], response
        if op not in {'start_test_combat', 'check_test_play_state'}:
            inspection_details(op, response['state'], arguments)
        return response['state']

    def find(name):
        return next(card for card in call('get_state')['player']['hand'] if card['name'] == name)

    def play(card, target=None):
        query = call('inspect_targets', {'card_id': card['id']})
        assert query['playable'], query
        supplied = {'target_id': target or query['targets'][0]['id']} if query['requires_target'] else {}
        result = call('play_card', {'card_id': card['id'], **supplied})
        assert result['transition']['complete'], result
        if args.scenario != 'cancel':
            assert any(event['type'] == 'card_played' and event['card']['id'] == card['id']
                       and event['autoplay'] is False for event in result['transition']['events']), result
        return result

    state = call('get_state')
    deadline = time.monotonic() + 30
    while state['scene'] == 'loading_or_noncombat' and time.monotonic() < deadline:
        time.sleep(.1)
        state = call('get_state')
    assert state['scene'] == 'main_menu', '只允许新启动的隔离实例。'
    call('start_test_combat')
    state = call('get_state')
    assert 'play_card' in state['available_actions'], 'Native play_card action is missing'
    card = state['player']['hand'][0]
    scenario = args.scenario

    if scenario == 'basic':
        for invalid in [{'card_id': 'bad'}, {'card_id': True}, {'card_id': 7, 'target_id': None}, {'card_id': 7, 'extra': 1}]:
            call('play_card', invalid, error='invalid_request')
        query = call('inspect_targets', {'card_id': card['id']})
        assert query['requires_target'] and query['targets'], query
        call('play_card', {'card_id': card['id']}, error='illegal_action')
        call('play_card', {'card_id': card['id'], 'target_id': 4294967295}, error='illegal_action')
        own = call('inspect_targets', {'card_id': find('Defend')['id']})['targets'][0]['id']
        call('play_card', {'card_id': card['id'], 'target_id': own}, error='illegal_action')
        token = state['snapshot_id']
        result = play(card)
        assert result['transition']['stop_reason'] == 'player_ready', result
        assert any(event['type'] == 'damage' for event in result['transition']['events']), result
        stale = client.call('play_card', token, arguments={'card_id': find('Defend')['id']})
        assert not stale['ok'] and stale['error']['code'] == 'stale_state', stale
        card = find('Defend')
        call('play_card', {'card_id': card['id'], 'target_id': own}, error='illegal_action')
        result = play(card)
        assert any(event['type'] == 'block_changed' for event in result['transition']['events']), result
    elif scenario in {'energy', 'stars', 'unplayable', 'card_logic', 'ally', 'no_target'}:
        query = call('inspect_targets', {'card_id': card['id']})
        assert not query['playable'] and query['reason'], query
        if scenario in {'ally', 'no_target'}: assert query['targets'] == [], query
        target = {'target_id': query['targets'][0]['id']} if query['requires_target'] and query['targets'] else {}
        call('play_card', {'card_id': card['id'], **target}, error='illegal_action')
        if scenario == 'no_target':
            assert play(find('Defend'))['transition']['stop_reason'] == 'player_ready'
    elif scenario == 'unhittable':
        protected = state['enemies'][0]
        assert protected['hp'] > 0, protected
        for name in ['Strike', 'Sword Boomerang', 'Thunderclap']:
            candidate = find(name)
            query = call('inspect_targets', {'card_id': candidate['id']})
            assert query['playable'] and query['targets'], query
            assert all(target['id'] != protected['id'] for target in query['targets']), query
            if query['requires_target']:
                call('play_card', {'card_id': candidate['id'], 'target_id': protected['id']}, error='illegal_action')
            play(candidate)
        # Native reticle eligibility is not a prediction of every effect's recipients.
        # AttackCommand filters living creatures, so this mock can still receive AOE damage.
        call('get_state')
    elif scenario == 'hook':
        for _ in range(3): play(find('Defend'))
        card = find('Defend')
        assert not call('inspect_targets', {'card_id': card['id']})['playable']
        call('play_card', {'card_id': card['id']}, error='illegal_action')
    elif scenario == 'test_subject':
        query = call('inspect_targets', {'card_id': card['id']})
        assert query['targets'] and query['playable'], query
        enemy_id = query['targets'][0]['id']
        result = play(card)
        assert result['transition']['stop_reason'] == 'player_ready', result
        strike = find('Strike')
        assert not call('inspect_targets', {'card_id': strike['id']})['playable']
        for name in ['Defend', 'Sword Boomerang', 'Thunderclap']:
            remaining = find(name)
            query = call('inspect_targets', {'card_id': remaining['id']})
            assert not query['requires_target'], query
            if name != 'Defend': assert not query['targets'], query
            result = play(remaining)
            assert result['transition']['stop_reason'] == 'player_ready', result
        call('end_turn')
        revived = call('inspect_targets', {'card_id': find('Strike')['id']})['targets']
        assert revived and revived[0]['id'] == enemy_id, revived
    else:
        if scenario in {'random', 'random_empty'}:
            before = call('check_test_play_state')
            for _ in range(5):
                query = call('inspect_targets', {'card_id': card['id']})
                assert query['target_type'] == 'random_enemy' and not query['requires_target'], query
            after = call('check_test_play_state')
            assert before == after, (before, after)
            assert not after['targeting'] and not after['in_card_play'], after
        result = play(card)
        reason = result['transition']['stop_reason']
        if scenario in {'discovery', 'charge3', 'glimmer', 'armaments', 'armaments_free', 'armaments_filtered'}:
            assert reason == 'choice_required', result
            assert 'play_card' not in result['available_actions'], result
            if scenario == 'glimmer':
                assert len([e for e in result['transition']['events'] if e['type'] == 'card_drawn']) == 3, result
            detail = call('inspect_selection')
            cards = detail['selection']['cards']
            if scenario == 'discovery': assert len(cards) == 3, detail
            if scenario == 'charge3': assert len(cards) == 3, detail
            if scenario.startswith('armaments'):
                assert len(cards) == 2 and all(not c['name'].endswith('+') for c in cards), detail
            if detail['selection']['can_view_battlefield']:
                call('set_selection_view', {'view': 'battlefield'})
                call('play_card', {'card_id': card['id']}, error='illegal_action')
                call('inspect_targets', {'card_id': card['id']}, error='illegal_action')
                call('set_selection_view', {'view': 'selection'})
            for selected in cards[:detail['selection']['min_select']]:
                deadline = time.monotonic() + 3
                while 'select_card' not in call('get_state')['available_actions'] and time.monotonic() < deadline:
                    time.sleep(.05)
                result = call('select_card', {'card_id': selected['id']})
            if (result.get('selection') or {}).get('status') == 'visible':
                result = call('selection_option', {'option_id': 'confirm'})
            assert result['transition']['complete'] and result['transition']['stop_reason'] == 'player_ready', result
        elif scenario == 'victory': assert reason == 'combat_won', result
        elif scenario in {'death', 'thorns_death'}: assert reason == 'combat_lost', result
        elif scenario == 'cancel':
            assert reason == 'action_canceled' and not result['transition']['events'], result
        else:
            assert reason in {'player_ready', 'combat_won'}, result
            assert result.get('selection') is None, result
            if scenario.startswith('charge'):
                assert result['player']['draw_count'] == int(scenario[-1]), result
            if scenario in {'random', 'aoe', 'multi_hit'}:
                assert len([e for e in result['transition']['events'] if e['type'] == 'damage']) >= 2, result
            if scenario in {'armaments_one', 'armaments_none', 'armaments_upgraded'}:
                assert reason == 'player_ready', result
                assert len(result['player']['hand']) == 2 and all(c['name'].endswith('+') for c in result['player']['hand']), result
    print('PASS', scenario)


if __name__ == '__main__':
    main()
