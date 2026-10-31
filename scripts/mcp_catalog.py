from mcp.types import Tool, ToolAnnotations

from deck_details import DECK_SCHEMA
from pile_details import PILE_SCHEMA
from selection_details import CARD_SCHEMA, OPTION_SCHEMA, VIEW_SCHEMA
from card_play_details import PLAY_SCHEMA, TARGET_SCHEMA
from potion_action_details import POTION_SCHEMA, USE_SCHEMA
from screenshot_tool import SCREENSHOT_SCHEMA
from reward_details import CLAIM_SCHEMA
from rest_site_details import REST_OPTION_SCHEMA
from treasure_details import LOOT_SCHEMA
from shop_details import BUY_SCHEMA
from ancient_details import ANCIENT_OPTION_SCHEMA
from event_details import EVENT_OPTION_SCHEMA
from divination_details import TOOL_SCHEMA, DIVINE_SCHEMA


SERVER_INSTRUCTIONS = (
    "Control a local Slay the Spire 2 game; output is English. "
    "Start with get_observation. Continue sequentially from a successful action result only if transition.complete is true, "
    "available_actions is nonempty, and the action screen or a supported selection is visible. "
    "Read-only inspections do not prepare actions. View tools change UI and clear action permission; "
    "return to the action's screen and observe again before acting. "
    "transition.complete confirms the stated boundary, not that choice-paused effects or cosmetic animations have finished. "
    "After failure or timeout, observe before deciding; never automatically retry an action with unknown outcome."
)
NO_ARGUMENTS = {"type": "object", "properties": {}, "additionalProperties": False}


