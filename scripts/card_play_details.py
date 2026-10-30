from game_output import EVENT_ENTITY, TEXT, project
from potion_action_details import POTION_SCHEMA, potion_arguments, potion_target_details


CARD_ID = {"type": "integer", "minimum": 0, "maximum": 2147483647}
CARD_TARGET_SCHEMA = {"type": "object", "properties": {"card_id": CARD_ID},
                 "required": ["card_id"], "additionalProperties": False}
TARGET_SCHEMA = {"type": "object", "properties": {"card_id": CARD_ID, "potion_slot": POTION_SCHEMA["properties"]["potion_slot"]},
                 "additionalProperties": False, "oneOf": [CARD_TARGET_SCHEMA, POTION_SCHEMA]}
PLAY_SCHEMA = {**CARD_TARGET_SCHEMA, "properties": {
    "card_id": CARD_ID, "target_id": {"type": "integer", "minimum": 0, "maximum": 4294967295}}}
TARGET_DETAILS = {"card": {"id": int, "name": TEXT}, "playable": bool, "target_type": str,
                  "requires_target": bool, "targets": [EVENT_ENTITY], "reason": TEXT}
TARGET_TYPES = {"none", "self", "any_enemy", "all_enemies", "random_enemy", "any_player",
                "any_ally", "all_allies", "osty"}


def card_play_arguments(operation, arguments):
    if operation == "inspect_targets" and isinstance(arguments, dict) and "potion_slot" in arguments:
        return potion_arguments(operation, arguments)
    allowed = {"card_id", "target_id"} if operation == "play_card" else {"card_id"}
    if (not isinstance(arguments, dict) or "card_id" not in arguments or not set(arguments) <= allowed
            or type(arguments["card_id"]) is not int or not 0 <= arguments["card_id"] <= 2147483647
            or ("target_id" in arguments and (type(arguments["target_id"]) is not int
                                              or not 0 <= arguments["target_id"] <= 4294967295))):
        raise ValueError("Invalid card play arguments.")
    return dict(arguments)


def target_details(state, arguments):
    if "potion_slot" in arguments:
        return potion_target_details(state, arguments)
    result = project(state, TARGET_DETAILS)
    if (set(result) != set(TARGET_DETAILS) or set(result["card"]) != {"id", "name"}
            or result["card"]["id"] != arguments["card_id"] or result["target_type"] not in TARGET_TYPES
            or result["requires_target"] != (result["target_type"] in {"any_enemy", "any_ally"})
            or (result["playable"] and (result["reason"] is not None
                                       or result["requires_target"] and not result["targets"]))
            or (not result["playable"] and not result["reason"])):
        raise ValueError("Invalid card targeting details.")
    seen = set()
    for target in result["targets"]:
        if (set(target) != set(EVENT_ENTITY) or not 0 <= target["id"] <= 4294967295
                or target["kind"] not in {"player", "enemy", "ally"} or target["id"] in seen):
            raise ValueError("Invalid card target.")
        seen.add(target["id"])
    return result
