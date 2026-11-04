from sts2_mcp.output.value_shapes import project, TEXT
from sts2_mcp.output.contracts.transition import POTION_REF, TARGET_ENTITY


POTION_SLOT = {"type": "integer", "minimum": 0, "maximum": 2147483647,
               "description": "Original zero-based belt slot, counting empty slots. For filtered inspect_potions results, use slot_indices, not the returned array position."}
POTION_SCHEMA = {"type": "object", "properties": {"potion_slot": POTION_SLOT},
                 "required": ["potion_slot"], "additionalProperties": False}
USE_SCHEMA = {**POTION_SCHEMA, "properties": {
    "potion_slot": POTION_SLOT, "target_id": {
        "description": "Current creature ID, or merchant for a merchant. Required for a targeted potion, even for one target; otherwise omit.",
        "oneOf": [
        {"type": "integer", "minimum": 0, "maximum": 4294967295}, {"type": "string", "enum": ["merchant"]}]}}}
POTION_TARGET_DETAILS = {"potion": POTION_REF, "usable": bool, "discardable": bool,
                         "target_type": str, "requires_target": bool, "targets": [TARGET_ENTITY], "reason": TEXT}
POTION_TARGET_TYPES = {"self", "any_enemy", "all_enemies", "any_player", "targeted_no_creature"}


def potion_arguments(operation, arguments):
    allowed = {"potion_slot", "target_id"} if operation == "use_potion" else {"potion_slot"}
    if (not isinstance(arguments, dict) or "potion_slot" not in arguments or not set(arguments) <= allowed
            or type(arguments["potion_slot"]) is not int or not 0 <= arguments["potion_slot"] <= 2147483647):
        raise ValueError('potion_slot must be an integer slot index from 0 to 2147483647; '
                         'only use_potion accepts an optional target_id.')
    if "target_id" in arguments:
        target = arguments["target_id"]
        if not (type(target) is int and 0 <= target <= 4294967295 or type(target) is str and target == "merchant"):
            raise ValueError("target_id must be an integer from 0 to 4294967295 or merchant; omit it when no target is required.")
    return dict(arguments)


def potion_target_details(state, arguments):
    result = project(state, POTION_TARGET_DETAILS)
    if (set(result) != set(POTION_TARGET_DETAILS) or set(result["potion"]) != set(POTION_REF)
            or result["potion"]["slot_index"] != arguments["potion_slot"]
            or result["target_type"] not in POTION_TARGET_TYPES
            or (result["target_type"] != "any_player" and result["requires_target"] !=
                (result["target_type"] in {"any_enemy", "any_ally", "targeted_no_creature"}))
            or (result["usable"] and (not result["discardable"] or result["reason"] is not None
                                     or result["requires_target"] and not result["targets"]))
            or (not result["usable"] and not result["reason"])):
        raise ValueError("Invalid potion targeting details.")
    seen = set()
    for target in result["targets"]:
        identity = target.get("id")
        if (set(target) != set(TARGET_ENTITY) or target["kind"] not in {"player", "enemy", "ally", "merchant"}
                or (type(identity) is int and (not 0 <= identity <= 4294967295 or target["kind"] == "merchant"))
                or (type(identity) is str and (identity not in {"self", "merchant"}
                    or target["kind"] != ("player" if identity == "self" else "merchant")))
                or (identity == "self" and result["requires_target"])
                or ((identity == "merchant") != (result["target_type"] == "targeted_no_creature"))
                or identity in seen):
            raise ValueError("Invalid potion target.")
        seen.add(identity)
    return result
