"""Apply public output presets only after validation, permissions and filtering."""
from copy import deepcopy
from functools import wraps
from inspect import signature

from sts2_mcp.output.divination_details import ImagePayload
from sts2_mcp.output.player_output import player_result


SPECIAL_PRESETS = {
    'get_observation': ('actions_only', 'summary', 'top_bar'),
    'inspect_hand': ('summary',),
    'inspect_selection': ('summary',),
    'inspect_relics': ('summary',),
    'inspect_map': ('selectable',),
}
PREVIEW_PATHS = (
    ('selection', 'upgrade_preview'),
    ('selection', 'upgrade_previews', '*'),
    ('selection', 'enchant_previews', '*'),
    ('selection', 'transform_previews', '*'),
)
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


def preserve_null(path, parent):
    """Keep facts and comparisons intact; array elements are never removed."""
    if path == ('treasure', 'relic') and parent.get('status') == 'visible':
        return True
    if path[:3] == ('transition', 'events', '*'):
        return True
    return any(path[:len(prefix)] == prefix and len(path) > len(prefix)
               and path[len(prefix)] in {'before', 'after'} for prefix in PREVIEW_PATHS)


def apply_preset(payload, preset):
    if preset != 'default' or 'error' in payload:
        return payload

    def compact(value, path=()):
        if isinstance(value, dict):
            return {key: compact(item, (*path, key)) for key, item in value.items()
                    if item is not None or preserve_null((*path, key), value)}
        if isinstance(value, list):
            return [compact(item, (*path, '*')) for item in value]
        return value

    result = compact(payload)
    return ImagePayload(result, payload.image) if isinstance(payload, ImagePayload) else result


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
            # Let the original validator preserve this operation's permission policy.
            if accepts_arguments:
                return await handler(self, arguments)
            return player_result({'ok': False, 'error': {'code': 'invalid_request'}})
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
            'inspect_hand', 'inspect_selection', 'inspect_relics'}
        return apply_preset(payload, 'default' if compact_summary else preset)

    wrapped.supports_output_presets = True
    return wrapped
