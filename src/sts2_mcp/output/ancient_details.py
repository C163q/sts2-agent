from sts2_mcp.output.value_shapes import project, TIP
from sts2_mcp.output.contracts.rooms import ANCIENT, ANCIENT_OPTION

ANCIENT_OPTION_SCHEMA = {'type': 'object', 'properties': {'option_id': {
    'type': 'integer', 'minimum': 0, 'maximum': 2147483647,
    'description': 'An enabled ancient.options[].id from get_observation or inspect_ancient.',
}},
                         'required': ['option_id'], 'additionalProperties': False}


def ancient_arguments(operation, arguments):
    if operation != 'choose_ancient_option':
        if arguments is not None and (not isinstance(arguments, dict) or arguments):
            raise ValueError('This action accepts no arguments.')
        return None
    if (not isinstance(arguments, dict) or set(arguments) != {'option_id'}
            or type(arguments['option_id']) is not int or not 0 <= arguments['option_id'] <= 2147483647):
        raise ValueError('A nonnegative option_id is required.')
    return dict(arguments)


def ancient_details(value, *, full=False, require_warning=False):
    shape = {**ANCIENT, 'options': ([{**ANCIENT_OPTION, 'hover_tips': [TIP]}],)} if full else ANCIENT
    result = project(value, shape)
    if set(result) != set(ANCIENT) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid ancient state.')
    if result['status'] == 'covered':
        if full or any(result[key] is not None for key in set(ANCIENT) - {'status'}):
            raise ValueError('Hidden ancient contents.')
        return result
    if not result['name'] or result['dialogue'] is None or result['options'] is None:
        raise ValueError('Missing ancient contents.')
    ids = set()
    for option in result['options']:
        if (set(option) != (set(shape['options'][0][0]) if require_warning or 'lethal_warning' in option
                                else set(shape['options'][0][0]) - {'lethal_warning'})
                or not 0 <= option['id'] <= 2147483647 or option['id'] in ids
                or full and any(set(tip) != set(TIP) for tip in option['hover_tips'])):
            raise ValueError('Invalid ancient option.')
        ids.add(option['id'])
    if any(set(line) != {'speaker', 'text'} for line in result['dialogue']):
        raise ValueError('Invalid ancient dialogue.')
    for key in ('continue', 'proceed'):
        if result[key] is not None and set(result[key]) != {'text', 'enabled'}:
            raise ValueError('Invalid ancient button.')
    return result


def inspect_ancient_details(state):
    from sts2_mcp.output.scene_context import scene_context
    context = scene_context(state)
    if context['scene'] != 'ancient' or context['screen'] != {'status': 'visible'}:
        raise ValueError('Invalid ancient inspection context.')
    ancient = ancient_details(state['ancient'], full=True, require_warning=state.get('schema_version', 0) >= 46)
    sources = state.get('unavailable_hover_sources', [])
    possible = {'ancient.options.' + str(option['id']) for option in ancient['options'] if not option['hover_tips']}
    if (not isinstance(sources, list) or any(not isinstance(source, str) or source not in possible for source in sources)
            or len(sources) != len(set(sources))):
        raise ValueError('Invalid unavailable ancient option hover evidence.')
    result = {**context, 'ancient': ancient}
    if sources:
        result['unavailable_hover_sources'] = list(sources)
    return result
