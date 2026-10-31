INSPECTIONS = frozenset({
    'inspect_hand', 'inspect_ui', 'inspect_potions', 'inspect_combatants', 'inspect_relics',
    'inspect_selection', 'inspect_targets', 'inspect_rewards', 'inspect_rest_site', 'inspect_treasure',
    'inspect_shop', 'inspect_ancient', 'inspect_event', 'inspect_run_result',
})
VIEWS = frozenset({'inspect_deck', 'inspect_pile', 'close_card_view', 'inspect_map', 'close_map', 'set_selection_view'})
GAME_ACTIONS = frozenset({
    'play_card', 'end_turn', 'use_potion', 'discard_potion', 'select_card', 'selection_option',
    'claim_reward', 'proceed', 'choose_rest_option', 'loot_treasure', 'open_shop', 'close_shop', 'buy_item',
    'choose_ancient_option', 'advance_dialogue', 'choose_event_option', 'set_divination_tool', 'divine',
    'respond_to_confirmation', 'travel_to_node', 'run_result_option',
})
PUBLIC_TOOLS = INSPECTIONS | VIEWS | GAME_ACTIONS


def public_tools(actions):
    return list(dict.fromkeys(action for action in actions if action in PUBLIC_TOOLS))
