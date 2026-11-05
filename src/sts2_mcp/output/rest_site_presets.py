"""Share static rest-site output and filter details by native option identities."""
from sts2_mcp.output.filtering import optional_filter
from sts2_mcp.output.rest_site_details import rest_site_summary


REST_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary keeps the prompt, option IDs/names/availability and Proceed, omitting descriptions.'},
    'option_ids': {'type': ['array', 'null'], 'items': {'type': 'string', 'minLength': 1, 'maxLength': 128},
        'description': 'Current rest option IDs, such as HEAL or SMITH. Omit/null for all; [] for none. Native order is kept; missing IDs are grouped in errors.'}},
    'additionalProperties': False}


def rest_inspection_arguments(arguments):
    arguments = {} if arguments is None else arguments
    message = 'option_ids must be null or an array of non-blank IDs up to 128 characters.'
    try: selected = optional_filter(arguments.get('option_ids'), 'option_ids')
    except ValueError as error: raise ValueError(message) from error
    if selected is not None and any(not value.strip() or len(value) > 128 for value in selected):
        raise ValueError(message)
    return {'preset': arguments.get('preset', 'full'), 'option_ids': selected}


def rest_site_preset(payload, preset, option_ids):
    if 'error' in payload or preset == 'full' and option_ids is None: return payload
    rest = rest_site_summary(payload['rest_site']) if preset == 'summary' else dict(payload['rest_site'])
    result = {**payload, 'rest_site': rest}
    if option_ids is not None:
        known = {option['id'] for option in rest['options']}
        selected = set(option_ids)
        rest['options'] = [option for option in rest['options'] if option['id'] in selected]
        missing = [identifier for identifier in option_ids if identifier not in known]
        if missing: result['errors'] = [{'code': 'option_ids_not_found', 'option_ids': missing}]
    notes = dict(result.get('notes', {}))
    unavailable = notes.pop('hover_tips_unavailable', None)
    if unavailable and preset != 'summary':
        selected_sources = {'rest_site.options.' + option['id'] for option in rest['options']}
        sources = [source for source in unavailable['sources'] if source in selected_sources]
        if sources: notes['hover_tips_unavailable'] = {**unavailable, 'sources': sources}
    if notes: result['notes'] = notes
    else: result.pop('notes', None)
    return result
