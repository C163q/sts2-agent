from sts2_mcp.output.observation_presets import observation_preset


def action_result(payload):
    """Project a validated action result after its permission has been handled."""
    if 'error' in payload:
        return payload
    result = observation_preset(payload, 'actions_only')
    result['transition'] = payload['transition']
    for key in ('purchase_result', 'reward_result', 'card_plays', 'potion_discard'):
        if key in payload:
            result[key] = payload[key]
    notes = {key: value for key, value in payload.get('notes', {}).items()
             if key in {'selection', 'interaction'}}
    if notes:
        result['notes'] = notes
    return result
