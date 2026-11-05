"""Shared meaning of room scenes and exposed or covering pages."""
SCENES = frozenset(('combat', 'main_menu', 'map', 'unrecognized', 'rewards', 'rest_site',
                    'treasure', 'shop', 'ancient', 'event', 'epilogue', 'run_result'))
SCREEN_STATUSES = frozenset(('visible', 'covered', 'hidden', 'not_ready', 'not_applicable'))


def scene_context(state):
    scene, screen = state.get('scene'), state.get('screen')
    if (not isinstance(scene, str) or scene not in SCENES or not isinstance(screen, dict)
            or not isinstance(screen.get('status'), str) or screen['status'] not in SCREEN_STATUSES
            or 'view' in screen and (not isinstance(screen['view'], str) or not screen['view'])):
        raise ValueError('Invalid observation context.')
    return {'scene': scene, 'screen': {key: screen[key] for key in ('status', 'view') if key in screen}}
