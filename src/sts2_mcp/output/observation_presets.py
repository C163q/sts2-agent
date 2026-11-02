OBSERVATION_SCHEMA = {
    'type': 'object',
    'properties': {'preset': {
        'type': 'string', 'enum': ['full', 'actions_only', 'summary', 'top_bar'], 'default': 'full',
        'description': 'full keeps basic observations; summary compacts combat resources and cards (default elsewhere); actions_only keeps context and tool names; top_bar adds top-bar values and relic_count, without relic details. All refresh action permission.',
    }},
    'additionalProperties': False,
}


def preset_arguments(arguments):
    if arguments is None:
        return 'full'
    if not isinstance(arguments, dict) or set(arguments) - {'preset'}:
        raise ValueError('Invalid observation arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'actions_only', 'summary', 'top_bar'):
        raise ValueError('Invalid observation preset.')
    return preset


def observation_preset(payload, preset):
    if preset == 'full' or 'error' in payload:
        return payload
    if preset == 'summary':
        return combat_summary(payload)
    result = {key: payload[key] for key in ('scene', 'screen', 'available_actions')}
    if payload.get('selection') is not None:
        result['selection'] = {key: payload['selection'][key] for key in ('type', 'status')}
    if preset == 'top_bar':
        from sts2_mcp.output.presets import apply_preset
        bar = apply_preset(payload, 'default').get('top_bar')
        if bar is not None:
            result['top_bar'] = {key: value for key, value in bar.items() if key != 'relics'}
    return result


def combat_summary(payload):
    from sts2_mcp.output.card_summary import card_summary
    from sts2_mcp.output.presets import apply_preset
    result = apply_preset(payload, 'default')
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
        energy, maximum = original.get('energy'), original.get('max_energy')
        player.pop('max_energy', None)
        player.pop('energy', None)
        if type(energy) is int and type(maximum) is int:
            player['energy'] = f'{energy}/{maximum}'
        if 'hand' in player:
            player['hand'] = [card_summary(card) for card in player['hand']]
    for key in ('enemies', 'allies'):
        for compact, original in zip(result.get(key) or [], payload.get(key) or [], strict=True):
            unit_summary(compact, original)
    if result.get('top_bar') is not None:
        result['top_bar'] = {key: value for key, value in result['top_bar'].items()
                             if key in {'gold', 'potion_slots', 'deck_count', 'relic_count'}}
    return result
