OBSERVATION_SCHEMA = {
    'type': 'object',
    'properties': {'preset': {
        'type': 'string', 'enum': ['full', 'actions_only', 'summary', 'top_bar'], 'default': 'full',
        'description': 'full/default/summary use static event/divination summaries and group map nodes by type. summary further compacts cards, combat and top bars; actions_only returns context and available tool names; top_bar adds top-bar values and relic_count without relic details.',
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
    if payload.get('shop') is not None:
        from sts2_mcp.output.shop_details import shop_summary
        result['shop'] = shop_summary(payload['shop'])
    if result.get('event') is not None:
        from sts2_mcp.output.event_presets import event_summary
        result['event'] = event_summary(result['event'])
    if result.get('divination') is not None:
        from sts2_mcp.output.event_presets import divination_summary
        result['divination'] = divination_summary(result['divination'])
    if payload['scene'] != 'combat':
        return result

    def unit_summary(compact, original):
        from sts2_mcp.output.combat_fields import health_summary
        health_summary(compact, original)
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
    from sts2_mcp.output.card_format import card_summary
    if payload['screen'].get('view') == 'deck' and payload.get('deck') is not None:
        payload['deck'] = [card_summary(card) for card in payload['deck']]
    if payload['screen'].get('view') in {'draw_pile', 'discard_pile', 'exhaust_pile'} and payload.get('cards') is not None:
        payload['cards'] = [card_summary(card) for card in payload['cards']]
        payload.pop('message', None)
    return payload
