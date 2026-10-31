def nullable(shape):
    return (shape,)


def project(value, shape):
    """Copy declared fields; a tuple allows null and a list describes array items."""
    if isinstance(shape, frozenset):
        if type(value) not in shape:
            raise ValueError("Invalid gameplay scalar type.")
        return value
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
    "hp": NUMBER, "max_hp": NUMBER,
    "gold": NUMBER, "floor": NUMBER, "ascension": NUMBER, "deck_count": NUMBER,
    "room_icon": TEXT, "bosses": [TEXT], "potion_slots": nullable([nullable({"name": TEXT, "usable_here": bool, "bouncing": bool})]),
    "relics": nullable([RELIC]), "map_visible": bool, "deck_visible": bool, "settings_visible": bool,
}
SCREEN = {"status": str, "view": str}
SELECTION_CARD = {**CARD, "description": TEXT}
SELECTION_OPTION = {"id": str, "text": TEXT, "enabled": bool}
UPGRADE_PREVIEW = {"before": SELECTION_CARD, "after": SELECTION_CARD}
SELECTION = {
    "type": str, "status": str, "prompt": TEXT, "min_select": NUMBER, "max_select": NUMBER,
    "selected_ids": nullable([int]), "cards": nullable([SELECTION_CARD]),
    "options": [SELECTION_OPTION], "can_view_battlefield": bool,
}
SELECTION_OUTPUT = {**SELECTION, "enchantment": nullable({"title": str, "description": str}), "enchant_previews": [UPGRADE_PREVIEW],
                    "transform_previews": [{"before": SELECTION_CARD, "after": nullable(SELECTION_CARD), "random": bool}],
                    "bundles": [{"id": str, "cards": [SELECTION_CARD]}], "upgrade_preview": nullable(UPGRADE_PREVIEW), "upgrade_previews": [UPGRADE_PREVIEW]}
EVENT_ENTITY = {"id": int, "kind": str, "name": TEXT}
TARGET_ENTITY = {**EVENT_ENTITY, "id": frozenset({int, str})}
POTION_REF = {"slot_index": int, "name": TEXT}
EVENT_SOURCE = {"kind": str, "name": TEXT}
EVENT = {
    "sequence": int, "type": str, "actor": EVENT_ENTITY, "target": EVENT_ENTITY,
    "source": nullable(EVENT_SOURCE), "card": {"id": int, "name": TEXT},
    "hp_loss": NUMBER, "blocked": int, "before": NUMBER, "after": NUMBER,
    "name": TEXT, "autoplay": bool, "change": str, "potion": POTION_REF,
}
TRANSITION = {"stop_reason": str, "complete": bool, "events": [EVENT]}
REWARD_ITEM = {'id': int, 'type': str, 'text': str, 'enabled': bool, 'linked_group': NUMBER}
REWARDS = {'status': str, 'title': TEXT, 'items': nullable([REWARD_ITEM]),
           'proceed': nullable({'text': str, 'enabled': bool, 'skips_remaining': bool})}
REST_OPTION = {'id': str, 'text': str, 'enabled': bool}
REST_SITE = {'status': str, 'prompt': TEXT, 'description': TEXT, 'options': nullable([REST_OPTION]),
             'proceed': nullable({'text': str, 'enabled': bool})}
TREASURE_RELIC = {'name': str, 'enabled': bool}
TREASURE = {'status': str, 'chest': TEXT, 'relic': nullable(TREASURE_RELIC),
            'proceed': nullable({'text': str, 'enabled': bool, 'skips_remaining': bool})}
SHOP_CARD = {key: BROWSED_CARD[key] for key in ('name', 'type', 'rarity', 'visual_card_pool', 'energy_cost', 'star_cost')}
SHOP_ITEM = {'id': int, 'kind': str, 'position': str, 'price': NUMBER, 'affordable': nullable(bool),
             'enabled': bool, 'name': str, 'used': bool, 'on_sale': bool, 'card': SHOP_CARD}
