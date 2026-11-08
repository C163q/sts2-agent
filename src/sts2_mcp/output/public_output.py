"""Assemble already validated domain data, shared tips and public notes."""
from copy import deepcopy


ENEMY_ATTACK_INTENT_NOTE = "Attack intents include current preview modifiers; block and damage redirection affect HP loss."
CARD_VALUE_NOTE = "Card values are contextual previews; aiming may change target-specific values."


def share_hand_tips(hand):
    cards = []
    shared = {}
    for card in hand:
        cards.append({key: value for key, value in card.items() if key != "hover_tips"})
        for tip in card.get("hover_tips") or []:
            key = (tip.get("title"), tip["description"])
            if key not in shared:
                shared[key] = {"title": key[0], "description": key[1], "card_ids": []}
            if card["id"] not in shared[key]["card_ids"]:
                shared[key]["card_ids"].append(card["id"])
    return cards, list(shared.values())


def share_indexed_tips(items, index_field):
    details = []
    shared = {}
    for index, item in enumerate(items):
        if item is None:
            details.append(None)
            continue
        details.append({key: value for key, value in item.items() if key != "hover_tips"})
        for tip in item.get("hover_tips") or []:
            key = (tip.get("title"), tip["description"])
            if key not in shared:
                shared[key] = {"title": key[0], "description": key[1], index_field: []}
            if index not in shared[key][index_field]:
                shared[key][index_field].append(index)
    return details, list(shared.values())


def share_potion_tips(slots):
    return share_indexed_tips(slots, "slot_indices")


def assemble_details(details, *, operation=None):
    result = deepcopy(details)
    if "hand" in result and result["hand"] is not None:
        result["hand"], result["hover_tips"] = share_hand_tips(result["hand"])
    if "potion_slots" in result and result["potion_slots"] is not None:
        result["potion_slots"], result["hover_tips"] = share_potion_tips(result["potion_slots"])
    if "relics" in result and result["relics"] is not None:
        result["relics"], result["hover_tips"] = share_indexed_tips(result["relics"], "relic_indices")
    if "deck" in result and operation in (None, 'inspect_deck'):
        result["deck"], result["hover_tips"] = share_hand_tips(result["deck"])
    if "pile" in result and result.get("cards") is not None and operation in (None, 'inspect_pile'):
        result["cards"], result["hover_tips"] = share_hand_tips(result["cards"])
    if operation == "inspect_selection":
        result["selection"]["cards"], result["hover_tips"] = share_hand_tips(result["selection"]["cards"])
    notes = {}
    from sts2_mcp.output.presentation_status import PAGE_CONTEXTS
    pending = [key for key in PAGE_CONTEXTS if (result.get(key) or {}).get('status') == 'not_ready']
    if pending:
        notes['presentation'] = {'message': 'Page updating; displayed content and available actions may be incomplete. Read again after it settles.',
                                 'sources': pending}
    if 'nodes_by_type' in (result.get('map') or {}):
        notes['map'] = 'Map connections omitted; use inspect_map for details.'
    unavailable = result.pop('unavailable_hover_sources', [])
    if unavailable:
        notes['hover_tips_unavailable'] = {
            'message': 'Hover help is currently unavailable for these displayed icons.',
            'sources': unavailable,
        }
    if result.get('transition', {}).get('stop_reason') == 'manual_input_required' \
            or result.get('screen', {}).get('view') == 'confirmation' and result.get('confirmation') is None:
        notes['interaction'] = 'A native dialog or unsupported screen requires manual input.'
    if (result.get('divination') or {}).get('status') == 'visible':
        notes['divination'] = ('11x11 cells, (0,0) top-left; x right, y down. # covered, . empty, s partial, S fully revealed icon. '
            'Choose a # cell while playing. Known icon shapes (width x height): potion 1x3, round potion 2x2, '
            'card 2x2, box 4x4, coin 1x1, coin pile 2x1.')
        if 'cell_rows' not in result['divination']['grid']:
            notes['divination'] = ('Legacy grid: 11x11, (0,0) top-left; x right, y down. '
                '# covered, . revealed with unknown contents. Update the Mod for text fragments.')
    selection = result.get("selection") or {}
    selection_view = result.pop("selection_view", None) or selection.get("status")
    if selection_view == "visible" and selection.get("can_view_battlefield"):
        notes["selection"] = 'Use set_selection_view(view="battlefield") (eye icon) to view combat.'
    elif selection_view == "battlefield":
        notes["selection"] = 'Selection pending; return with set_selection_view(view="selection") before choosing.'
    elif selection_view == "covered":
        notes["selection"] = 'Selection pending; close this view to return.'
    elif selection_view == "unsupported":
        notes["selection"] = 'This selection requires manual input; automatic selection is unavailable.'
    if result.get("hand"):
        notes["card_values"] = CARD_VALUE_NOTE
    if result.get("scene") == "combat" and any(
        enemy.get("intents") for enemy in result.get("enemies") or []
    ):
        notes["enemy_attack_intents"] = ENEMY_ATTACK_INTENT_NOTE
    if notes:
        result["notes"] = notes
    return result
