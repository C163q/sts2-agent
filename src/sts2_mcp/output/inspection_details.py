from sts2_mcp.tool_registry import NATIVE_TOOLS, binding
from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.ui_details import ui_details
from sts2_mcp.output.deck_details import closed_card_view
from sts2_mcp.output.observation_details import observation_details


# File-only operations remain outside the public tool catalog.
READERS = {'start_test_combat': observation_details, 'close_deck': closed_card_view}


def _read_details(operation, state, arguments=None):
    if operation in READERS:
        return READERS[operation](state)
    read = binding(NATIVE_TOOLS[operation].reader)
    if operation == 'inspect_targets': return read(state, arguments)
    if operation == 'inspect_pile': return read(state, arguments['pile'])
    return read(state)


def inspection_details(operation, state, arguments=None):
    result = _read_details(operation, state, arguments)
    if "scene" in result:
        result.update(scene_context(state))
    if "selection_view" in state:
        if state["selection_view"] not in {"visible", "battlefield", "covered", "unsupported"}:
            raise ValueError("Invalid pending selection view.")
        result["selection_view"] = state["selection_view"]
    return result