SHOP = {'status': str, 'view': TEXT, 'items': nullable([SHOP_ITEM]),
        'open': nullable({'enabled': bool}), 'back': nullable({'enabled': bool}),
        'proceed': nullable({'text': str, 'enabled': bool})}
ANCIENT_OPTION = {'id': int, 'title': str, 'description': str, 'enabled': bool}
ROOM_EVENT_OPTION = {**ANCIENT_OPTION, 'lethal_warning': bool}
ROOM_EVENT = {'status': str, 'name': TEXT, 'description': TEXT, 'options': nullable([ROOM_EVENT_OPTION]),
              'proceed': nullable({'text': str, 'enabled': bool})}
ANCIENT = {'status': str, 'name': TEXT, 'epithet': TEXT, 'description': TEXT, 'dialogue': nullable([{'speaker': str, 'text': str}]),
           'options': nullable([ANCIENT_OPTION]), 'continue': nullable({'text': TEXT, 'enabled': bool}),
           'proceed': nullable({'text': str, 'enabled': bool})}
OBSERVATION = {
    "scene": str, "screen": SCREEN, "turn": NUMBER, "player": nullable(PLAYER),
    "enemies": nullable([ENEMY]), "top_bar": nullable(TOP_BAR),
    "buttons": nullable({"end_turn": nullable({"text": TEXT, "enabled": bool})}),
    "available_actions": [str],
}
OPTIONAL_OBSERVATION = {"event": nullable(ROOM_EVENT), "ancient": nullable(ANCIENT),"selection": nullable(SELECTION_OUTPUT), 'rewards': nullable(REWARDS), 'rest_site': nullable(REST_SITE), 'treasure': nullable(TREASURE), 'shop': nullable(SHOP)}
GAMEPLAY = {
    'reward_result': {'reward_id': int, 'status': str},
    'purchase_result': {'item_id': int, 'status': str},
    **OBSERVATION, **OPTIONAL_OBSERVATION, "transition": TRANSITION, "hand": nullable([HAND_CARD]),
    "selection_view": str,
    "hover_tips": [{**TIP, "sources": [str]}], "slot_tip": TIP,
    "potion_slots": nullable([nullable({"name": TEXT, "description": str, "hover_tips": [TIP]})]),
    "relics": nullable([{**RELIC, "description": str, "hover_tips": [TIP]}]),
    "deck": [BROWSED_CARD], "cards": nullable([BROWSED_CARD]),
    "detail_level": str, "view_upgrades": bool, "sort": {"by": str, "descending": bool},
    "pile": str, "status": str, "reason": TEXT, "message": str,
    "card": {"id": int, "name": TEXT}, "playable": bool, "target_type": str,
    "requires_target": bool, "targets": [TARGET_ENTITY], "potion": POTION_REF, "usable": bool, "discardable": bool,
    "act": int, "current_node": TEXT, "visited_path": [str], "can_travel": bool,
    "selectable_nodes": [str], "nodes": [{
        "id": str, "row": int, "column": int, "type": str, "next": [str],
        "name": str, "revealed_type": str, "marked": bool,
    }],
}


