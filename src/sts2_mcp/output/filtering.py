"""Selection primitives preserve native order and canonical references."""


def optional_filter(value, field, *, integers=False):
    if value is None:
        return None
    valid_item = (lambda item: type(item) is int and 0 <= item <= 2147483647) if integers else (
        lambda item: isinstance(item, str) and bool(item))
    if not isinstance(value, list) or any(not valid_item(item) for item in value):
        kind = 'integer IDs from 0 to 2147483647' if integers else 'non-empty source paths'
        raise ValueError(f'{field} must be null or an array of {kind}.')
    return list(dict.fromkeys(value))


def filter_indices(items, requested):
    if requested is None:
        return list(range(len(items))), []
    requested = list(dict.fromkeys(requested))
    selected = set(requested)
    return ([index for index in range(len(items)) if index in selected],
            [index for index in requested if index >= len(items)])


def linked_help(tips, field, selected):
    result = []
    for tip in tips:
        matches = [source for source in tip[field] if selected(source)]
        if matches:
            result.append({**tip, field: matches})
    return result
