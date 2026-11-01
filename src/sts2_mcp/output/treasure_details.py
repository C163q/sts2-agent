from sts2_mcp.output.game_output import TREASURE, TREASURE_RELIC, TIP, project


LOOT_SCHEMA = {'type': 'object', 'properties': {'open_only': {
    'type': 'boolean', 'default': False,
    'description': 'true opens the chest without taking its relic; false (default) also takes the relic. Does not proceed.',
}},
               'additionalProperties': False}


def loot_arguments(arguments):
    if arguments is None:
        return {}
    if not isinstance(arguments, dict) or set(arguments) - {'open_only'}:
        raise ValueError('Only open_only is accepted.')
    if 'open_only' in arguments and type(arguments['open_only']) is not bool:
        raise ValueError('open_only must be boolean.')
    return dict(arguments)


def treasure_details(value, *, full=False):
    relic_shape = {**TREASURE_RELIC, 'description': str, 'hover_tips': [TIP]} if full else TREASURE_RELIC
    result = project(value, {**TREASURE, 'relic': (relic_shape,)})
    if set(result) != set(TREASURE) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid treasure structure.')
    if result['status'] == 'covered':
        if full or any(result[key] is not None for key in ('chest', 'relic', 'proceed')):
            raise ValueError('Hidden treasure contents.')
        return result
    if result['chest'] not in {'closed', 'opening', 'open'}:
        raise ValueError('Invalid chest state.')
    relic = result['relic']
    if relic is not None and (result['chest'] != 'open' or set(relic) != set(relic_shape) or not relic['name']):
        raise ValueError('Invalid visible treasure relic.')
    if full and relic is not None and any(set(tip) != set(TIP) for tip in relic['hover_tips']):
        raise ValueError('Invalid treasure hover help.')
    proceed = result['proceed']
    if proceed is not None and (set(proceed) != {'text', 'enabled', 'skips_remaining'} or not proceed['text']):
        raise ValueError('Invalid treasure proceed button.')
    return result


def inspect_treasure_details(state):
    if state.get('scene') != 'treasure':
        raise ValueError('Invalid treasure inspection scene.')
    return {'scene': 'treasure', 'treasure': treasure_details(state['treasure'], full=True)}
