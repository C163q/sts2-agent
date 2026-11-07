"""Page display progress is independent of covering screens and action readiness."""
READABLE_STATUSES = frozenset({'visible', 'not_ready'})
PAGE_STATUSES = READABLE_STATUSES | {'covered'}
PAGE_CONTEXTS = {
    'event': ('event', None), 'ancient': ('ancient', None), 'shop': ('shop', None),
    'treasure': ('treasure', None), 'rest_site': ('rest_site', None), 'rewards': ('rewards', None),
    'divination': ('event', 'divination'), 'epilogue': ('epilogue', 'epilogue'),
    'run_result': ('run_result', 'run_result'),
}


def validate_presentations(value):
    for key, (scene, view) in PAGE_CONTEXTS.items():
        page = value.get(key)
        if page is None or page['status'] not in READABLE_STATUSES:
            continue
        screen = {'status': 'visible', **({'view': view} if view else {})}
        if value['scene'] != scene or value['screen'] != screen:
            raise ValueError('Page display and screen context disagree.')
    return value
