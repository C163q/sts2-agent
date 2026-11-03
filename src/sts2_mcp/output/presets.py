"""Apply public output presets only after validation, permissions and filtering."""
from copy import deepcopy
from functools import wraps
from inspect import signature

from sts2_mcp.output.null_fields import apply_preset, preserve_null, PREVIEW_PATHS
from sts2_mcp.output.player_output import player_result
from sts2_mcp.output.error_output import invalid_request


SPECIAL_PRESETS = {
    'get_observation': ('actions_only', 'summary', 'top_bar'),
    'inspect_ui': ('summary',),
    'inspect_combatants': ('summary',),
    'inspect_hand': ('summary',),
    'inspect_deck': ('summary',),
    'inspect_pile': ('summary',),
    'inspect_selection': ('summary',),
    'inspect_relics': ('summary',),
    'inspect_map': ('selectable',),
}
PRESET_DESCRIPTION = 'default omits ordinary null fields; full preserves nulls.'


def preset_schema(schema):
    result = deepcopy(schema)
    previous = result['properties'].get('preset', {})
    result['properties']['preset'] = {
        'type': 'string', 'enum': ['default', *previous.get('enum', ['full'])],
        'default': 'default',
        'description': ' '.join(filter(None, (PRESET_DESCRIPTION, previous.get('description')))),
    }
    for key in ('oneOf', 'anyOf', 'allOf'):
        if key in result:
            result[key] = [preset_schema(branch) for branch in result[key]]
    return result






def output_preset(handler):
    operation = handler.__name__
    accepts_arguments = len(signature(handler).parameters) > 1

    @wraps(handler)
    async def wrapped(self, arguments=None):
        valid = arguments is None or isinstance(arguments, dict)
        preset = (arguments or {}).get('preset', 'default') if valid else None
        valid = valid and isinstance(preset, str) and preset in (
            'default', 'full', *SPECIAL_PRESETS.get(operation, ()))
        if not valid:
            if operation not in {'get_observation', 'inspect_targets', 'inspect_ui', 'inspect_hand', 'inspect_combatants'} and accepts_arguments:
                return await handler(self, arguments)
            if not isinstance(arguments, dict):
                return invalid_request('Tool arguments must be a JSON object.')
            allowed = ', '.join(('default', 'full', *SPECIAL_PRESETS.get(operation, ())))
            return invalid_request(f'preset must be one of: {allowed}.')
        native = dict(arguments or {})
        if operation in SPECIAL_PRESETS:
            native['preset'] = 'full' if preset == 'default' else preset
        else:
            native.pop('preset', None)
        if accepts_arguments:
            payload = await handler(self, native)
        elif native:
            return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
        else:
            payload = await handler(self)
        compact_summary = preset == 'summary' and operation in {
            'inspect_ui', 'inspect_combatants', 'inspect_hand', 'inspect_selection', 'inspect_relics', 'inspect_deck', 'inspect_pile'}
        return apply_preset(payload, 'default' if compact_summary else preset)

    wrapped.supports_output_presets = True
    return wrapped
