from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.deck_details import browsed_cards
from sts2_mcp.output.pile_presets import PILES


def pile_details(state, pile):
    context = scene_context(state)
    status = state["status"]
    screen = state["screen"]
    if (state["pile"] != pile
            or status not in ("opened", "empty", "unavailable") or not isinstance(screen, dict)
            or not isinstance(screen["status"], str) or not isinstance(state["message"], str)):
        raise ValueError("Invalid pile details.")
    view = {"status": screen["status"]}
    if "view" in screen:
        if not isinstance(screen["view"], str):
            raise ValueError("Invalid pile screen view.")
        view["view"] = screen["view"]
    result = {**context, "pile": pile, "status": status,
              "screen": view, "message": state["message"]}
    if status == "unavailable":
        if state["cards"] is not None or state["reason"] not in ("entry_not_visible", "entry_disabled"):
            raise ValueError("Invalid unavailable pile.")
        result.update(cards=None, reason=state["reason"])
    else:
        if status == "opened":
            if view != {"status": "covered", "view": pile + "_pile"} or not state["cards"]:
                raise ValueError("Invalid opened pile screen.")
        elif state["cards"] != [] or view != {"status": "visible"}:
            raise ValueError("Invalid empty pile.")
        result["cards"] = browsed_cards(state["cards"], "pile")
    return result


def pile_observation(state):
    values = ('pile', 'cards', 'message')
    if not any(key in state for key in values):
        return {}
    if (not all(key in state for key in values) or state['pile'] not in PILES
            or state['scene'] != 'combat' or not isinstance(state['message'], str)
            or state['screen'] != {'status': 'covered', 'view': state['pile'] + '_pile'}):
        raise ValueError('Invalid observed pile page.')
    return {'pile': state['pile'], 'cards': browsed_cards(state['cards'], 'pile', full=False),
            'message': state['message']}
