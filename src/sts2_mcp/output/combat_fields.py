"""Validate shared static combatant fields without observation assembly."""
from sts2_mcp.output.value_shapes import project, nullable
from sts2_mcp.output.contracts.combat import BLADE, ORB, ORB_SLOTS


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
