"""Validate shared static combatant fields without observation assembly."""
from sts2_mcp.output.value_shapes import project, nullable
from sts2_mcp.output.contracts.combat import BLADE, ORB, ORB_SLOTS, HEALTH


def health_fields(value, *, required=False):
    present = set(value) & set(HEALTH)
    if not present and not required:
        return {}
    if present != set(HEALTH):
        raise ValueError('Incomplete combatant health.')
    result = project(value, HEALTH)
    status = result['hp_display']
    if (status not in {'numeric', 'dead', 'hidden', 'infinite', 'unknown'}
            or any(result[key] is not None and result[key] < 0 for key in ('hp', 'max_hp', 'block'))
            or status == 'numeric' and (result['hp'] is None or result['max_hp'] is None)
            or status != 'numeric' and (result['hp'] is not None or result['max_hp'] is not None)):
        raise ValueError('Invalid combatant health.')
    return result


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


def orb_slots(value):
    result = project(value, ORB_SLOTS)
    if result is not None and (len(result) > 10 or any(
            slot is not None and (set(slot) != set(ORB) or not slot['name']) for slot in result)):
        raise ValueError('Invalid public orb slots.')
    return result
