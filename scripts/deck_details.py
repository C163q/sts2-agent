import re


SORT_KEYS = ("obtained", "type", "cost", "name")
DECK_SCHEMA = {
    "type": "object",
    "properties": {
        "detail_level": {"type": "string", "enum": ["summary", "full"], "default": "summary",
                         "description": "Summary omits descriptions and hover tips; full includes both."},
        "view_upgrades": {"type": "boolean", "description": "Preview upgrades. Omit to keep the current page setting."},
        "sort_by": {"type": "string", "enum": list(SORT_KEYS),
                    "description": "Change the native page's primary sort. Omit to keep it."},
        "descending": {"type": "boolean", "description": "Requires sort_by; an explicit sort defaults to ascending."},
    },
    "dependentRequired": {"descending": ["sort_by"]},
    "additionalProperties": False,
}


def deck_arguments(arguments):
    if arguments is None:
        return {}
    if not isinstance(arguments, dict) or set(arguments) - set(DECK_SCHEMA["properties"]):
        raise ValueError("Invalid deck arguments.")
    if "detail_level" in arguments and arguments["detail_level"] not in ("summary", "full"):
        raise ValueError("Invalid detail level.")
    if "sort_by" in arguments and arguments["sort_by"] not in SORT_KEYS:
        raise ValueError("Invalid sorting key.")
    for key in ("view_upgrades", "descending"):
        if key in arguments and type(arguments[key]) is not bool:
            raise ValueError("Invalid boolean option.")
    if "descending" in arguments and "sort_by" not in arguments:
        raise ValueError("Sorting direction requires a key.")
    return dict(arguments)


def deck_details(state, level):
    sort = state["sort"]
    if (state["scene"] != "deck" or state["detail_level"] != level
            or type(state["view_upgrades"]) is not bool or not isinstance(sort, dict)
            or sort["by"] not in SORT_KEYS or type(sort["descending"]) is not bool
            or not isinstance(state["deck"], list)):
        raise ValueError("Invalid deck details.")
    cards = []
    ids = set()
    for card in state["deck"]:
        if (not isinstance(card, dict) or not isinstance(card["id"], str)
                or not re.fullmatch(r"deck:(0|[1-9][0-9]*)", card["id"]) or card["id"] in ids):
            raise ValueError("Invalid deck card identity.")
        ids.add(card["id"])
        text = {key: card[key] for key in ("id", "name", "type", "rarity", "visual_card_pool", "energy_cost", "star_cost")}
        if any(not isinstance(text[key], str) for key in ("name", "type", "rarity", "visual_card_pool")):
            raise ValueError("Invalid deck card text.")
        if any(text[key] is not None and not isinstance(text[key], str) for key in ("energy_cost", "star_cost")):
            raise ValueError("Invalid deck cost.")
        if level == "full":
            if not isinstance(card["description"], str) or not isinstance(card["hover_tips"], list):
                raise ValueError("Invalid deck card description.")
            tips = []
            for tip in card["hover_tips"]:
                if (not isinstance(tip, dict) or (tip["title"] is not None and not isinstance(tip["title"], str))
                        or not isinstance(tip["description"], str)):
                    raise ValueError("Invalid deck hover tip.")
                tips.append({"title": tip["title"], "description": tip["description"]})
            text.update(description=card["description"], hover_tips=tips)
        cards.append(text)
    return {"scene": "deck", "detail_level": level, "view_upgrades": state["view_upgrades"],
            "sort": {"by": sort["by"], "descending": sort["descending"]}, "deck": cards}


def closed_card_view(state):
    result = {key: state[key] for key in ("scene", "screen", "turn", "player", "enemies", "top_bar", "buttons", "available_actions")}
    if (not isinstance(result["scene"], str) or not isinstance(result["screen"], dict)
            or not isinstance(result["screen"]["status"], str) or not isinstance(result["available_actions"], list)
            or any(not isinstance(action, str) for action in result["available_actions"])):
        raise ValueError("Invalid card view close observation.")
    result["screen"] = {"status": state["screen"]["status"]}
    if "view" in state["screen"]:
        if not isinstance(state["screen"]["view"], str):
            raise ValueError("Invalid screen view.")
        result["screen"]["view"] = state["screen"]["view"]
    return result
