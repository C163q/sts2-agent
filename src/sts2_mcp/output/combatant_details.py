from sts2_mcp.output.scene_context import scene_context
import re
from sts2_mcp.output.game_output import blade_refs, orb_slots, validate_identities


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


def validate_source(source, player, enemies, allies):
    blade = re.fullmatch(r'player\.sovereign_blades\.(0|[1-9][0-9]*)', source)
    if blade:
        items = player.get('sovereign_blades') if player is not None else None
        if items is None or int(blade[1]) >= len(items):
            raise ValueError('Missing public blade.')
        return
    ally = re.fullmatch(r'allies\.(0|[1-9][0-9]*)\.powers\.(0|[1-9][0-9]*)', source)
    if ally:
        if allies is None or int(ally[1]) >= len(allies):
            raise ValueError('Missing public ally.')
        items = allies[int(ally[1])]['powers']
        if items is None or int(ally[2]) >= len(items):
            raise ValueError('Missing allied power.')
        return
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
    context = scene_context(state)
    if not isinstance(state["enemies"], list):
        raise ValueError("Invalid combatant details.")
    player = None if state["player"] is None else {"powers": powers(state["player"]["powers"])}
    if player is not None and 'orb_slots' in state['player']:
        player['orb_slots'] = orb_slots(state['player']['orb_slots'])
    if player is not None and 'sovereign_blades' in state['player']:
        player['sovereign_blades'] = blade_refs(state['player']['sovereign_blades'])
    allies = None
    if state.get('allies') is not None:
        if not isinstance(state['allies'], list):
            raise ValueError('Invalid public allies.')
        allies = [{'id': item['id'], 'name': nullable_text(item['name']), 'powers': powers(item['powers'])}
                  for item in state['allies']]
        validate_identities(allies, 4294967295)
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
            validate_source(source, player, enemies, allies)
        tips.append({"title": title, "description": description, "sources": list(sources)})
    result = {**context, "player": player, "enemies": enemies, "hover_tips": tips}
    if 'allies' in state:
        result['allies'] = allies
    if 'unavailable_hover_sources' in state:
        unavailable = state['unavailable_hover_sources']
        if (not isinstance(unavailable, list) or any(not isinstance(source, str) for source in unavailable)
                or len(set(unavailable)) != len(unavailable)):
            raise ValueError('Invalid unavailable hover sources.')
        explained = {source for tip in tips for source in tip['sources']}
        for source in unavailable:
            validate_source(source, player, enemies, allies)
            if source in explained: raise ValueError('Conflicting hover availability.')
        result['unavailable_hover_sources'] = list(unavailable)
    return result
