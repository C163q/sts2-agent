"""Select potion slots without renumbering action targets or linked help."""
from sts2_mcp.output.filtering import optional_filter, linked_help, filter_indices


POTION_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
               'description': 'summary keeps basic potion slot names and displayed flags, without hover help.'},
    'slot_indices': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647},
                     'description': 'Zero-based belt positions, matching potion_slot. Omit/null for all; [] selects none. Empty slots are valid. Duplicates are ignored; native order remains. Returned slot_indices maps results to original slots; out-of-range positions are grouped in errors.'}},
    'additionalProperties': False}
STATIC_FIELDS = {'name', 'bouncing', 'usable_here'}


def potion_arguments(arguments):
    arguments = {} if arguments is None else arguments
    preset = arguments.get('preset', 'full')
    indices = optional_filter(arguments.get('slot_indices'), 'slot_indices', integers=True)
    result = {'preset': preset, 'slot_indices': indices}
    if preset == 'summary': result['level'] = 'summary'
    return result


def potion_preset(payload, preset, slot_indices):
    if 'error' in payload or preset == 'full' and slot_indices is None:
        return payload
    retained, missing = filter_indices(payload['potion_slots'], slot_indices)
    result = {**payload, 'potion_slots': [payload['potion_slots'][index] for index in retained]}
    if slot_indices is not None: result['slot_indices'] = retained
    if preset == 'summary':
        result['potion_slots'] = [None if slot is None else {key: value for key, value in slot.items() if key in STATIC_FIELDS}
                                  for slot in result['potion_slots']]
        result.pop('slot_tip', None)
        result.pop('hover_tips', None)
    elif slot_indices is not None:
        result['hover_tips'] = linked_help(payload['hover_tips'], 'slot_indices', set(retained).__contains__)
    notes = dict(result.get('notes', {}))
    unavailable = notes.pop('hover_tips_unavailable', None)
    if preset == 'full' and unavailable:
        selected = {f'potion_slots.{index}' for index in retained}
        sources = [source for source in unavailable['sources'] if source in selected]
        if sources: notes['hover_tips_unavailable'] = {**unavailable, 'sources': sources}
    if notes: result['notes'] = notes
    else: result.pop('notes', None)
    if missing:
        result['errors'] = [{'code': 'potion_slot_indices_out_of_range', 'slot_indices': missing}]
    return result
