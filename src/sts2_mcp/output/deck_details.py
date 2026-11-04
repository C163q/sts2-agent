from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.deck_presets import SORT_KEYS
import re


def deck_details(state):
    context = scene_context(state)
    sort = state["sort"]
    if (context["screen"].get("view") != "deck"
            or type(state["view_upgrades"]) is not bool or not isinstance(sort, dict)
            or sort["by"] not in SORT_KEYS or type(sort["descending"]) is not bool
            or not isinstance(state["deck"], list)):
        raise ValueError("Invalid deck details.")
    return {**context, "view_upgrades": state["view_upgrades"],
            "sort": {"by": sort["by"], "descending": sort["descending"]},
            "deck": browsed_cards(state["deck"], "deck")}


def browsed_cards(items, prefix, *, full=True):
    from sts2_mcp.output.card_format import BROWSED_CARD, format_card
    from sts2_mcp.output.value_shapes import project
    cards = project(items, [BROWSED_CARD])
    ids = set()
    for card in cards:
        required = {"id", "name", "type", "rarity", "visual_card_pool", "energy_cost", "star_cost"}
        if full: required |= {'description', 'hover_tips'}
        if (not required <= card.keys()
                or not re.fullmatch(prefix + r":(0|[1-9][0-9]*)", card['id']) or card['id'] in ids):
            raise ValueError("Invalid browse card identity or details.")
        ids.add(card['id'])
        if any(not isinstance(card[key], str) for key in ('name', 'type', 'rarity', 'visual_card_pool')) \
                or full and (not isinstance(card['description'], str) or not isinstance(card['hover_tips'], list)
                    or any(set(tip) != {'title', 'description'} for tip in card['hover_tips'])):
            raise ValueError('Invalid browse card text or hover help.')
    return [format_card(card, 'full' if full else 'face_full') for card in cards]


def deck_observation(state):
    values = ('deck', 'view_upgrades', 'sort')
    if not any(key in state for key in values):
        return {}
    if (state['screen'].get('view') != 'deck' or not all(key in state for key in values)
            or type(state['view_upgrades']) is not bool or not isinstance(state['sort'], dict)
            or state['sort'].get('by') not in SORT_KEYS or type(state['sort'].get('descending')) is not bool):
        raise ValueError('Invalid observed deck page.')
    return {'deck': browsed_cards(state['deck'], 'deck', full=False),
            'view_upgrades': state['view_upgrades'],
            'sort': {'by': state['sort']['by'], 'descending': state['sort']['descending']}}
