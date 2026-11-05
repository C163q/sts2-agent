from sts2_mcp.tool_registry import NATIVE_TOOLS, binding
from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.ui_details import ui_details
from sts2_mcp.output.view_details import legacy_view_observation
from sts2_mcp.output.observation_details import observation_details


# File-only operations remain outside the public tool catalog.
READERS = {'start_test_combat': observation_details, 'close_deck': legacy_view_observation}


def _read_details(operation, state, arguments=None):
    if operation in READERS:
        return READERS[operation](state)
    spec = NATIVE_TOOLS[operation]
    read = binding(spec.reader)
    if spec.reader_argument == 'request': return read(state, arguments)
    if spec.reader_argument is not None: return read(state, arguments[spec.reader_argument])
    return read(state)


def inspection_details(operation, state, arguments=None):
    result = _read_details(operation, state, arguments)
    if "scene" in result or state.get("schema_version") in (35, 36, 37, 38, 39, 40, 41):
        result.update(scene_context(state))
    if "selection_view" in state:
        if state["selection_view"] not in {"visible", "battlefield", "covered", "unsupported"}:
            raise ValueError("Invalid pending selection view.")
        result["selection_view"] = state["selection_view"]
    return result
