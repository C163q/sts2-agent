"""Assert the current combatant contract without freezing unrelated tool lists."""
from sts2_mcp.output.player_output import ENEMY_ATTACK_INTENT_NOTE


def assert_combatant_inspection(details, observed):
    assert {k: details[k] for k in ('scene', 'screen')} == {k: observed[k] for k in ('scene', 'screen')}
    assert {'scene', 'screen', 'player', 'enemies', 'allies', 'hover_tips'} <= details.keys(), details
    assert set(details) <= {'scene', 'screen', 'player', 'enemies', 'allies', 'hover_tips', 'notes'}, details
    if details['player'] is not None:
        assert set(details['player']) == {'powers', 'orb_slots', 'sovereign_blades'}, details['player']
        for key in details['player']:
            assert details['player'][key] == observed['player'][key], (key, details['player'], observed['player'])
    for group in ('enemies', 'allies'):
        actual = details[group]
        expected = observed[group]
        assert [item['id'] for item in actual] == [item['id'] for item in expected], (group, actual, expected)
        for item, original in zip(actual, expected, strict=True):
            keys = {'id', 'name', 'powers'} | ({'intents'} if group == 'enemies' else set())
            assert set(item) == keys, item
            for key in keys:
                assert item[key] == original[key], (group, key, item, original)
    tips = details['hover_tips']
    assert len(tips) == len({(tip['title'], tip['description']) for tip in tips}), tips
    for tip in tips:
        assert set(tip) == {'title', 'description', 'sources'}, tip
        assert isinstance(tip['description'], str), tip
        assert '[img]' not in tip['description'] and '[gold]' not in tip['description'], tip
        assert tip['sources'] and len(tip['sources']) == len(set(tip['sources'])), tip
        for source in tip['sources']:
            value = details
            for part in source.split('.'):
                value = value[int(part)] if isinstance(value, list) else value[part]
            assert isinstance(value, dict), (source, value)
    if 'enemy_attack_intents' in details.get('notes', {}):
        assert details['notes']['enemy_attack_intents'] == ENEMY_ATTACK_INTENT_NOTE
