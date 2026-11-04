"""Validate full inventory inspection against native entries and static top-bar data."""
import json


STATIC_FIELDS = {'name', 'counter', 'melted', 'grayed_out', 'pulsing'}


def assert_relic_inspection(result, raw_state, observed):
    assert set(result) <= {'relics', 'hover_tips', 'scene', 'screen', 'notes'}, result
    assert result['scene'] == observed['scene'] and result['screen'] == observed['screen'], result
    relics = result['relics']
    assert [{key: value for key, value in relic.items() if key in STATIC_FIELDS} for relic in relics] \
        == observed['top_bar']['relics'], (result, observed['top_bar'])
    unavailable = []
    for index, item in enumerate(relics):
        assert set(item) <= STATIC_FIELDS | {'description'}, item
        assert isinstance(item['name'], str) and item['name'], item
        assert item['counter'] is None or type(item['counter']) is int, item
        for field in ('melted', 'grayed_out', 'pulsing'):
            if field in item: assert item[field] is None or type(item[field]) is bool, item
        description = item['description']
        assert description is None or isinstance(description, str), item
        assert '[img]' not in (description or '') and '[gold]' not in (description or ''), item
        if description is None: unavailable.append(f'relics.{index}')
    assert (result.get('notes', {}).get('hover_tips_unavailable') or {}).get('sources', []) == unavailable, result
    tips = result['hover_tips']
    assert len(tips) == len({(tip['title'], tip['description']) for tip in tips}), tips
    expected = {(index, tip['title'], tip['description'])
                for index, relic in enumerate(raw_state['relics']) for tip in relic['hover_tips']}
    actual = {(index, tip['title'], tip['description']) for tip in tips for index in tip['relic_indices']}
    assert expected == actual, (expected, actual)
    for tip in tips:
        assert set(tip) == {'title', 'description', 'relic_indices'}, tip
        assert isinstance(tip['description'], str), tip
        indices = tip['relic_indices']
        assert indices == sorted(set(indices)) and indices, tip
        assert all(type(index) is int and 0 <= index < len(relics) for index in indices), tip
    assert not any('\u4e00' <= character <= '\u9fff' for character in json.dumps(result, ensure_ascii=False)), result