def gameplay_fields(state):
    shape = GAMEPLAY
    if state.get("scene") == "card_selection":
        shape = {**GAMEPLAY, "selection": {**SELECTION_OUTPUT, "cards": [HAND_CARD], "bundles": [{"id": str, "cards": [HAND_CARD]}]}}
    if (state.get('rewards') or {}).get('items') and 'hover_tips' in state['rewards']['items'][0]:
        shape = {**shape, 'rewards': {**REWARDS, 'items': [{**REWARD_ITEM, 'hover_tips': [TIP]}]}}
    if (state.get('rest_site') or {}).get('options') and 'description' in state['rest_site']['options'][0]:
        shape = {**shape, 'rest_site': {**REST_SITE, 'options': [{**REST_OPTION, 'description': str}]}}
    if (state.get('treasure') or {}).get('relic') and 'description' in state['treasure']['relic']:
        shape = {**shape, 'treasure': {**TREASURE, 'relic': nullable({**TREASURE_RELIC, 'description': str, 'hover_tips': [TIP]})}}
    if state.get('scene') == 'shop' and (state.get('shop') or {}).get('items'):
        full = any('description' in (i.get('card') or i) for i in state['shop']['items'])
        if full:
            shape = {**shape, 'shop': {**SHOP, 'items': nullable([{**SHOP_ITEM, 'description': str, 'hover_tips': [TIP],
                'card': {**SHOP_CARD, 'description': str, 'hover_tips': [TIP]}}])}}
    if state.get('scene') == 'ancient' and any('hover_tips' in o for o in (state.get('ancient') or {}).get('options') or []):
        shape = {**shape, 'ancient': {**ANCIENT, 'options': nullable([{**ANCIENT_OPTION, 'hover_tips': [TIP]}])}}
    if state.get('scene') == 'event' and any('hover_tips' in o for o in (state.get('event') or {}).get('options') or []):
        shape = {**shape, 'event': {**ROOM_EVENT, 'options': nullable([{**ROOM_EVENT_OPTION, 'hover_tips': [TIP]}])}}
    return project(state, shape)


def observation_details(state):
    result = project(state, {**OBSERVATION, **OPTIONAL_OBSERVATION})
    if (not set(OBSERVATION) <= result.keys() or "status" not in result["screen"]
            or result["scene"] not in ("combat", "main_menu", "loading_or_noncombat", "rewards", 'rest_site', 'treasure', 'shop', 'ancient', 'event')
            or result["screen"]["status"] not in ("visible", "covered", "hidden", "not_ready", "not_applicable")):
        raise ValueError("Invalid observation structure.")
    if result.get("selection") is not None:
        result["selection"] = selection_details(result["selection"])
    if result.get('rewards') is not None:
        from reward_details import rewards_details
        result['rewards'] = rewards_details(result['rewards'])
    elif result['scene'] == 'rewards':
        raise ValueError('Missing rewards state.')
    if result.get('rest_site') is not None:
        from rest_site_details import rest_site_details
        result['rest_site'] = rest_site_details(result['rest_site'])
    elif result['scene'] == 'rest_site':
        raise ValueError('Missing rest site state.')
    if result.get('treasure') is not None:
        from treasure_details import treasure_details
        result['treasure'] = treasure_details(result['treasure'])
    elif result['scene'] == 'treasure':
        raise ValueError('Missing treasure state.')
    if result.get('shop') is not None:
        from shop_details import shop_details
        result['shop'] = shop_details(result['shop'])
    elif result['scene'] == 'shop':
        raise ValueError('Missing shop state.')
    if result.get('ancient') is not None:
        from ancient_details import ancient_details
        result['ancient'] = ancient_details(result['ancient'])
    elif result['scene'] == 'ancient':
        raise ValueError('Missing ancient state.')
    if result.get('event') is not None:
        from event_details import event_details
        result['event'] = event_details(result['event'])
    elif result['scene'] == 'event':
        raise ValueError('Missing event state.')
    return result


