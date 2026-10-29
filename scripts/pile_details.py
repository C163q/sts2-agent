from deck_details import browsed_cards


PILES = ("draw", "discard", "exhaust")
PILE_SCHEMA = {
    "type": "object",
    "properties": {
        "pile": {"type": "string", "enum": list(PILES), "description": "The combat pile to inspect."},
        "detail_level": {"type": "string", "enum": ["summary", "full"], "default": "summary",
                         "description": "Summary omits descriptions and hover tips; full includes both."},
    },
    "required": ["pile"],
    "additionalProperties": False,
}


def pile_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) - set(PILE_SCHEMA["properties"])
            or arguments.get("pile") not in PILES
            or arguments.get("detail_level", "summary") not in ("summary", "full")):
        raise ValueError("Invalid pile arguments.")
    return dict(arguments)


def pile_details(state, pile, level):
    status = state["status"]
    screen = state["screen"]
    if (state["scene"] != "card_pile" or state["pile"] != pile or state["detail_level"] != level
            or status not in ("opened", "empty", "unavailable") or not isinstance(screen, dict)
            or not isinstance(screen["status"], str) or not isinstance(state["message"], str)):
        raise ValueError("Invalid pile details.")
    view = {"status": screen["status"]}
    if "view" in screen:
        if not isinstance(screen["view"], str):
            raise ValueError("Invalid pile screen view.")
        view["view"] = screen["view"]
    result = {"scene": "card_pile", "pile": pile, "detail_level": level, "status": status,
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
        result["cards"] = browsed_cards(state["cards"], level, "pile")
    return result
