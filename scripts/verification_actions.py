async def confirm_transform(call, result, count=3):
    """Complete a native transform selection through the public tool contract."""
    assert result['transition']['stop_reason'] == 'choice_required', result
    assert result['selection']['type'] == 'deck_transform', result
    details = await call('inspect_selection')
    cards = details['selection']['cards'][:count]
    assert len(cards) == count, details
    for card in cards:
        result = await call('select_card', {'card_id': card['id']})
        assert result['transition']['stop_reason'] == 'choice_required', result
    assert len(result['selection']['transform_previews']) == count, result
    assert all(p['random'] and p['after'] is None for p in result['selection']['transform_previews']), result
    result = await call('selection_option', {'option_id': 'confirm'})
    assert result['transition']['complete'] and result['transition']['stop_reason'] == 'action_completed', result
    return result
