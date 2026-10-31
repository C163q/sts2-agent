from combatant_details import combatant_details
from deck_details import closed_card_view, deck_details
from game_output import hand_details, observation_details
from map_details import closed_map, map_details
from pile_details import pile_details
from relic_details import relic_details
from transition_details import end_turn_details
from selection_details import inspect_selection_details
from card_play_details import target_details
from reward_details import claim_reward_details, inspect_rewards_details
from rest_site_details import inspect_rest_site_details
from treasure_details import inspect_treasure_details
from shop_details import inspect_shop_details, purchase_details
from event_details import inspect_event_details


def potion_details(state):
    def tip_text(tip):
        if (not isinstance(tip, dict)
                or (tip["title"] is not None and not isinstance(tip["title"], str))
                or not isinstance(tip["description"], str)):
            raise ValueError("Invalid potion hover tip.")
        return {"title": tip["title"], "description": tip["description"]}

    common = tip_text(state["slot_tip"])
    slots = state["potion_slots"]
    if not isinstance(slots, list):
        raise ValueError("Invalid potion slots.")
    potions = []
    for potion in slots:
        if potion is None:
            potions.append(None)
            continue
        if (not isinstance(potion, dict)
                or (potion["name"] is not None and not isinstance(potion["name"], str))
                or not isinstance(potion["description"], str)
                or not isinstance(potion["hover_tips"], list)):
            raise ValueError("Invalid potion details.")
        potions.append({"name": potion["name"], "description": potion["description"],
                        "hover_tips": [tip_text(tip) for tip in potion["hover_tips"]]})
    return {"slot_tip": common, "potion_slots": potions}


def ui_details(state):
    tips = state.get("hover_tips")
    if state.get("scene") != "combat" or not isinstance(tips, list):
        raise ValueError("Invalid UI details.")
    for tip in tips:
        if (not isinstance(tip, dict)
                or (tip.get("title") is not None and not isinstance(tip["title"], str))
                or not isinstance(tip.get("description"), str)
                or not isinstance(tip.get("sources"), list) or not tip["sources"]
                or any(not isinstance(source, str) or not source for source in tip["sources"])):
            raise ValueError("Invalid UI hover tip.")
    return {"scene": state["scene"], "hover_tips": [
        {key: tip[key] for key in ("title", "description", "sources")} for tip in tips]}


from ancient_details import inspect_ancient_details


READERS = {
    'respond_to_confirmation': end_turn_details,
    'set_divination_tool': end_turn_details,
    'divine': end_turn_details,
    'inspect_event': inspect_event_details,
    'choose_event_option': end_turn_details,
    'inspect_ancient': inspect_ancient_details,
    'choose_ancient_option': end_turn_details,
    'advance_dialogue': end_turn_details,
    'inspect_shop': inspect_shop_details,
    'open_shop': end_turn_details,
    'close_shop': end_turn_details,
    'buy_item': purchase_details,
    "get_state": observation_details,
    "end_turn": end_turn_details,
    "inspect_hand": hand_details,
    "inspect_ui": ui_details,
    "inspect_potions": potion_details,
    "inspect_combatants": combatant_details,
    "inspect_relics": relic_details,
    "close_card_view": closed_card_view,
    "inspect_map": map_details,
    "close_map": closed_map,
    "inspect_selection": inspect_selection_details,
    "set_selection_view": observation_details,
    "select_card": end_turn_details,
    "selection_option": end_turn_details,
    "play_card": end_turn_details,
    "use_potion": end_turn_details,
    "discard_potion": end_turn_details,
    'claim_reward': claim_reward_details,
    'proceed': end_turn_details,
    'inspect_rewards': inspect_rewards_details,
    'inspect_rest_site': inspect_rest_site_details,
    'choose_rest_option': end_turn_details,
    'loot_treasure': end_turn_details,
    'inspect_treasure': inspect_treasure_details,
}


def _read_details(operation, state, arguments=None):
    if operation == "inspect_targets":
        return target_details(state, arguments)
    if operation == "inspect_deck":
        return deck_details(state, (arguments or {}).get("detail_level", "summary"))
    if operation == "inspect_pile":
        return pile_details(state, arguments["pile"], arguments.get("detail_level", "summary"))
    return READERS[operation](state)


def inspection_details(operation, state, arguments=None):
    result = _read_details(operation, state, arguments)
    if "selection_view" in state:
        if state["selection_view"] not in {"visible", "battlefield", "covered", "unsupported"}:
            raise ValueError("Invalid pending selection view.")
        result["selection_view"] = state["selection_view"]
    return result
