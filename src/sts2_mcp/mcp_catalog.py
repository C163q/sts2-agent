from mcp.types import Tool, ToolAnnotations
from sts2_mcp.tool_registry import SPECS, NO_ARGUMENTS


SERVER_INSTRUCTIONS = (
    "Control a local Slay the Spire 2 game; output is English. "
    "Output preset defaults to default: full content with ordinary null object fields omitted. "
    "Array positions, event nulls and card comparison sides remain. "
    "Relic grayed_out/pulsing false flags are also omitted in default/summary; other omissions never mean zero, false, empty or unchanged. "
    "Use full to preserve all existing nulls; other named presets retain their own behavior. "
    "Call tools sequentially and decide after each result. "
    "A page body status of not_ready means its display is still updating; visible does not mean all buttons are enabled. "
    "available_actions lists currently offered tool names; arguments and state are checked at call time. "
    "Use IDs from current observations or inspections. "
    "Action receipts contain context and events, not full state or state deltas. "
    "After draws, cost changes or turn changes, read current values with get_observation or inspections as needed. "
    "Handle card choices with selection tools; transition.complete can mean effects are paused for input. "
    "Successful observations, inspections and view changes refresh the state used to validate the next action; screenshots do not. "
    "No extra get_observation is needed when a result already provides the information needed to act. "
    "Close covering views before acting on the underlying screen. "
    "Follow error.recovery; choose_legal_action permits deciding from existing information, with inspections as needed. "
    "After stale observations, timeouts, incomplete transitions or unknown card results, check current state before deciding; "
    "never automatically retry an action with unknown outcome."
)


def tool_definitions(*, screenshots_enabled=False):
    return [Tool(name=spec.name, description=spec.description, inputSchema=spec.input_schema,
                 annotations=ToolAnnotations(**spec.annotations)) for spec in SPECS
            if screenshots_enabled or spec.category != 'screenshot']
