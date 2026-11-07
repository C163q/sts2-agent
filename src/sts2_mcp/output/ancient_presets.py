"""Compact displayed ancient gifts and filter by their stable option IDs."""
from copy import deepcopy

from sts2_mcp.output.filtering import optional_filter


ANCIENT_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary keeps dialogue and gift effects, omitting hover help and false death warnings.'},
    'option_ids': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647},
        'description': 'Current ancient option IDs. Omit/null for all; [] for none. Page order is kept; missing IDs are grouped in errors.'}},
    'additionalProperties': False}


def ancient_inspection_arguments(arguments):
    arguments = {} if arguments is None else arguments
    return {'preset': arguments.get('preset', 'full'),
            'option_ids': optional_filter(arguments.get('option_ids'), 'option_ids', integers=True)}


def ancient_summary(value):
    result = deepcopy(value)
    for option in result.get('options') or []:
        option.pop('hover_tips', None)
        if option.get('lethal_warning') is False:
            option.pop('lethal_warning')
    return result


def ancient_preset(payload, preset, option_ids):
    if 'error' in payload or preset == 'full' and option_ids is None:
        return payload
    result = deepcopy(payload)
    ancient = result['ancient']
    if preset == 'summary':
        ancient = result['ancient'] = ancient_summary(ancient)
    if option_ids is not None:
        known = {option['id'] for option in ancient['options']}
        selected = set(option_ids)
        ancient['options'] = [option for option in ancient['options'] if option['id'] in selected]
        missing = [identifier for identifier in option_ids if identifier not in known]
        if missing:
            result['errors'] = [{'code': 'option_ids_not_found', 'option_ids': missing}]
    notes = result.get('notes', {})
    unavailable = notes.pop('hover_tips_unavailable', None)
    if unavailable and preset != 'summary':
        selected_sources = {'ancient.options.' + str(option['id']) for option in ancient['options']}
        sources = [source for source in unavailable['sources'] if source in selected_sources]
        if sources:
            notes['hover_tips_unavailable'] = {**unavailable, 'sources': sources}
    if not notes:
        result.pop('notes', None)
    return result
