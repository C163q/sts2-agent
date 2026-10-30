def nullable(shape):
    return (shape,)


def project(value, shape):
    """Copy declared fields; a tuple allows null and a list describes array items."""
    if isinstance(shape, tuple):
        if value is None:
            return None
        return project(value, shape[0])
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            raise ValueError("Expected a gameplay object.")
        return {key: project(item, shape[key]) for key, item in value.items() if key in shape}
    if isinstance(shape, list):
        if not isinstance(value, list):
            raise ValueError("Expected a gameplay array.")
        return [project(item, shape[0]) for item in value]
    # bool is an int subclass; accepting it would hide malformed numeric fields.
    if type(value) is not shape:
        raise ValueError("Invalid gameplay field type.")
    return value


TEXT = nullable(str)
NUMBER = nullable(int)
TIP = {"title": TEXT, "description": str}
CARD = {
    "id": int, "name": TEXT, "type": TEXT, "rarity": TEXT, "visual_card_pool": TEXT,
    "energy_cost": TEXT, "star_cost": TEXT, "energy_cost_color": str, "star_cost_color": str,
    "unplayable_markers": [str], "outline": str,
}
HAND_CARD = {**CARD, "description": TEXT, "hover_tips": nullable([TIP])}
BROWSED_CARD = {**HAND_CARD, "id": str}
POWER = {"name": TEXT, "amount": NUMBER}
INTENT = {"category": TEXT, "value": TEXT}
HEALTH = {"hp": NUMBER, "max_hp": NUMBER, "hp_display": str, "block": NUMBER}
PLAYER = {
    **HEALTH, "character": TEXT, "energy": NUMBER, "max_energy": NUMBER, "stars": NUMBER,
    "powers": nullable([POWER]), "hand": nullable([CARD]),
    "draw_count": NUMBER, "discard_count": NUMBER, "exhaust_count": NUMBER,
}
ENEMY = {
    **HEALTH, "id": NUMBER, "name": TEXT, "powers": nullable([POWER]),
    "intents": nullable([INTENT]),
}
RELIC = {"name": TEXT, "counter": NUMBER}
TOP_BAR = {
    "gold": NUMBER, "floor": NUMBER, "ascension": NUMBER, "deck_count": NUMBER,
    "room_icon": TEXT, "bosses": [TEXT], "potion_slots": nullable([nullable({"name": TEXT})]),
    "relics": nullable([RELIC]), "map_visible": bool, "deck_visible": bool, "settings_visible": bool,
}
SCREEN = {"status": str, "view": str}
SELECTION_CARD = {**CARD, "description": TEXT}
SELECTION_OPTION = {"id": str, "text": TEXT, "enabled": bool}
SELECTION = {
    "type": str, "status": str, "prompt": TEXT, "min_select": NUMBER, "max_select": NUMBER,
    "selected_ids": nullable([int]), "cards": nullable([SELECTION_CARD]),
    "options": [SELECTION_OPTION], "can_view_battlefield": bool,
}
EVENT_ENTITY = {"id": int, "kind": str, "name": TEXT}
EVENT_SOURCE = {"kind": str, "name": TEXT}
EVENT = {
    "sequence": int, "type": str, "actor": EVENT_ENTITY, "target": EVENT_ENTITY,
    "source": nullable(EVENT_SOURCE), "card": {"id": int, "name": TEXT},
    "hp_loss": NUMBER, "blocked": int, "before": NUMBER, "after": NUMBER,
    "name": TEXT, "autoplay": bool, "change": str,
}
TRANSITION = {"stop_reason": str, "complete": bool, "events": [EVENT]}
OBSERVATION = {
    "scene": str, "screen": SCREEN, "turn": NUMBER, "player": nullable(PLAYER),
    "enemies": nullable([ENEMY]), "top_bar": nullable(TOP_BAR),
    "buttons": nullable({"end_turn": nullable({"text": TEXT, "enabled": bool})}),
    "available_actions": [str],
}
OPTIONAL_OBSERVATION = {"selection": nullable(SELECTION)}
GAMEPLAY = {
    **OBSERVATION, **OPTIONAL_OBSERVATION, "transition": TRANSITION, "hand": nullable([HAND_CARD]),
    "selection_view": str,
    "hover_tips": [{**TIP, "sources": [str]}], "slot_tip": TIP,
    "potion_slots": nullable([nullable({"name": TEXT, "description": str, "hover_tips": [TIP]})]),
    "relics": nullable([{**RELIC, "description": str, "hover_tips": [TIP]}]),
    "deck": [BROWSED_CARD], "cards": nullable([BROWSED_CARD]),
    "detail_level": str, "view_upgrades": bool, "sort": {"by": str, "descending": bool},
    "pile": str, "status": str, "reason": TEXT, "message": str,
    "card": {"id": int, "name": TEXT}, "playable": bool, "target_type": str,
    "requires_target": bool, "targets": [EVENT_ENTITY],
    "act": int, "current_node": TEXT, "visited_path": [str], "can_travel": bool,
    "selectable_nodes": [str], "nodes": [{
        "id": str, "row": int, "column": int, "type": str, "next": [str],
        "name": str, "revealed_type": str, "marked": bool,
    }],
}


