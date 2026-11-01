from sts2_mcp.output.game_output import ANCIENT, ANCIENT_OPTION, TIP, project

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


def ancient_details(value, *, full=False):
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
        if (set(option) != set(shape['options'][0][0]) or option['id'] < 0 or option['id'] in ids
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
    if state.get('scene') != 'ancient': raise ValueError('Invalid ancient inspection scene.')
    return {'scene': 'ancient', 'ancient': ancient_details(state['ancient'], full=True)}
