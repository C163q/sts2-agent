"""Shared static event output and optional inspection media."""
from copy import deepcopy


EVENT_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary omits event narrative, hover help, false death warnings and divination instructions.'},
    'include_image': {'type': 'boolean', 'default': False,
        'description': 'Attach the currently visible divination board PNG; text is always returned.'}},
    'additionalProperties': False}


def event_summary(value):
    result = deepcopy(value)
    result.pop('description', None)
    for option in result.get('options') or []:
        option.pop('hover_tips', None)
        if option.get('lethal_warning') is False:
            option.pop('lethal_warning')
    return result


def divination_summary(value):
    result = deepcopy(value)
    result.pop('instructions', None)
    return result


def inspect_event_preset(payload, preset='full', include_image=False):
    result = dict(payload)
    if result.get('event') is not None and preset == 'summary':
        result['event'] = event_summary(result['event'])
    if result.get('divination') is not None:
        board = divination_summary(result['divination']) if preset == 'summary' else deepcopy(result['divination'])
        if board.get('grid') is not None and not include_image:
            board['grid'].pop('image', None)
        result['divination'] = board
    from sts2_mcp.output.media import ImagePayload
    return ImagePayload(result, payload.image) if isinstance(payload, ImagePayload) else result
