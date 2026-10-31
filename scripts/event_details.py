from game_output import ROOM_EVENT, ROOM_EVENT_OPTION, TIP, project

EVENT_OPTION_SCHEMA = {'type': 'object', 'properties': {'option_id': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647}},
                       'required': ['option_id'], 'additionalProperties': False}


def event_arguments(operation, arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'option_id'}
            or type(arguments['option_id']) is not int or not 0 <= arguments['option_id'] <= 2147483647):
        raise ValueError('A nonnegative option_id is required.')
    return dict(arguments)


def event_details(value, *, full=False):
    shape = {**ROOM_EVENT, 'options': ([{**ROOM_EVENT_OPTION, 'hover_tips': [TIP]}],)} if full else ROOM_EVENT
    result = project(value, shape)
    if set(result) != set(ROOM_EVENT) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid event state.')
    if result['status'] == 'covered':
        if full or any(result[key] is not None for key in set(ROOM_EVENT) - {'status'}):
            raise ValueError('Hidden event contents.')
        return result
    if result['options'] is None:
        raise ValueError('Missing event options.')
    ids = set()
    for option in result['options']:
        if (set(option) != set(shape['options'][0][0]) or not 0 <= option['id'] <= 2147483647 or option['id'] in ids
                or full and any(set(tip) != set(TIP) for tip in option['hover_tips'])):
            raise ValueError('Invalid event option.')
        ids.add(option['id'])
    if result['proceed'] is not None and set(result['proceed']) != {'text', 'enabled'}:
        raise ValueError('Invalid event proceed button.')
    return result


def inspect_event_details(state):
    if state.get('scene') != 'event': raise ValueError('Invalid event inspection scene.')
    if (state.get('divination') or {}).get('status') == 'visible':
        from divination_details import divination_details
        return {'scene': 'event', 'divination': divination_details(state['divination'])}
    return {'scene': 'event', 'event': event_details(state['event'], full=True)}