def tool_definitions(*, screenshots_enabled=False):
    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    view = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    action = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
    definitions = [
        Tool(name='set_divination_tool', inputSchema=TOOL_SCHEMA, annotations=view, description=(
            'Select the visible big (3x3) or small (one cell) divination tool without spending a reveal.')),
        Tool(name='divine', inputSchema=DIVINE_SCHEMA, annotations=action, description=(
            'Spend one reveal on a covered divination cell at zero-based x,y (right,down). '
            'Use the attached board image and grid; stops at rewards or the enabled Proceed.')),
        Tool(name='inspect_event', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the exposed event and hover help, or the current divination board with its image. Does not reveal hidden outcomes.')),
        Tool(name='choose_event_option', inputSchema=EVENT_OPTION_SCHEMA, annotations=action, description=(
            'Click one enabled event option by observed option_id; lethal_warning marks the visible red warning. '
            'Handle subsequent card selections, rewards or combat separately.')),
        Tool(name='inspect_ancient', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the exposed ancient, visible dialogue, options and their hover help. Never reveals future dialogue or hidden choices.')),
        Tool(name='choose_ancient_option', inputSchema=ANCIENT_OPTION_SCHEMA, annotations=action, description=(
            'Click one enabled ancient option by observed option_id. Stops at card selections or rewards; handle those separately.')),
        Tool(name='advance_dialogue', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the ancient dialogue continue area once to show the next line. Does not choose a gift or proceed.')),

        Tool(name='open_shop', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the exposed merchant to open the shop. Returns card summaries and visible prices.')),
        Tool(name='close_shop', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the open shop back button to return to the merchant. Does not proceed or travel.')),
        Tool(name='inspect_shop', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read all currently displayed shop items, card effects and hover help. Open the shop first.')),
        Tool(name='buy_item', inputSchema=BUY_SCHEMA, annotations=action, description=(
            'Buy one observed shop item by item_id. Restocked goods have new IDs. '
            'Card removal opens selection tools; canceling costs nothing. Full slots or potion-gain restrictions can prevent purchase without spending gold. '
            'Stops at choices or rewards; never buys additional items automatically.')),

        Tool(name="get_observation", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read the current visible game state and refresh the action observation. Card effects and hover help require inspections.")),
        Tool(name='inspect_rewards', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the current browsable reward rows and their hover help. Does not reveal unopened card reward candidates.')),
        Tool(name='claim_reward', inputSchema=CLAIM_SCHEMA, annotations=action, description=(
            'Click one observed reward row by reward_id; choose the order yourself. Card rewards open selection tools. '
            'A full potion belt leaves the reward unclaimed; discard or use a potion separately if desired. '
            'Blocked potion gain can consume the reward without obtaining it (not_obtained).')),
        Tool(name='proceed', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the visible rewards/treasure Skip/Proceed, rest-site, event, ancient or closed-shop Proceed button. '
            'Uses the native flow, which may open the map, resume an event, change act or finish the run.')),
        Tool(name='loot_treasure', inputSchema=LOOT_SCHEMA, annotations=action, description=(
            'Open a single-player treasure chest and take its relic; never proceeds. '
            'Set open_only=true to reveal it first. On an opened chest, omit open_only to take the visible relic. '
            'Stops at extra rewards, card choices or dialogs; handle those separately.')),
        Tool(name='inspect_treasure', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the exposed treasure room and visible relic hover help. Closed chests reveal no contents.')),
        Tool(name='inspect_rest_site', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read visible rest-site options and their current hover descriptions, including disabled options.')),
        Tool(name='choose_rest_option', inputSchema=REST_OPTION_SCHEMA, annotations=action, description=(
            'Click one enabled rest-site option by its observed option_id. Some options take effect immediately; '
            'card choices use selection tools. Smith previews require confirmation; use offered cancel buttons to go back.')),
        Tool(name="inspect_hand", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read all visible hand cards' descriptions; shared hover_tips link to card_ids.")),
        Tool(name="inspect_targets", inputSchema=TARGET_SCHEMA, annotations=read_only, description=(
            "Query one visible hand card (card_id) or potion (zero-based potion_slot): usability, requires_target and targeting range. "
            "No aiming or random resolution; the range does not predict every effect.")),
        Tool(name="play_card", inputSchema=PLAY_SCHEMA, annotations=action, description=(
            "Play one observed hand card. Supply a combatant target_id only when requires_target is true, even for one candidate. "
            "Return events and stop at choices; use selection tools to continue.")),
        Tool(name="inspect_ui", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible combat UI and resource hover help, linked by sources. "
            "Cards, potions, relics and combatants have dedicated inspections.")),
        Tool(name="inspect_potions", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible potion descriptions: one slot_tip, positional potion_slots (null for empty slots), "
            "and shared hover_tips linked by zero-based slot_indices.")),
        Tool(name="use_potion", inputSchema=USE_SCHEMA, annotations=action, description=(
            "Use one observed zero-based potion_slot, in or out of combat when usable. "
            "Supply target_id only when inspect_targets requires it; stop at choices and continue with selection tools.")),
        Tool(name="discard_potion", inputSchema=POTION_SCHEMA, annotations=action, description=(
            "Discard one observed zero-based potion_slot through the native action. "
            "Allowed only when potions can be removed; automatic potions may be discarded.")),
        Tool(name="inspect_combatants", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read both sides' visible powers and current enemy intent hover help; shared hover_tips use sources paths. "
            "Unavailable while aiming or playing a card.")),
        Tool(name="inspect_relics", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible, hoverable owned relics in combat, an exposed ancient or shop: descriptions and displayed counters; "
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
            "Hand upgrades preview before confirmation; click the selected card to deselect. "
            "Use the latest observation or complete action result.")),
        Tool(name="selection_option", inputSchema=OPTION_SCHEMA, annotations=action, description=(
            "Click an enabled selection.options button by option_id: confirm, cancel preview, skip or a reward alternative. Choose card bundles with the offered bundle:N option. "
            "Only offered buttons in the latest observation or complete action result are legal.")),
        Tool(name="set_selection_view", inputSchema=VIEW_SCHEMA, annotations=view, description=(
            "Click the native eye to show battlefield or return to selection. "
            "Battlefield view permits available inspections, never normal combat actions. "
            "Close covering card/map views first. Clears action permission.")),
        Tool(name="end_turn", inputSchema=NO_ARGUMENTS, annotations=action, description=(
            "End the player's turn once; return observed events, a stop reason, and the resulting observation. "
            "Stops for player choices; inspect selection and choose separately. "
            "Use the latest observation or complete action result. Never retry an incomplete transition automatically.")),
    ]
    if screenshots_enabled:
        definitions.append(Tool(name="capture_screenshot", inputSchema=SCREENSHOT_SCHEMA, annotations=view, description=(
            "Save the current game viewport as PNG in the configured directory; return its path and dimensions. "
            "Does not change the UI or prepare an action.")))
    return definitions
