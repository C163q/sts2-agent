"""Strict scalar and object projection shared by gameplay structures."""

def nullable(shape):
    return (shape,)


def project(value, shape):
    """Copy declared fields; a tuple allows null and a list describes array items."""
    if isinstance(shape, frozenset):
        if type(value) not in shape:
            raise ValueError("Invalid gameplay scalar type.")
        return value
    if isinstance(shape, tuple):
        if value is None:
            return None
        return project(value, shape[0])
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            raise ValueError("Expected a gameplay object.")
        return {key: project(item, shape[key]) for key, item in value.items() if key in shape}
    if isinstance(shape, list):
        if not isinstance(value, list):
            raise ValueError("Expected a gameplay array.")
        return [project(item, shape[0]) for item in value]
    # bool is an int subclass; accepting it would hide malformed numeric fields.
    if type(value) is not shape:
        raise ValueError("Invalid gameplay field type.")
    return value


TEXT = nullable(str)
NUMBER = nullable(int)
TIP = {"title": TEXT, "description": str}
