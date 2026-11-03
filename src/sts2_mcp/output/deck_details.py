from sts2_mcp.output.scene_context import scene_context
import re


SORT_KEYS = ("obtained", "type", "cost", "name")
DECK_SCHEMA = {
    "type": "object",
    "properties": {
        "preset": {"type": "string", "enum": ["full", "summary"], "default": "full",
                   "description": "full includes card effects and shared hover help; summary keeps the shared compact card fields."},
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
    if "preset" in arguments and arguments["preset"] not in ("summary", "full"):
        raise ValueError("Invalid browse preset.")
    if "sort_by" in arguments and arguments["sort_by"] not in SORT_KEYS:
        raise ValueError("Invalid sorting key.")
    for key in ("view_upgrades", "descending"):
        if key in arguments and type(arguments[key]) is not bool:
            raise ValueError("Invalid boolean option.")
    if "descending" in arguments and "sort_by" not in arguments:
        raise ValueError("Sorting direction requires a key.")
    return dict(arguments)


def deck_details(state):
    context = scene_context(state)
    sort = state["sort"]
    if (context["screen"].get("view") != "deck"
            or type(state["view_upgrades"]) is not bool or not isinstance(sort, dict)
            or sort["by"] not in SORT_KEYS or type(sort["descending"]) is not bool
            or not isinstance(state["deck"], list)):
        raise ValueError("Invalid deck details.")
    return {**context, "view_upgrades": state["view_upgrades"],
            "sort": {"by": sort["by"], "descending": sort["descending"]},
            "deck": browsed_cards(state["deck"], "deck")}


def browsed_cards(items, prefix):
    from sts2_mcp.output.card_format import BROWSED_CARD, format_card
    from sts2_mcp.output.value_shapes import project
    cards = project(items, [BROWSED_CARD])
    ids = set()
    for card in cards:
        if (not {"id", "name", "type", "rarity", "visual_card_pool", "energy_cost", "star_cost", "description", "hover_tips"} <= card.keys()
                or not re.fullmatch(prefix + r":(0|[1-9][0-9]*)", card['id']) or card['id'] in ids):
            raise ValueError("Invalid browse card identity or details.")
        ids.add(card['id'])
        if any(not isinstance(card[key], str) for key in ('name', 'type', 'rarity', 'visual_card_pool', 'description')) \
                or not isinstance(card['hover_tips'], list) \
                or any(set(tip) != {'title', 'description'} for tip in card['hover_tips']):
            raise ValueError('Invalid browse card text or hover help.')
    return [format_card(card, 'full') for card in cards]


def closed_card_view(state):
    result = {**scene_context(state), **{key: state[key] for key in ("turn", "player", "enemies", "top_bar", "buttons", "available_actions")}}
    if (not isinstance(result["scene"], str) or not isinstance(result["screen"], dict)
            or not isinstance(result["screen"]["status"], str) or not isinstance(result["available_actions"], list)
            or any(not isinstance(action, str) for action in result["available_actions"])):
        raise ValueError("Invalid card view close observation.")
    result["screen"] = {"status": state["screen"]["status"]}
    if "view" in state["screen"]:
        if not isinstance(state["screen"]["view"], str):
            raise ValueError("Invalid screen view.")
        result["screen"]["view"] = state["screen"]["view"]
    from sts2_mcp.output.contracts.observation import OBSERVATION
    from sts2_mcp.output.value_shapes import project
    from sts2_mcp.output.card_format import format_game_cards
    return format_game_cards(project(result, OBSERVATION))
