from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.combatant_details import combatant_details
from sts2_mcp.output.deck_details import closed_card_view, deck_details
from sts2_mcp.output.hand_details import hand_details
from sts2_mcp.output.observation_details import observation_details
from sts2_mcp.output.ui_details import ui_details
from sts2_mcp.output.potion_details import potion_details
from sts2_mcp.output.map_details import map_details
from sts2_mcp.output.view_details import closed_map
from sts2_mcp.output.pile_details import pile_details
from sts2_mcp.output.relic_details import relic_details
from sts2_mcp.output.transition_details import end_turn_details
from sts2_mcp.output.selection_details import inspect_selection_details
from sts2_mcp.output.card_play_details import target_details
from sts2_mcp.output.reward_details import inspect_rewards_details
from sts2_mcp.output.action_details import claim_reward_details, purchase_details
from sts2_mcp.output.rest_site_details import inspect_rest_site_details
from sts2_mcp.output.treasure_details import inspect_treasure_details
from sts2_mcp.output.shop_details import inspect_shop_details
from sts2_mcp.output.event_details import inspect_event_details






from sts2_mcp.output.ancient_details import inspect_ancient_details


from sts2_mcp.output.run_ending_details import inspect_result_details

READERS = {
    # File-client compatibility; neither entry is exposed in the MCP catalog.
    'start_test_combat': observation_details,
    'close_deck': closed_card_view,
    'inspect_run_result': inspect_result_details,
    'run_result_option': end_turn_details,
    'travel_to_node': end_turn_details,
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
        return deck_details(state)
    if operation == "inspect_pile":
        return pile_details(state, arguments["pile"])
    return READERS[operation](state)


def inspection_details(operation, state, arguments=None):
    result = _read_details(operation, state, arguments)
    if "scene" in result:
        result.update(scene_context(state))
    if "selection_view" in state:
        if state["selection_view"] not in {"visible", "battlefield", "covered", "unsupported"}:
            raise ValueError("Invalid pending selection view.")
        result["selection_view"] = state["selection_view"]
    return result
