"""Public null rules, independent of tool dispatch and result assembly."""
from sts2_mcp.output.media import ImagePayload


PREVIEW_PATHS = (
    ('selection', 'upgrade_preview'),
    ('selection', 'upgrade_previews', '*'),
    ('selection', 'enchant_previews', '*'),
    ('selection', 'transform_previews', '*'),
)


def preserve_null(path, parent):
    """Keep facts and comparisons intact; array elements are never removed."""
    if path == ('treasure', 'relic') and parent.get('status') == 'visible':
        return True
    if path[:3] == ('transition', 'events', '*'):
        return True
    return any(path[:len(prefix)] == prefix and len(path) > len(prefix)
               and path[len(prefix)] in {'before', 'after'} for prefix in PREVIEW_PATHS)


def omit_false(path):
    return path[:-1] in {('relics', '*'), ('top_bar', 'relics', '*')} \
        and path[-1] in {'grayed_out', 'pulsing'}


def apply_preset(payload, preset, *, path=()):
    if preset != 'default' or 'error' in payload:
        return payload

    def compact(value, path=()):
        if isinstance(value, dict):
            return {key: compact(item, (*path, key)) for key, item in value.items()
                    if (item is not None or preserve_null((*path, key), value))
                    and not (item is False and omit_false((*path, key)))}
        if isinstance(value, list):
            return [compact(item, (*path, '*')) for item in value]
        return value

    result = compact(payload, path)
    return ImagePayload(result, payload.image) if isinstance(payload, ImagePayload) else result
