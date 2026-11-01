import re
from game_output import orb_slots


def nullable_text(value):
    if value is not None and not isinstance(value, str):
        raise ValueError("Invalid combatant text.")
    return value


def powers(items):
    if items is None:
        return None
    if not isinstance(items, list):
        raise ValueError("Invalid powers.")
    result = []
    for item in items:
        amount = item["amount"]
        if amount is not None and type(amount) is not int:
            raise ValueError("Invalid power amount.")
        result.append({"name": nullable_text(item["name"]), "amount": amount})
    return result


def intents(items):
    if items is None:
        return None
    if not isinstance(items, list):
        raise ValueError("Invalid intents.")
    return [{"category": nullable_text(item["category"]), "value": nullable_text(item["value"])} for item in items]


def validate_source(source, player, enemies):
    orb = re.fullmatch(r'player\.orb_slots\.(0|[1-9][0-9]*)', source)
    if orb:
        slots = player.get('orb_slots') if player is not None else None
        if slots is None or int(orb[1]) >= len(slots) or slots[int(orb[1])] is None:
            raise ValueError('Missing occupied public orb slot.')
        return
    match = re.fullmatch(r"(player\.powers|enemies\.(0|[1-9][0-9]*)\.(powers|intents))\.(0|[1-9][0-9]*)", source)
    if match is None:
        raise ValueError("Invalid combatant source.")
    if match[1] == "player.powers":
        items = player["powers"] if player is not None else None
    else:
        index = int(match[2])
        if index >= len(enemies):
            raise ValueError("Missing combatant source.")
        items = enemies[index][match[3]]
    if items is None or int(match[4]) >= len(items):
        raise ValueError("Missing combatant source item.")


def combatant_details(state):
    if state["scene"] != "combat" or not isinstance(state["enemies"], list):
        raise ValueError("Invalid combatant details.")
    player = None if state["player"] is None else {"powers": powers(state["player"]["powers"])}
    if player is not None and 'orb_slots' in state['player']:
        player['orb_slots'] = orb_slots(state['player']['orb_slots'])
    enemies = []
    for enemy in state["enemies"]:
        identity = enemy["id"]
        if identity is not None and (type(identity) is not int or not 0 <= identity <= 4294967295):
            raise ValueError("Invalid combatant identity.")
        enemies.append({"id": identity, "name": nullable_text(enemy["name"]),
                        "powers": powers(enemy["powers"]), "intents": intents(enemy["intents"])})
    if not isinstance(state["hover_tips"], list):
        raise ValueError("Invalid combatant hover tips.")
    tips = []
    seen = set()
    for tip in state["hover_tips"]:
        title, description, sources = nullable_text(tip["title"]), tip["description"], tip["sources"]
        if (not isinstance(description, str) or not isinstance(sources, list) or not sources
                or any(not isinstance(source, str) for source in sources)):
            raise ValueError("Invalid combatant hover tip.")
        if (title, description) in seen or len(set(sources)) != len(sources):
            raise ValueError("Duplicate combatant hover tip or source.")
        seen.add((title, description))
        for source in sources:
            validate_source(source, player, enemies)
        tips.append({"title": title, "description": description, "sources": list(sources)})
    return {"scene": "combat", "player": player, "enemies": enemies, "hover_tips": tips}
