OBSERVATION_SCHEMA = {
    'type': 'object',
    'properties': {'preset': {
        'type': 'string', 'enum': ['full', 'actions_only', 'summary', 'top_bar'], 'default': 'full',
        'description': 'full keeps basic observations; summary compacts cards (including result unlocks), combat, and top bars, omitting event narrative, false warnings, and divination instructions; actions_only keeps context and tool names; top_bar adds values and relic_count without relic details. All refresh action permission.',
    }},
    'additionalProperties': False,
}


def preset_arguments(arguments):
    if arguments is None:
        return 'full'
    if not isinstance(arguments, dict) or set(arguments) - {'preset'}:
        raise ValueError('get_observation accepts only the optional preset field.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'actions_only', 'summary', 'top_bar'):
        raise ValueError('Invalid observation preset.')
    return preset


def observation_preset(payload, preset):
    if preset == 'full' or 'error' in payload:
        return payload
    if preset == 'summary':
        return observation_summary(payload)
    result = {key: payload[key] for key in ('scene', 'screen', 'available_actions')}
    if payload.get('selection') is not None:
        result['selection'] = {key: payload['selection'][key] for key in ('type', 'status')}
    if preset == 'top_bar':
        from sts2_mcp.output.null_fields import apply_preset
        bar = apply_preset(payload, 'default').get('top_bar')
        if bar is not None:
            result['top_bar'] = {key: value for key, value in bar.items() if key != 'relics'}
    return result


def actions_only_result(payload, preset='full'):
    return payload if 'error' in payload else observation_preset(payload, 'actions_only')


def observation_summary(payload):
    from sts2_mcp.output.card_format import card_summary
    from sts2_mcp.output.null_fields import apply_preset
    from sts2_mcp.output.selection_summary import selection_summary
    from sts2_mcp.output.top_bar_summary import top_bar_summary
    result = apply_preset(payload, 'default')
    if result.get('top_bar') is not None:
        result['top_bar'] = top_bar_summary(result['top_bar'])
    if payload['screen'].get('view') in {'map', 'deck', 'draw_pile', 'discard_pile', 'exhaust_pile'}:
        return browsing_summary(result)
    if result.get('selection') is not None:
        result['selection'] = selection_summary(result['selection'])
    if result.get('run_result') is not None:
        result['run_result']['cards'] = [card_summary(card) for card in result['run_result']['cards']]
    for item in (result.get('shop') or {}).get('items') or []:
        if item['kind'] == 'card':
            item['card'] = card_summary(item['card'])
    if result.get('event') is not None:
        event = result['event']
        event.pop('description', None)
        for option in event.get('options', []):
            if option.get('lethal_warning') is False:
                option.pop('lethal_warning')
    if result.get('divination') is not None:
        result['divination'].pop('instructions', None)
    if payload['scene'] != 'combat':
        return result

    def unit_summary(compact, original):
        status = original.get('hp_display')
        hp, maximum = original.get('hp'), original.get('max_hp')
        health = {'infinite': '∞', 'dead': 'dead', 'unknown': 'unknown'}.get(status)
        if status == 'numeric' and type(hp) is int and type(maximum) is int:
            health = f'{hp}/{maximum}'
        for key in ('hp', 'max_hp', 'hp_display'):
            compact.pop(key, None)
        compact['health'] = health
        for key in ('powers', 'orb_slots', 'sovereign_blades'):
            if compact.get(key) == []:
                compact.pop(key)

    if result.get('player') is not None:
        player, original = result['player'], payload['player']
        unit_summary(player, original)
        from sts2_mcp.output.resource_summary import resource_summary
        player = result['player'] = resource_summary(player)
        if 'hand' in player:
            player['hand'] = [card_summary(card) for card in player['hand']]
    for key in ('enemies', 'allies'):
        for compact, original in zip(result.get(key) or [], payload.get(key) or [], strict=True):
            unit_summary(compact, original)
    return result


def browsing_summary(payload):
    if payload['screen'].get('view') == 'deck' and payload.get('deck') is not None:
        from sts2_mcp.output.card_format import card_summary
        payload['deck'] = [card_summary(card) for card in payload['deck']]
    # Map and combat pile content retain their pending review projection.
    return payload
