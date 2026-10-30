from game_output import TRANSITION, observation_details, project


REASONS = {"player_ready", "choice_required", "combat_won", "combat_lost", "timeout", "interrupted", "selection_resolved", "action_canceled"}
FIELDS = {
    "damage": {"target", "hp_loss", "blocked"},
    "hp_changed": {"target", "before", "after"},
    "block_changed": {"target", "before", "after"},
    "power_changed": {"target", "name", "change", "before", "after"},
    "died": {"target"}, "revived": {"target"}, "creature_added": {"target"},
    "card_played": {"card", "autoplay"}, "card_drawn": {"card"},
    "card_discarded": {"card"}, "card_exhausted": {"card"},
    "card_added": {"card"},
}


def end_turn_details(state):
    result = observation_details(state)
    transition = project(state["transition"], TRANSITION)
    if (set(transition) != set(TRANSITION) or transition["stop_reason"] not in REASONS
            or (transition["stop_reason"] in {"timeout", "interrupted"} and transition["complete"])):
        raise ValueError("Invalid turn transition.")
    previous = 0
    for event in transition["events"]:
        kind = event.get("type")
        if (kind not in FIELDS or not FIELDS[kind] <= event.keys()
                or event.get("sequence", 0) <= previous):
            raise ValueError("Invalid transition event.")
        previous = event["sequence"]
        for key in ("actor", "target"):
            if key in event and (set(event[key]) != {"id", "kind", "name"}
                                or event[key]["kind"] not in {"player", "enemy", "ally"}):
                raise ValueError("Invalid event entity.")
        if event.get("source") is not None and (
                set(event["source"]) != {"kind", "name"}
                or event["source"]["kind"] not in {"card", "power", "relic"}):
            raise ValueError("Invalid event source.")
        if "card" in event and (set(event["card"]) != {"id", "name"} or event["card"]["id"] < 0):
            raise ValueError("Invalid event card.")
        if any(event.get(key) is not None and event[key] < 0 for key in ("hp_loss", "blocked")):
            raise ValueError("Invalid event damage.")
        if kind in {"hp_changed", "block_changed"} and any(type(event[key]) is not int for key in ("before", "after")):
            raise ValueError("Invalid event values.")
        if kind == "power_changed" and event["change"] not in {"applied", "modified", "removed"}:
            raise ValueError("Invalid power change.")
    result["transition"] = transition
    if transition["stop_reason"] != "player_ready" or not transition["complete"]:
        result["available_actions"] = [action for action in result["available_actions"]
            if transition["complete"] and transition["stop_reason"] == "choice_required"
            and (result.get("selection") or {}).get("status") == "visible"
            and action in {"select_card", "selection_option"}]
    return result
