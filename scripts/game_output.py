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
GAMEPLAY = {
    **OBSERVATION, "transition": TRANSITION, "hand": nullable([HAND_CARD]),
    "hover_tips": [{**TIP, "sources": [str]}], "slot_tip": TIP,
    "potion_slots": nullable([nullable({"name": TEXT, "description": str, "hover_tips": [TIP]})]),
    "relics": nullable([{**RELIC, "description": str, "hover_tips": [TIP]}]),
    "deck": [BROWSED_CARD], "cards": nullable([BROWSED_CARD]),
    "detail_level": str, "view_upgrades": bool, "sort": {"by": str, "descending": bool},
    "pile": str, "status": str, "reason": str, "message": str,
    "act": int, "current_node": TEXT, "visited_path": [str], "can_travel": bool,
    "selectable_nodes": [str], "nodes": [{
        "id": str, "row": int, "column": int, "type": str, "next": [str],
        "name": str, "revealed_type": str, "marked": bool,
    }],
}


def gameplay_fields(state):
    return project(state, GAMEPLAY)


def observation_details(state):
    result = project(state, OBSERVATION)
    if (set(result) != set(OBSERVATION) or "status" not in result["screen"]
            or result["scene"] not in ("combat", "main_menu", "loading_or_noncombat")
            or result["screen"]["status"] not in ("visible", "covered", "hidden", "not_ready", "not_applicable")):
        raise ValueError("Invalid observation structure.")
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
