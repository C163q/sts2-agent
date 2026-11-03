from sts2_mcp.output.filtering import optional_filter, linked_help, filter_indices
"""Discover UI help sources and select their native descriptions."""
UI_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary omits description from each hover tip; keep title and sources to select help to read.'},
    'sources': {'type': ['array', 'null'], 'items': {'type': 'string', 'minLength': 1},
        'description': 'Exact hover_tips.sources paths. Omit/null for all; [] returns none. Duplicates are ignored, native order remains. Shared tips keep matching sources; unavailable paths are grouped in errors.'}},
    'additionalProperties': False}


def ui_arguments(arguments):
    if arguments is None: arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'sources'}:
        raise ValueError('inspect_ui accepts only preset and sources.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid UI preset.')
    sources = arguments.get('sources')
    sources = optional_filter(sources, 'sources', integers=False)
    return {'preset': preset, 'sources': None if sources is None else list(dict.fromkeys(sources))}


def ui_preset(payload, preset, sources):
    if 'error' in payload or preset == 'full' and sources is None: return payload
    requested = None if sources is None else set(sources)
    known = {source for tip in payload['hover_tips'] for source in tip['sources']}
    tips = linked_help(payload['hover_tips'], 'sources', lambda source: requested is None or source in requested)
    if preset == 'summary':
        tips = [{key: value for key, value in tip.items() if key != 'description'} for tip in tips]
    result = {**payload, 'hover_tips': tips}
    missing = list(dict.fromkeys(source for source in sources or [] if source not in known))
    if missing: result['errors'] = [{'code': 'ui_sources_unavailable', 'sources': missing}]
    return result
