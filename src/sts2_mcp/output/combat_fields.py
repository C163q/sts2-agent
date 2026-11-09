"""Validate shared static combatant fields without observation assembly."""
from sts2_mcp.output.value_shapes import project, nullable
from sts2_mcp.output.contracts.combat import BLADE, ORB, ORB_SLOTS, HEALTH, HEALTH_PREVIEW, HP_PREVIEW


def preview_fields(value, *, required=False):
    if 'hp_preview' not in value:
        if required:
            raise ValueError('Missing combatant health preview.')
        return {}
    result = project(value, HEALTH_PREVIEW)
    preview = result['hp_preview']
    if preview is not None and (set(preview) != set(HP_PREVIEW)
            or preview['lethal'] not in (None, 'poison', 'doom')
            or any(preview[key] is not None and preview[key] < 0 for key in ('poison_damage', 'doom_threshold'))
            or value.get('hp_display') != 'numeric'):
        raise ValueError('Invalid combatant health preview.')
    return result


def health_fields(value, *, required=False, preview_required=False):
    preview = preview_fields(value, required=preview_required)
    present = set(value) & set(HEALTH)
    if not present and not required:
        return preview
    if present != set(HEALTH):
        raise ValueError('Incomplete combatant health.')
    result = project(value, HEALTH)
    status = result['hp_display']
    if (status not in {'numeric', 'dead', 'hidden', 'infinite', 'unknown'}
            or any(result[key] is not None and result[key] < 0 for key in ('hp', 'max_hp', 'block'))
            or status == 'numeric' and (result['hp'] is None or result['max_hp'] is None)
            or status != 'numeric' and (result['hp'] is not None or result['max_hp'] is not None)):
        raise ValueError('Invalid combatant health.')
    return {**result, **preview}


def health_summary(compact, original):
    status = original.get('hp_display')
    hp, maximum = original.get('hp'), original.get('max_hp')
    health = {'infinite': '∞', 'dead': 'dead', 'unknown': 'unknown'}.get(status)
    if status == 'numeric' and type(hp) is int and type(maximum) is int:
        health = f'{hp}/{maximum}'
    for key in ('hp', 'max_hp', 'hp_display'):
        compact.pop(key, None)
    compact['health'] = health


def validate_identities(items, maximum):
    seen = set()
    for item in items:
        identity = item.get('id')
        if type(identity) is not int or not 0 <= identity <= maximum or identity in seen:
            raise ValueError('Invalid or duplicate public identity.')
        seen.add(identity)


def blade_refs(value):
    result = project(value, nullable([BLADE]))
    if result is not None:
        validate_identities(result, 2147483647)
        if any(set(item) != set(BLADE) for item in result):
            raise ValueError('Incomplete public blade identity.')
    return result


def orb_slots(value, *, indexed=False):
    result = project(value, ORB_SLOTS)
    if result is not None:
        required = set(ORB) if indexed else set(ORB) - {'slot_index'}
        if len(result) > 10 or any(slot is not None and (
                not required <= set(slot) or not slot['name']
                or 'slot_index' in slot and slot['slot_index'] != len(result) - 1 - i)
                for i, slot in enumerate(result)):
            raise ValueError('Invalid public orb slots.')
    return result
