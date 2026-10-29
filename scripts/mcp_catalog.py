from mcp.types import Tool, ToolAnnotations

from deck_details import DECK_SCHEMA
from pile_details import PILE_SCHEMA
from selection_details import CARD_SCHEMA, OPTION_SCHEMA, VIEW_SCHEMA


SERVER_INSTRUCTIONS = (
    "Control a local Slay the Spire 2 game; output is English. "
    "Call get_observation before each gameplay action; its permission is consumed even on failure. "
    "Read-only inspections do not prepare actions. View tools change UI and clear action permission; "
    "return to the action's screen and observe again before acting. Actions return a resulting observation. "
    "After failure or timeout, observe before deciding; never automatically retry an action with unknown outcome."
)
NO_ARGUMENTS = {"type": "object", "properties": {}, "additionalProperties": False}


def tool_definitions():
    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    view = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    action = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
    return [
        Tool(name="get_observation", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read the current visible game state and prepare one action. Card effects and hover help require inspections.")),
        Tool(name="inspect_hand", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read all visible hand cards' descriptions; shared hover_tips link to card_ids.")),
        Tool(name="inspect_ui", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible combat UI and resource hover help, linked by sources. "
            "Cards, potions, relics and combatants have dedicated inspections.")),
        Tool(name="inspect_potions", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible potion descriptions: one slot_tip, positional potion_slots (null for empty slots), "
            "and shared hover_tips linked by zero-based slot_indices.")),
        Tool(name="inspect_combatants", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read both sides' visible powers and current enemy intent hover help; shared hover_tips use sources paths. "
            "Unavailable while aiming or playing a card.")),
        Tool(name="inspect_relics", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible, hoverable combat relics' descriptions and displayed counters; "
            "shared hover_tips link to zero-based relic_indices.")),
        Tool(name="inspect_deck", inputSchema=DECK_SCHEMA, annotations=view, description=(
            "Open/reuse the native deck page and read the entire browsable deck. "
            "Upgrade preview does not upgrade owned cards. Leaves the page open; close with close_card_view.")),
        Tool(name="inspect_pile", inputSchema=PILE_SCHEMA, annotations=view, description=(
            "Open/reuse a combat draw, discard or exhaust page, replacing another card page. "
            "Returns the entire pile in display order, never draw order. "
            "Status is opened, empty (native click feedback), or unavailable (cards null). "
            "Leaves an opened page until close_card_view; full details include shared hover_tips linked by card_ids.")),
        Tool(name="close_card_view", inputSchema=NO_ARGUMENTS, annotations=view, description=(
            "Close the top deck/draw/discard/exhaust browsing page and return a basic observation. "
            "Preserves an underlying map; cannot close card selections or other screens.")),
        Tool(name="inspect_map", inputSchema=NO_ARGUMENTS, annotations=view, description=(
            "Open/reuse the entire current-act map, replacing a covering card page. Leaves it open. "
            "Returns nodes, next connections and visited_path; selectable_nodes lists all currently legal travel choices. "
            "Does not travel or reveal unknown encounters.")),
        Tool(name="close_map", inputSchema=NO_ARGUMENTS, annotations=view, description=(
            "Close the exposed map using its enabled native back button; return a basic observation. "
            "Cannot close through card pages or force a mandatory map closed.")),
        Tool(name="inspect_selection", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read the current selection's entire browsable candidate list and card details. "
            "Unavailable while the selection is hidden; does not switch views.")),
        Tool(name="select_card", inputSchema=CARD_SCHEMA, annotations=action, description=(
            "Click one candidate by its observed card_id. Multi-select clicks toggle that card; "
            "single-choice screens may immediately submit. Use enabled selection.options to confirm when required. "
            "Requires a fresh get_observation.")),
        Tool(name="selection_option", inputSchema=OPTION_SCHEMA, annotations=action, description=(
            "Click an enabled selection.options button by option_id: confirm, cancel preview, skip or a reward alternative. "
            "Only offered buttons are legal; requires a fresh get_observation.")),
        Tool(name="set_selection_view", inputSchema=VIEW_SCHEMA, annotations=view, description=(
            "Click the native eye to show battlefield or return to selection. "
            "Battlefield view permits available inspections, never normal combat actions. "
            "Close covering card/map views first. Clears action permission.")),
        Tool(name="end_turn", inputSchema=NO_ARGUMENTS, annotations=action, description=(
            "End the player's turn once; return observed events, a stop reason, and the resulting observation. "
            "Stops for player choices; inspect selection and choose separately. "
            "Requires a fresh get_observation. Never retry an incomplete transition automatically.")),
    ]
