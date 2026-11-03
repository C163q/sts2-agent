"""Compatibility projection for direct player_result callers; production uses response_pipeline."""
from sts2_mcp.output.value_shapes import nullable, project, TEXT, NUMBER, TIP
from sts2_mcp.output.contracts.cards import CARD_FACE as CARD, CARD_FULL as HAND_CARD, BROWSED_CARD
from sts2_mcp.output.contracts.combat import POWER, INTENT, HEALTH, ORB, ORB_SLOTS, BLADE, PLAYER, ENEMY, ALLY
from sts2_mcp.output.contracts.ui import RELIC, TOP_BAR, SCREEN
from sts2_mcp.output.contracts.selection import SELECTION_CARD, SELECTION_OPTION, UPGRADE_PREVIEW, SELECTION, SELECTION_OUTPUT
from sts2_mcp.output.contracts.transition import EVENT_ENTITY, TARGET_ENTITY, POTION_REF, EVENT_SOURCE, EVENT, TRANSITION
from sts2_mcp.output.contracts.rooms import REWARD_ITEM, REWARDS, REST_OPTION, REST_SITE, TREASURE_RELIC, TREASURE, SHOP_CARD, SHOP_ITEM, SHOP, ANCIENT_OPTION, ROOM_EVENT_OPTION, ROOM_EVENT, DIVINATION, ANCIENT, CONFIRMATION
from sts2_mcp.output.contracts.endings import OPTION, RESULT, EPILOGUE, PHASES, EPILOGUE_TOOLS
from sts2_mcp.output.contracts.map import MAP_SUMMARY
from sts2_mcp.output.contracts.observation import OBSERVATION, OPTIONAL_OBSERVATION
from sts2_mcp.output.scene_context import SCENES as OBSERVATION_SCENES, scene_context
from sts2_mcp.output.card_format import format_game_cards
from sts2_mcp.output.combat_fields import validate_identities, blade_refs, orb_slots
from sts2_mcp.output.hand_details import hand_details
from sts2_mcp.output.selection_details import selection_details
from sts2_mcp.output.observation_details import observation_details


GAMEPLAY = {
    'energy': NUMBER, 'max_energy': NUMBER, 'stars': NUMBER,
    'reward_result': {'reward_id': int, 'status': str},
    'purchase_result': {'item_id': int, 'status': str},
    **OBSERVATION, **OPTIONAL_OBSERVATION, "transition": TRANSITION, "hand": nullable([HAND_CARD]),
    "selection_view": str,
    "hover_tips": [{**TIP, "sources": [str]}], "slot_tip": TIP,
    "potion_slots": nullable([nullable({"name": TEXT, "description": str, "hover_tips": [TIP]})]),
    "relics": nullable([{**RELIC, "description": str, "hover_tips": [TIP]}]),
    "deck": [BROWSED_CARD], "cards": nullable([BROWSED_CARD]),
    "view_upgrades": bool, "sort": {"by": str, "descending": bool},
    "pile": str, "status": str, "reason": TEXT, "message": str,
    "card": {"id": int, "name": TEXT}, "playable": bool, "target_type": str,
    "requires_target": bool, "targets": [TARGET_ENTITY], "potion": POTION_REF, "usable": bool, "discardable": bool,
    "act": int, "current_node": TEXT, "visited_path": [str], "can_travel": bool,
    "selectable_nodes": [str], "nodes": [{
        "id": str, "row": int, "column": int, "type": str, "next": [str],
        "name": str, "revealed_type": str, "marked": bool,
    }],
}


def gameplay_fields(state, *, operation=None):
    shape = GAMEPLAY
    shop_mode = "face_full"
    if operation == 'inspect_combatants':
        shape = {**shape, 'unavailable_hover_sources': [str]}
    if operation == "inspect_selection":
        shape = {**GAMEPLAY, 'errors': [{'code': str}],
                 "selection": {**SELECTION_OUTPUT, "cards": [HAND_CARD], "bundles": [{"id": str, "cards": [HAND_CARD]}]}}
    if (state.get('rewards') or {}).get('items') and 'hover_tips' in state['rewards']['items'][0]:
        shape = {**shape, 'rewards': {**REWARDS, 'items': [{**REWARD_ITEM, 'hover_tips': [TIP]}]}}
    if (state.get('rest_site') or {}).get('options') and 'description' in state['rest_site']['options'][0]:
        shape = {**shape, 'rest_site': {**REST_SITE, 'options': [{**REST_OPTION, 'description': str}]}}
    if (state.get('treasure') or {}).get('relic') and 'description' in state['treasure']['relic']:
        shape = {**shape, 'treasure': {**TREASURE, 'relic': nullable({**TREASURE_RELIC, 'description': str, 'hover_tips': [TIP]})}}
    if state.get('scene') == 'shop' and (state.get('shop') or {}).get('items'):
        full = any('description' in (i.get('card') or i) for i in state['shop']['items'])
        if full:
            shop_mode = "full"
            shape = {**shape, 'shop': {**SHOP, 'items': nullable([{**SHOP_ITEM, 'description': str, 'hover_tips': [TIP],
                'card': {**SHOP_CARD, 'description': str, 'hover_tips': [TIP]}}])}}
    if state.get('scene') == 'ancient' and any('hover_tips' in o for o in (state.get('ancient') or {}).get('options') or []):
        shape = {**shape, 'ancient': {**ANCIENT, 'options': nullable([{**ANCIENT_OPTION, 'hover_tips': [TIP]}])}}
    if state.get('scene') == 'event' and any('hover_tips' in o for o in (state.get('event') or {}).get('options') or []):
        shape = {**shape, 'event': {**ROOM_EVENT, 'options': nullable([{**ROOM_EVENT_OPTION, 'hover_tips': [TIP]}])}}
    if 'hover_tips' in (state.get('run_result') or {}):
        from sts2_mcp.output.run_ending_details import result_details
        return format_game_cards({**project(state, shape), 'run_result': result_details(state['run_result'], full=True)}, shop_mode=shop_mode)
    return format_game_cards(project(state, shape), shop_mode=shop_mode)
