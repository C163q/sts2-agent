OBSERVATION_SCHEMA = {
    'type': 'object',
    'properties': {'preset': {
        'type': 'string', 'enum': ['full', 'actions_only'], 'default': 'full',
        'description': 'full includes visible gameplay state and any exposed divination image; actions_only returns scene, screen, selection type/status and tool names. Both refresh action permission.',
    }},
    'additionalProperties': False,
}


def preset_arguments(arguments):
    if arguments is None:
        return 'full'
    if not isinstance(arguments, dict) or set(arguments) - {'preset'}:
        raise ValueError('Invalid observation arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'actions_only'):
        raise ValueError('Invalid observation preset.')
    return preset


def observation_preset(payload, preset):
    if preset == 'full' or 'error' in payload:
        return payload
    result = {key: payload[key] for key in ('scene', 'screen', 'available_actions')}
    if payload.get('selection') is not None:
        result['selection'] = {key: payload['selection'][key] for key in ('type', 'status')}
    return result