def selection_details(value):
    result = project(value, SELECTION_OUTPUT)
    if (not set(SELECTION) <= result.keys() or result["type"] not in
            {"choose_one", "reward", "grid", "combat_pile", "deck", "deck_upgrade", "deck_enchant", "deck_transform", "bundle", "view_cards", "hand", "hand_upgrade", "unsupported"}
            or result["status"] not in {"visible", "battlefield", "covered", "unsupported"}):
        raise ValueError("Invalid card selection.")
    preview = result.get("upgrade_preview")
    if result["type"] == "hand_upgrade":
        if "upgrade_preview" not in result:
            raise ValueError("Missing upgrade preview state.")
        if preview is not None and (set(preview) != set(UPGRADE_PREVIEW)
                or any(not {"id", "name", "description"} <= card.keys() or card['id'] < 0
                       for card in preview.values())
                or result["selected_ids"] != [preview['before']['id']]
                or preview['before']['id'] != preview['after']['id']):
            raise ValueError("Invalid upgrade preview.")
    elif preview is not None:
        raise ValueError("Unexpected upgrade preview.")
    previews = result.get('upgrade_previews', [])
    if result['type'] == 'deck_upgrade':
        if 'upgrade_previews' not in result:
            raise ValueError('Missing deck upgrade previews.')
        preview_ids = []
        for pair in previews:
            if (set(pair) != set(UPGRADE_PREVIEW) or any(not {'id', 'name', 'description'} <= c.keys() or c['id'] < 0
                                                       for c in pair.values())
                    or pair['before']['id'] != pair['after']['id']):
                raise ValueError('Invalid deck upgrade preview identity.')
            preview_ids.append(pair['before']['id'])
        if len(set(preview_ids)) != len(preview_ids) or previews and set(preview_ids) != set(result['selected_ids'] or []):
            raise ValueError('Invalid deck upgrade preview selection.')
    elif previews:
        raise ValueError('Unexpected deck upgrade previews.')
    transformations = result.get('transform_previews', [])
    if result['type'] == 'deck_transform':
        if 'transform_previews' not in result: raise ValueError('Missing transform previews.')
        preview_ids = []
        for pair in transformations:
            if (set(pair) != {'before', 'after', 'random'} or not {'id', 'name', 'description'} <= pair['before'].keys()
                    or pair['before']['id'] < 0 or pair['random'] != (pair['after'] is None)
                    or pair['after'] is not None and (not {'id', 'name', 'description'} <= pair['after'].keys()
                                                     or pair['after']['id'] != pair['before']['id'])):
                raise ValueError('Invalid transform preview.')
            preview_ids.append(pair['before']['id'])
        if len(set(preview_ids)) != len(preview_ids) or transformations and set(preview_ids) != set(result['selected_ids'] or []):
            raise ValueError('Invalid transform selection.')
    elif transformations: raise ValueError('Unexpected transform previews.')
    bundles = result.get('bundles', [])
    if result['type'] == 'bundle':
        if 'bundles' not in result or any(set(b) != {'id', 'cards'} or not b['id'].startswith('bundle:')
                                         or any(not {'id', 'name'} <= c.keys() for c in b['cards']) for b in bundles):
            raise ValueError('Invalid bundles.')
        if len({b['id'] for b in bundles}) != len(bundles): raise ValueError('Repeated bundle.')
    elif bundles: raise ValueError('Unexpected bundles.')
    enchantment = result.get('enchantment')
    enchanted = result.get('enchant_previews', [])
    if result['type'] == 'deck_enchant':
        if 'enchantment' not in result or 'enchant_previews' not in result:
            raise ValueError('Missing enchantment preview state.')
        if enchantment is not None and set(enchantment) != {'title', 'description'}:
            raise ValueError('Invalid enchantment help.')
        preview_ids = []
        for pair in enchanted:
            if (set(pair) != set(UPGRADE_PREVIEW) or any(not {'id', 'name', 'description'} <= c.keys() or c['id'] < 0
                                                      for c in pair.values()) or pair['before']['id'] != pair['after']['id']):
                raise ValueError('Invalid enchantment preview identity.')
            preview_ids.append(pair['before']['id'])
        if len(set(preview_ids)) != len(preview_ids) or enchanted and set(preview_ids) != set(result['selected_ids'] or []):
            raise ValueError('Invalid enchantment preview selection.')
    elif enchantment is not None or enchanted:
        raise ValueError('Unexpected enchantment preview.')
    if result["status"] != "visible":
        if (any(result[key] is not None for key in
                ("prompt", "min_select", "max_select", "selected_ids", "cards")) or result["options"] or preview is not None or previews or enchantment is not None or enchanted or transformations or bundles):
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
