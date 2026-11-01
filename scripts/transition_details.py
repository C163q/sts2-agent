from game_output import TRANSITION, observation_details, project
from available_tools import INSPECTIONS, VIEWS


REASONS = {"player_ready", "choice_required", "combat_won", "combat_lost", "run_lost", "timeout", "interrupted", "selection_resolved", "action_canceled", "action_completed", 'manual_input_required'}
FIELDS = {
    "damage": {"target", "hp_loss", "blocked"},
    "hp_changed": {"target", "before", "after"},
    "max_hp_changed": {"target", "before", "after"},
    "gold_changed": {"target", "before", "after"},
    "energy_changed": {"target", "before", "after"},
    "stars_changed": {"target", "before", "after"},
    "block_changed": {"target", "before", "after"},
    "power_changed": {"target", "name", "change", "before", "after"},
    "died": {"target"}, "revived": {"target"}, "creature_added": {"target"},
    "card_played": {"card", "autoplay"}, "card_drawn": {"card"},
    "card_discarded": {"card"}, "card_exhausted": {"card"},
    "card_added": {"card"},
    "potion_used": {"potion"}, "potion_discarded": {"potion"},
    "potion_obtained": {"potion"},
    "relic_obtained": {"relic"}, "relic_removed": {"relic"},
    "card_removed": {"card", "pile"}, "card_upgraded": {"card", "pile"},
    "card_downgraded": {"card", "pile"}, "card_enchantment_changed": {"card", "pile"},
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
                or event["source"]["kind"] not in {"card", "power", "relic", "potion"}):
            raise ValueError("Invalid event source.")
        if "card" in event and (set(event["card"]) != {"id", "name"} or event["card"]["id"] < 0):
            raise ValueError("Invalid event card.")
        if "potion" in event and (set(event["potion"]) != {"slot_index", "name"}
                                  or not 0 <= event["potion"]["slot_index"] <= 2147483647):
            raise ValueError("Invalid event potion.")
        if 'pile' in event and (event['pile'] != 'deck' or kind not in {
                'card_added', 'card_removed', 'card_upgraded', 'card_downgraded', 'card_enchantment_changed'}):
            raise ValueError('Invalid permanent card scope.')
        if kind in {'card_removed', 'card_upgraded', 'card_downgraded', 'card_enchantment_changed'} or 'pile' in event:
            if not event['card']['name']:
                raise ValueError('Missing visible permanent card identity.')
        if kind in {'relic_obtained', 'relic_removed'} and (
                set(event['relic']) != {'name'} or not event['relic']['name']):
            raise ValueError('Invalid visible relic identity.')
        if kind == 'potion_obtained' and not event['potion']['name']:
            raise ValueError('Missing visible potion identity.')
        if any(event.get(key) is not None and event[key] < 0 for key in ("hp_loss", "blocked")):
            raise ValueError("Invalid event damage.")
        if kind in {"hp_changed", "block_changed"} and any(type(event[key]) is not int for key in ("before", "after")):
            raise ValueError("Invalid event values.")
        if kind in {'max_hp_changed', 'gold_changed', 'energy_changed', 'stars_changed'}:
            before, after = event['before'], event['after']
            if (event['target']['kind'] != 'player' or type(after) is not int or after < 0
                    or not (type(before) is int and before >= 0 or kind == 'stars_changed' and before is None)):
                raise ValueError('Invalid player resource change.')
        if kind == "power_changed" and event["change"] not in {"applied", "modified", "removed"}:
            raise ValueError("Invalid power change.")
    result["transition"] = transition
    if transition["stop_reason"] not in {"player_ready", "action_completed"} or not transition["complete"]:
        result["available_actions"] = [action for action in result["available_actions"]
            if transition["complete"] and transition["stop_reason"] == "choice_required"
            and (result.get("selection") or {}).get("status") == "visible"
            and action in INSPECTIONS | VIEWS | {"select_card", "selection_option"}]
    return result
