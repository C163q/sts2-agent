from game_output import gameplay_fields


ENEMY_ATTACK_INTENT_NOTE = "Enemy attack intents already include current preview modifiers, including effects on you. Do not apply those modifiers again; the number is not guaranteed HP loss."
CARD_VALUE_NOTE = "Card values are contextual previews. Target-specific modifiers may apply only when aiming. Do not apply included modifiers again."


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


def player_result(response):
    if response["ok"]:
        result = gameplay_fields(response["state"])
        if "hand" in result and result["hand"] is not None:
            result["hand"], result["hover_tips"] = share_hand_tips(result["hand"])
        if "potion_slots" in result and result["potion_slots"] is not None:
            result["potion_slots"], result["hover_tips"] = share_potion_tips(result["potion_slots"])
        if "relics" in result and result["relics"] is not None:
            result["relics"], result["hover_tips"] = share_indexed_tips(result["relics"], "relic_indices")
        if "deck" in result and result.get("detail_level") == "full":
            result["deck"], result["hover_tips"] = share_hand_tips(result["deck"])
        if result.get("scene") == "card_pile" and result.get("detail_level") == "full" and result.get("cards") is not None:
            result["cards"], result["hover_tips"] = share_hand_tips(result["cards"])
        notes = {}
        if result.get("hand"):
            notes["card_values"] = CARD_VALUE_NOTE
        if result.get("scene") == "combat" and any(
            enemy.get("intents") for enemy in result.get("enemies") or []
        ):
            notes["enemy_attack_intents"] = ENEMY_ATTACK_INTENT_NOTE
        if notes:
            result["notes"] = notes
        return result
    code = response["error"]["code"]
    messages = {
        "stale_state": ("The observation is outdated. Read the current state before choosing an action.", "get_state"),
        "illegal_action": ("The requested action is unavailable. Read the current state and choose a legal action.", "get_state"),
        "invalid_request": ("The request arguments are invalid. Correct them before submitting again.", "correct_request"),
        "expired_request": ("The request expired before execution. Read the current state before choosing an action.", "get_state"),
        "timeout": ("The request timed out; execution outcome is unknown. Read the current state and do not retry the action automatically.", "get_state"),
        "game_error": ("The game could not complete the request; execution outcome is unknown. Read the current state and do not retry the action automatically.", "get_state"),
        "transport_error": ("The local game connection failed. Check the connection before reading the current state.", "check_connection"),
    }
    message, recovery = messages.get(code, (
        "The request failed; execution outcome is unknown. Read the current state and do not retry the action automatically.", "get_state"))
    error = {"code": code, "message": message, "recovery": recovery}
    if code not in {"stale_state", "illegal_action", "invalid_request", "expired_request"}:
        error["outcome"] = "unknown"
    return {"error": error}
