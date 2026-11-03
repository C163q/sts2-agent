from sts2_mcp.output.filtering import optional_filter, linked_help, filter_indices
"""Project validated relic details while keeping original and result indices distinct."""

RELIC_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full keeps descriptions and shared hover help; summary keeps only name, displayed counter and visible melted state, as in basic observations.'},
        'relic_indices': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647},
                          'description': 'Zero-based positions in the current unfiltered inspect_relics list, not persistent IDs or top_bar positions. Omit/null for all; [] returns none. Duplicates are ignored; native order remains. Returned relic_indices maps results to original positions; unavailable positions are grouped in errors.'},
    },
    'additionalProperties': False,
}


def relic_arguments(arguments):
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'relic_indices'}:
        raise ValueError('Invalid relic inspection arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid relic inspection preset.')
    indices = arguments.get('relic_indices')
    indices = optional_filter(indices, 'relic_indices', integers=True)
    return {'preset': preset, 'relic_indices': None if indices is None else list(dict.fromkeys(indices))}


def relic_preset(payload, preset, relic_indices):
    if 'error' in payload or preset == 'full' and relic_indices is None:
        return payload
    retained, missing = filter_indices(payload['relics'], relic_indices)
    result = {**payload, 'relics': [payload['relics'][index] for index in retained]}
    if relic_indices is not None:
        result['relic_indices'] = retained
    if preset == 'summary':
        result['relics'] = [{key: value for key, value in relic.items() if key in {'name', 'counter', 'melted'}}
                            for relic in result['relics']]
        result.pop('hover_tips', None)
    elif relic_indices is not None:
        result['hover_tips'] = linked_help(payload['hover_tips'], 'relic_indices', set(retained).__contains__)
    if missing:
        result['errors'] = [{'code': 'relic_indices_out_of_range', 'relic_indices': missing}]
    return result
