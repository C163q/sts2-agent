from sts2_mcp.output.value_shapes import project, TIP, NUMBER
from sts2_mcp.output.contracts.cards import CARD_FULL as HAND_CARD


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
    return {**project(state, {key: NUMBER for key in ('energy', 'max_energy', 'stars')}), "hand": hand}
