from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.deck_details import browsed_cards


PILES = ("draw", "discard", "exhaust")
PILE_SCHEMA = {
    "type": "object",
    "properties": {
        "pile": {"type": "string", "enum": list(PILES), "description": "The combat pile to inspect."},
        "preset": {"type": "string", "enum": ["full", "summary"], "default": "full",
                   "description": "full includes card effects and shared hover help; summary keeps the shared compact card fields."},
    },
    "required": ["pile"],
    "additionalProperties": False,
}


def pile_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) - set(PILE_SCHEMA["properties"])
            or arguments.get("pile") not in PILES
            or arguments.get("preset", "full") not in ("summary", "full")):
        raise ValueError("Invalid pile arguments.")
    return dict(arguments)


def pile_details(state, pile):
    context = scene_context(state)
    status = state["status"]
    screen = state["screen"]
    if (state["pile"] != pile
            or status not in ("opened", "empty", "unavailable") or not isinstance(screen, dict)
            or not isinstance(screen["status"], str) or not isinstance(state["message"], str)):
        raise ValueError("Invalid pile details.")
    view = {"status": screen["status"]}
    if "view" in screen:
        if not isinstance(screen["view"], str):
            raise ValueError("Invalid pile screen view.")
        view["view"] = screen["view"]
    result = {**context, "pile": pile, "status": status,
              "screen": view, "message": state["message"]}
    if status == "unavailable":
        if state["cards"] is not None or state["reason"] not in ("entry_not_visible", "entry_disabled"):
            raise ValueError("Invalid unavailable pile.")
        result.update(cards=None, reason=state["reason"])
    else:
        if status == "opened":
            if view != {"status": "covered", "view": pile + "_pile"} or not state["cards"]:
                raise ValueError("Invalid opened pile screen.")
        elif state["cards"] != [] or view != {"status": "visible"}:
            raise ValueError("Invalid empty pile.")
        result["cards"] = browsed_cards(state["cards"], "pile")
    return result
