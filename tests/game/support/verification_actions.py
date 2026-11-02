def full_output_arguments(name, arguments=None):
    """Pin legacy GUI checks to full output; explicit named presets still win."""
    if name == 'capture_screenshot':
        return arguments or {}
    return {'preset': 'full', **(arguments or {})}


async def observe_after_action(call, receipt):
    """Read current public details explicitly when a GUI check needs a snapshot."""
    if 'error' in receipt or 'transition' not in receipt or receipt['scene'] == 'main_menu':
        return receipt
    observation = await call('get_observation')
    return {**observation, **{key: receipt[key] for key in ('transition', 'purchase_result', 'reward_result') if key in receipt}}


def completed_action_snapshot(ipc, receipt):
    """Read the exact native response for stability checks without refreshing MCP permission."""
    from sts2_mcp.output.player_output import player_result
    from sts2_mcp.output.transition_details import end_turn_details

    return player_result({'ok': True, 'state': end_turn_details(completed_action_state(ipc, receipt))})


def completed_action_state(ipc, receipt):
    """Recover the native state and token belonging to a compact MCP receipt."""
    import json
    from sts2_mcp.output.action_output import action_result
    from sts2_mcp.output.player_output import player_result
    from sts2_mcp.output.transition_details import end_turn_details

    for path in sorted((ipc / 'responses').glob('*.json'), key=lambda p: p.stat().st_mtime_ns, reverse=True):
        response = json.loads(path.read_text())
        if response.get('ok') and 'transition' in response.get('state', {}):
            full = player_result({'ok': True, 'state': end_turn_details(response['state'])})
            if action_result(full) == receipt:
                return response['state']
    raise AssertionError('No native action response matches the compact MCP receipt.')


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
    preview = await call('inspect_selection')
    assert len(preview['selection']['transform_previews']) == count, preview
    assert all(p['random'] and p['after'] is None for p in preview['selection']['transform_previews']), preview
    result = await call('selection_option', {'option_id': 'confirm'})
    assert result['transition']['complete'] and result['transition']['stop_reason'] == 'action_completed', result
    return await observe_after_action(call, result)
