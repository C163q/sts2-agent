"""Project complete treasure inspections through the shared static room format."""
from sts2_mcp.output.treasure_details import treasure_details


TREASURE_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary keeps chest state, displayed relic name/availability and the page button, omitting hover text.'}},
    'additionalProperties': False}


def treasure_preset(payload, preset):
    if 'error' in payload or preset == 'full': return payload
    result = {**payload, 'treasure': treasure_details(payload['treasure'])}
    notes = dict(result.get('notes', {}))
    notes.pop('hover_tips_unavailable', None)
    if notes: result['notes'] = notes
    else: result.pop('notes', None)
    return result
