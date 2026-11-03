"""Discover UI help sources and select their native descriptions."""
UI_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary omits description from each hover tip; keep title and sources to select help to read.'},
    'sources': {'type': 'array', 'items': {'type': 'string', 'minLength': 1},
        'description': 'Exact hover_tips.sources paths. Omit for all; [] returns none. Duplicates are ignored, native order remains. Shared tips keep matching sources; unavailable paths are grouped in errors.'}},
    'additionalProperties': False}


def ui_arguments(arguments):
    if arguments is None: arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'sources'}:
        raise ValueError('Invalid UI inspection arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid UI preset.')
    sources = arguments.get('sources')
    if 'sources' in arguments and (not isinstance(sources, list) or any(
            not isinstance(source, str) or not source for source in sources)):
        raise ValueError('Invalid UI source paths.')
    return {'preset': preset, 'sources': None if sources is None else list(dict.fromkeys(sources))}


def ui_preset(payload, preset, sources):
    if 'error' in payload or preset == 'full' and sources is None: return payload
    requested = None if sources is None else set(sources)
    known = {source for tip in payload['hover_tips'] for source in tip['sources']}
    tips = []
    for tip in payload['hover_tips']:
        matches = [source for source in tip['sources'] if requested is None or source in requested]
        if not matches: continue
        tips.append({key: matches if key == 'sources' else value for key, value in tip.items()
                     if preset != 'summary' or key != 'description'})
    result = {**payload, 'hover_tips': tips}
    missing = list(dict.fromkeys(source for source in sources or [] if source not in known))
    if missing: result['errors'] = [{'code': 'ui_sources_unavailable', 'sources': missing}]
    return result
