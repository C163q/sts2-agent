from sts2_mcp.output.presentation_status import PAGE_STATUSES, READABLE_STATUSES
from sts2_mcp.output.value_shapes import project, TIP
from sts2_mcp.output.contracts.rooms import ROOM_EVENT, ROOM_EVENT_OPTION

EVENT_OPTION_SCHEMA = {'type': 'object', 'properties': {'option_id': {
    'type': 'integer', 'minimum': 0, 'maximum': 2147483647,
    'description': 'An enabled event.options[].id from get_observation or inspect_event; lethal_warning marks a visible death warning.',
}},
                       'required': ['option_id'], 'additionalProperties': False}


def event_arguments(operation, arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'option_id'}
            or type(arguments['option_id']) is not int or not 0 <= arguments['option_id'] <= 2147483647):
        raise ValueError('A nonnegative option_id is required.')
    return dict(arguments)


def event_details(value, *, full=False):
    shape = {**ROOM_EVENT, 'options': ([{**ROOM_EVENT_OPTION, 'hover_tips': [TIP]}],)} if full else ROOM_EVENT
    result = project(value, shape)
    if set(result) != set(ROOM_EVENT) or result['status'] not in PAGE_STATUSES:
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
    from sts2_mcp.output.scene_context import scene_context
    context = scene_context(state)
    if context['scene'] != 'event': raise ValueError('Invalid event inspection scene.')
    board = None
    if state.get('divination') is not None:
        from sts2_mcp.output.divination_details import divination_details
        board = divination_details(state['divination'], require_text=state.get('schema_version', 0) >= 45)
    if board is not None and board['status'] in READABLE_STATUSES:
        if (context['screen'] != {'status': 'visible', 'view': 'divination'}
                or state.get('event') is not None and state['event'].get('status') != 'covered'):
            raise ValueError('Divination is not the exposed screen.')
        if state.get('event') is not None:
            event_details(state['event'])
        return {'scene': 'event', 'divination': board}
    if context['screen'] != {'status': 'visible'}:
        raise ValueError('Event is not the exposed screen.')
    return {'scene': 'event', 'event': event_details(state['event'], full=True)}
