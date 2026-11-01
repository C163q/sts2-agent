"""Project validated relic details while keeping original and result indices distinct."""

RELIC_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full keeps descriptions and shared hover help; summary keeps only name, displayed counter and visible melted state, as in basic observations.'},
        'relic_indices': {'type': 'array', 'items': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647},
                          'description': 'Zero-based positions in the current unfiltered inspect_relics list, not persistent IDs or top_bar positions. Omit for all; [] returns none. Duplicates are ignored; native order remains. Returned relic_indices maps results to original positions; unavailable positions are grouped in errors.'},
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
    if 'relic_indices' in arguments and (not isinstance(indices, list) or any(
            type(index) is not int or not 0 <= index <= 2147483647 for index in indices)):
        raise ValueError('Invalid relic indices.')
    return {'preset': preset, 'relic_indices': None if indices is None else list(dict.fromkeys(indices))}


def relic_preset(payload, preset, relic_indices):
    if 'error' in payload or preset == 'full' and relic_indices is None:
        return payload
    requested = None if relic_indices is None else set(relic_indices)
    retained = [index for index in range(len(payload['relics'])) if requested is None or index in requested]
    result = {**payload, 'relics': [payload['relics'][index] for index in retained]}
    if relic_indices is not None:
        result['relic_indices'] = retained
    if preset == 'summary':
        result['relics'] = [{key: value for key, value in relic.items() if key in {'name', 'counter', 'melted'}}
                            for relic in result['relics']]
        result.pop('hover_tips', None)
    elif relic_indices is not None:
        positions = {original: current for current, original in enumerate(retained)}
        result['hover_tips'] = [{**tip, 'relic_indices': [positions[i] for i in tip['relic_indices'] if i in positions]}
                                for tip in payload['hover_tips'] if any(i in positions for i in tip['relic_indices'])]
    missing = [index for index in relic_indices or [] if index >= len(payload['relics'])]
    if missing:
        result['errors'] = [{'code': 'relic_indices_out_of_range', 'relic_indices': missing}]
    return result
