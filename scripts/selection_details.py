from game_output import HAND_CARD, TIP, project, selection_details


CARD_SCHEMA = {"type": "object", "properties": {"card_id": {"type": "integer", "minimum": 0, "maximum": 2147483647}},
               "required": ["card_id"], "additionalProperties": False}
OPTION_SCHEMA = {"type": "object", "properties": {"option_id": {"type": "string", "minLength": 1, "maxLength": 128}},
                 "required": ["option_id"], "additionalProperties": False}
VIEW_SCHEMA = {"type": "object", "properties": {"view": {"type": "string", "enum": ["battlefield", "selection"]}},
               "required": ["view"], "additionalProperties": False}


def selection_arguments(operation, arguments):
    field = {"select_card": "card_id", "selection_option": "option_id", "set_selection_view": "view"}[operation]
    if not isinstance(arguments, dict) or set(arguments) != {field}:
        raise ValueError("Invalid selection arguments.")
    value = arguments[field]
    if (field == "card_id" and (type(value) is not int or not 0 <= value <= 2147483647)
            or field == "option_id" and (not isinstance(value, str) or not value.strip() or len(value) > 128)
            or field == "view" and value not in ("battlefield", "selection")):
        raise ValueError("Invalid selection argument.")
    return {field: value}


def inspect_selection_details(state):
    if state.get("scene") != "card_selection":
        raise ValueError("Invalid selection inspection scene.")
    raw = state["selection"]
    selection = selection_details(raw)
    if selection["status"] != "visible":
        raise ValueError("Selection inspection is hidden.")
    selection["cards"] = project(raw["cards"], [HAND_CARD])
    for card in selection["cards"]:
        if (not {"description", "hover_tips"} <= card.keys()
                or any(set(tip) != set(TIP) for tip in card["hover_tips"] or [])):
            raise ValueError("Incomplete selection detail.")
    if selection['type'] == 'bundle':
        selection['bundles'] = project(raw['bundles'], [{'id': str, 'cards': [HAND_CARD]}])
        if any(not {'description', 'hover_tips'} <= c.keys() for b in selection['bundles'] for c in b['cards']):
            raise ValueError('Incomplete bundle details.')
    return {"scene": "card_selection", "selection": selection}
