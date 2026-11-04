"""Check full potion output against native slots and a same-screen observation."""
import json


def assert_potion_inspection(result, raw_state, observed):
    assert set(result) <= {'scene', 'screen', 'slot_tip', 'potion_slots', 'hover_tips', 'notes'}, result
    assert result['scene'] == observed['scene'] and result['screen'] == observed['screen'], result
    common = result['slot_tip']
    assert set(common) == {'title', 'description'} and isinstance(common['description'], str), common
    assert json.dumps(result).count(json.dumps(common['description'])) == 1
    slots, basic = result['potion_slots'], observed['top_bar']['potion_slots']
    assert len(slots) == len(basic)
    for potion, visible in zip(slots, basic):
        if visible is None:
            assert potion is None
        else:
            assert {k: v for k, v in potion.items() if k not in {'description'}} == visible, (potion, visible)
            assert potion['description'] is None or isinstance(potion['description'], str)
            assert '[img]' not in (potion['description'] or '') and '[gold]' not in (potion['description'] or '')
    tips = result['hover_tips']
    assert len(tips) == len({(tip['title'], tip['description']) for tip in tips})
    expected = {(i, tip['title'], tip['description']) for i, slot in enumerate(raw_state['potion_slots']) if slot
                for tip in slot['hover_tips']}
    actual = {(i, tip['title'], tip['description']) for tip in tips for i in tip['slot_indices']}
    assert expected == actual, (expected, actual)
    for tip in tips:
        assert set(tip) == {'title', 'description', 'slot_indices'}
        assert tip['slot_indices'] == sorted(set(tip['slot_indices'])) and tip['slot_indices']