def gameplay_fields(state):
    shape = GAMEPLAY
    if state.get("scene") == "card_selection":
        shape = {**GAMEPLAY, "selection": {**SELECTION, "cards": [HAND_CARD]}}
    return project(state, shape)


def observation_details(state):
    result = project(state, {**OBSERVATION, **OPTIONAL_OBSERVATION})
    if (not set(OBSERVATION) <= result.keys() or "status" not in result["screen"]
            or result["scene"] not in ("combat", "main_menu", "loading_or_noncombat")
            or result["screen"]["status"] not in ("visible", "covered", "hidden", "not_ready", "not_applicable")):
        raise ValueError("Invalid observation structure.")
    if result.get("selection") is not None:
        result["selection"] = selection_details(result["selection"])
    return result


def selection_details(value):
    result = project(value, SELECTION)
    if (set(result) != set(SELECTION) or result["type"] not in
            {"choose_one", "reward", "grid", "combat_pile", "deck", "hand", "unsupported"}
            or result["status"] not in {"visible", "battlefield", "covered", "unsupported"}):
        raise ValueError("Invalid card selection.")
    if result["status"] != "visible":
        if (any(result[key] is not None for key in
                ("prompt", "min_select", "max_select", "selected_ids", "cards")) or result["options"]):
            raise ValueError("Hidden selection contents.")
        return result
    minimum, maximum = result["min_select"], result["max_select"]
    if (type(minimum) is not int or type(maximum) is not int or not 0 <= minimum <= maximum
            or result["cards"] is None or result["selected_ids"] is None
            or any(i < 0 for i in result["selected_ids"])
            or len(set(result["selected_ids"])) != len(result["selected_ids"])):
        raise ValueError("Invalid selection rules.")
    ids = []
    for card in result["cards"]:
        if not {"id", "name"} <= card.keys() or card["id"] < 0:
            raise ValueError("Invalid selection card.")
        ids.append(card["id"])
    if len(set(ids)) != len(ids):
        raise ValueError("Repeated selection card.")
    options = []
    for option in result["options"]:
        if set(option) != set(SELECTION_OPTION) or not option["id"]:
            raise ValueError("Invalid selection option.")
        options.append(option["id"])
    if len(set(options)) != len(options):
        raise ValueError("Repeated selection option.")
    return result


def hand_details(state):
    hand = project(state["hand"], [HAND_CARD])
    ids = set()
    for card in hand:
        if (not {"id", "name", "description", "hover_tips"} <= card.keys()
                or card["id"] < 0 or card["id"] in ids):
            raise ValueError("Invalid hand card identity or details.")
        ids.add(card["id"])
        for tip in card["hover_tips"] or []:
            if set(tip) != set(TIP):
                raise ValueError("Invalid hand hover tip.")
    return {"hand": hand}
