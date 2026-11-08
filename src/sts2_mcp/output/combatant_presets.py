from sts2_mcp.output.filtering import optional_filter, linked_help, filter_indices
"""Select static combatant subtrees while preserving canonical source addresses."""
from copy import deepcopy
from sts2_mcp.output.combat_fields import health_summary

HEALTH_FIELDS = ('hp', 'max_hp', 'hp_display', 'health', 'block')


COMBATANT_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
               'description': 'summary keeps static combatant data and omits all hover help.'},
    'sources': {'type': ['array', 'null'], 'items': {'type': 'string', 'minLength': 1},
                'description': 'Paths in the current unfiltered inspection, e.g. player, enemies, enemies.0, enemies.0.intents.0. Group prefixes include descendants. Omit/null for all; [] selects no objects. source_indices maps compact arrays to original positions.'}},
    'additionalProperties': False}
ROOTS = ('player', 'enemies', 'allies')


def combatant_arguments(arguments):
    if arguments is None: arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'sources'}:
        raise ValueError('inspect_combatants accepts only preset and sources.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('preset must be one of: default, full, summary.')
    sources = arguments.get('sources')
    sources = optional_filter(sources, 'sources', integers=False)
    return {'preset': preset, 'sources': None if sources is None else list(dict.fromkeys(sources))}


def _source_paths(payload):
    paths = set()

    def entries(path, value):
        paths.add(path)
        if isinstance(value, list):
            paths.update(f'{path}.{i}' for i in range(len(value)))

    def owner(path, value, fields):
        paths.add(path)
        if isinstance(value, dict):
            for field in fields:
                if field in value: entries(f'{path}.{field}', value[field])

    if 'player' in payload: owner('player', payload['player'], (*HEALTH_FIELDS, 'powers', 'orb_slots', 'sovereign_blades'))
    for root in ('enemies', 'allies'):
        if root not in payload: continue
        paths.add(root)
        for index, item in enumerate(payload[root] or []):
            owner(f'{root}.{index}', item, (*HEALTH_FIELDS, 'powers', 'intents') if root == 'enemies'
                  else (*HEALTH_FIELDS, 'powers', 'block_shared_with'))
    return paths


def combatant_preset(payload, preset, sources):
    if 'error' in payload or preset == 'full' and sources is None: return payload
    if preset == 'summary':
        payload = deepcopy(payload)
        for unit in [payload.get('player'), *(payload.get('enemies') or []), *(payload.get('allies') or [])]:
            if unit is not None and 'hp_display' in unit: health_summary(unit, unit.copy())
    requested = None if sources is None else list(dict.fromkeys(sources))
    known = _source_paths(payload)
    valid = None if requested is None else [source for source in requested if source in known]
    mappings = {}
    omitted = object()

    def selected(path):
        return valid is None or any(path == source or path.startswith(source + '.') for source in valid)

    def project(path, value):
        if selected(path): return deepcopy(value)
        if not any(source.startswith(path + '.') for source in valid): return omitted
        if isinstance(value, list):
            items, indices = [], []
            for index, item in enumerate(value):
                child = project(f'{path}.{index}', item)
                if child is not omitted:
                    items.append(child); indices.append(index)
            if indices != list(range(len(value))): mappings[path] = indices
            return items
        result = {key: deepcopy(value[key]) for key in ('id', 'name') if key in value}
        for key, item in value.items():
            if key in {'id', 'name'}: continue
            child = project(f'{path}.{key}', item)
            if child is not omitted: result[key] = child
        return result

    result = {key: deepcopy(payload[key]) for key in ('scene', 'screen')}
    for root in ROOTS:
        if root in payload:
            item = project(root, payload[root])
            if item is not omitted: result[root] = item
    if mappings: result['source_indices'] = mappings
    if preset == 'full' and any(root in result for root in ROOTS):
        result['hover_tips'] = linked_help(payload['hover_tips'], 'sources', selected)
    notes = deepcopy(payload.get('notes', {}))
    if not any(enemy.get('intents') for enemy in result.get('enemies') or []):
        notes.pop('enemy_attack_intents', None)
    unavailable = notes.pop('hover_tips_unavailable', None)
    if preset == 'full' and unavailable:
        matches = [source for source in unavailable['sources'] if selected(source)]
        if matches: notes['hover_tips_unavailable'] = {**unavailable, 'sources': matches}
    if notes: result['notes'] = notes
    missing = [] if requested is None else [source for source in requested if source not in known]
    if missing: result['errors'] = [{'code': 'combatant_sources_unavailable', 'sources': missing}]
    return result
