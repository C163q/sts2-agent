from mcp.types import Tool, ToolAnnotations
from sts2_mcp.output.observation_presets import OBSERVATION_SCHEMA
from sts2_mcp.output.hand_presets import HAND_SCHEMA
from sts2_mcp.output.selection_presets import SELECTION_SCHEMA
from sts2_mcp.output.relic_presets import RELIC_SCHEMA

from sts2_mcp.output.run_ending_details import OPTION_SCHEMA as RESULT_OPTION_SCHEMA
from sts2_mcp.output.map_details import MAP_SCHEMA, TRAVEL_SCHEMA
from sts2_mcp.output.deck_details import DECK_SCHEMA
from sts2_mcp.output.pile_details import PILE_SCHEMA
from sts2_mcp.output.selection_details import CARD_SCHEMA, OPTION_SCHEMA, VIEW_SCHEMA
from sts2_mcp.output.card_play_details import PLAY_SCHEMA, TARGET_SCHEMA
from sts2_mcp.output.potion_action_details import POTION_SCHEMA, USE_SCHEMA
from sts2_mcp.screenshot_tool import SCREENSHOT_SCHEMA
from sts2_mcp.output.reward_details import CLAIM_SCHEMA
from sts2_mcp.output.rest_site_details import REST_OPTION_SCHEMA
from sts2_mcp.output.treasure_details import LOOT_SCHEMA
from sts2_mcp.output.shop_details import BUY_SCHEMA
from sts2_mcp.output.ancient_details import ANCIENT_OPTION_SCHEMA
from sts2_mcp.output.event_details import EVENT_OPTION_SCHEMA
from sts2_mcp.output.confirmation_details import CONFIRMATION_SCHEMA
from sts2_mcp.output.divination_details import TOOL_SCHEMA, DIVINE_SCHEMA


SERVER_INSTRUCTIONS = (
    "Control a local Slay the Spire 2 game; output is English. "
    "Call tools sequentially and decide after each result. "
    "available_actions lists currently offered tool names; arguments and state are checked at call time. "
    "Use IDs from current observations or inspections. "
    "Action receipts contain context and events, not full state or state deltas. "
    "After draws, cost changes or turn changes, read current values with get_observation or inspections as needed. "
    "Handle card choices with selection tools; transition.complete can mean effects are paused for input. "
    "Successful observations, inspections and view changes refresh the state used to validate the next action; screenshots do not. "
    "No extra get_observation is needed when a result already provides the information needed to act. "
    "Close covering views before acting on the underlying screen. "
    "After errors, timeouts or incomplete transitions, check current state with get_observation or a relevant inspection before deciding; "
    "never automatically retry an action with unknown outcome."
)
NO_ARGUMENTS = {"type": "object", "properties": {}, "additionalProperties": False}


def tool_definitions(*, screenshots_enabled=False):
    read_only = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
    view = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
    action = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False)
    definitions = [
        Tool(name='inspect_run_result', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the current run result page, badge/discovery hover help and revealed unlock details. Does not advance pages.')),
        Tool(name='run_result_option', inputSchema=RESULT_OPTION_SCHEMA, annotations=action, description=(
            'Click one offered result button or unlock entry. Stops at the next page; only scene=main_menu confirms return to menu. '
            'Does not start a new run.')),
        Tool(name='travel_to_node', inputSchema=TRAVEL_SCHEMA, annotations=action, description=(
            'Travel to one currently selectable map node. Leaves the room and forfeits unclaimed rewards. '
            'Uses native routes and Winged Boots charges; stops at the next input boundary.')),
        Tool(name='respond_to_confirmation', inputSchema=CONFIRMATION_SCHEMA, annotations=action, description=(
            'Respond to the visible Trial event confirmation. Confirm abandons this run; cancel returns to the event. '
            'Other dialogs require manual input.')),
        Tool(name='set_divination_tool', inputSchema=TOOL_SCHEMA, annotations=view, description=(
            'Switch the divination reveal size without spending a reveal. Returns an action receipt and can continue under the action rules.')),
        Tool(name='divine', inputSchema=DIVINE_SCHEMA, annotations=action, description=(
            'Spend one reveal centered on a covered divination cell. Read the updated board image and grid with inspect_event '
            'or full get_observation; the action receipt omits them. May pause for rewards or choices.')),
        Tool(name='inspect_event', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read current event text, options and hover help, or the visible divination board and PNG image. '
            'Divination requires an image-capable client and model.')),
        Tool(name='choose_event_option', inputSchema=EVENT_OPTION_SCHEMA, annotations=action, description=(
            'Choose one enabled event option; lethal_warning marks the visible red warning. '
            'Handle subsequent card selections, rewards or combat separately.')),
        Tool(name='inspect_ancient', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the current ancient dialogue, displayed gift options and their hover help.')),
        Tool(name='choose_ancient_option', inputSchema=ANCIENT_OPTION_SCHEMA, annotations=action, description=(
            'Choose one enabled ancient gift option. Handle subsequent card selections or rewards separately.')),
        Tool(name='advance_dialogue', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Advance the current ancient or Architect dialogue once. Does not choose a gift or press the final Proceed.')),

        Tool(name='open_shop', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the exposed merchant to open the shop. Read items and prices with inspect_shop or get_observation.')),
        Tool(name='close_shop', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the open shop back button to return to the merchant. Does not proceed or travel.')),
        Tool(name='inspect_shop', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read all currently displayed shop items, card effects and hover help. Open the shop first.')),
        Tool(name='buy_item', inputSchema=BUY_SCHEMA, annotations=action, description=(
            'Buy one shop item; restocked goods have new IDs. Card removal opens a selection and canceling costs nothing. '
            'Full potion slots or gain restrictions can block purchase without spending gold. Check purchase_result for the outcome.')),

        Tool(name="get_observation", inputSchema=OBSERVATION_SCHEMA, annotations=read_only, description=(
            "Read an overview of the current visible screen. Includes available inspection/action names, excluding this tool and screenshots. "
            "Ordinary hand effects and hover help require dedicated inspections.")),
        Tool(name='inspect_rewards', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the current browsable reward rows and their hover help. Does not reveal unopened card reward candidates.')),
        Tool(name='claim_reward', inputSchema=CLAIM_SCHEMA, annotations=action, description=(
            'Claim one reward row. Card rewards open a selection. '
            'A full potion belt leaves the reward unclaimed; discard or use a potion separately if desired. '
            'Blocked potion gain can consume the reward without obtaining it (not_obtained).')),
        Tool(name='proceed', inputSchema=NO_ARGUMENTS, annotations=action, description=(
            'Click the enabled Skip/Proceed at rewards, treasure, rest sites, events, ancients, a closed shop or the Architect. '
            'May forfeit unclaimed rewards, open the map, resume an event, change act or finish the run.')),
        Tool(name='loot_treasure', inputSchema=LOOT_SCHEMA, annotations=action, description=(
            'Open a single-player chest and take its relic by default, or take the relic from an already opened chest. '
            'Does not proceed; handle subsequent rewards, choices or dialogs separately.')),
        Tool(name='inspect_treasure', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read the exposed treasure room and visible relic hover help. Closed chests reveal no contents.')),
        Tool(name='inspect_rest_site', inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            'Read visible rest-site options and their current hover descriptions, including disabled options.')),
        Tool(name='choose_rest_option', inputSchema=REST_OPTION_SCHEMA, annotations=action, description=(
            'Choose one enabled rest-site option. Some options take effect immediately; '
            'card choices use selection tools. Smith previews require confirmation; use offered cancel buttons to go back.')),
        Tool(name="inspect_hand", inputSchema=HAND_SCHEMA, annotations=read_only, description=(
            "Read current visible hand cards, optionally by card_ids. full includes descriptions and hover help; "
            "summary keeps identity, visible costs, enchantments and UI markers. Unavailable IDs are grouped in errors; valid cards remain. "
            "Markers do not guarantee a legal play.")),
        Tool(name="inspect_targets", inputSchema=TARGET_SCHEMA, annotations=read_only, description=(
            "Query exactly one hand card or potion for usability, requires_target and targeting range. "
            "Does not enter aiming or resolve randomness; targets do not predict every effect.")),
        Tool(name="play_card", inputSchema=PLAY_SCHEMA, annotations=action, description=(
            "Play one current hand card. Use inspect_targets when target requirements are unknown. "
            "Stops at choices; continue with selection tools.")),
        Tool(name="inspect_ui", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read hover help for visible combat UI, resources and empty orb slots. Use inspect_combatants for occupied orbs; "
            "use dedicated inspections for cards, potions and relics.")),
        Tool(name="inspect_potions", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible potion descriptions and hover help. potion_slots preserves belt positions, with null for empty slots.")),
        Tool(name="use_potion", inputSchema=USE_SCHEMA, annotations=action, description=(
            "Use one potion, in or out of combat when usable. Use inspect_targets when target requirements are unknown. "
            "Stops at choices; continue with selection tools.")),
        Tool(name="discard_potion", inputSchema=POTION_SCHEMA, annotations=action, description=(
            "Discard one potion through the native action. "
            "Allowed only when potions can be removed; automatic potions may be discarded.")),
        Tool(name="inspect_combatants", inputSchema=NO_ARGUMENTS, annotations=read_only, description=(
            "Read visible combatant powers, enemy intent explanations, occupied orb help and floating Sovereign Blade previews. "
            "Unavailable while aiming or playing a card.")),
        Tool(name="inspect_relics", inputSchema=RELIC_SCHEMA, annotations=read_only, description=(
            "Read visible, hoverable owned relics. Full descriptions and hover help by default; "
            "summary keeps basic fields. relic_indices filters by positions in the current unfiltered inspection.")),
        Tool(name="inspect_deck", inputSchema=DECK_SCHEMA, annotations=view, description=(
            "Open/reuse the native full-deck page during combat and read the entire browsable deck. "
            "Upgrade preview does not upgrade owned cards. Leaves the page open; close with close_card_view.")),
        Tool(name="inspect_pile", inputSchema=PILE_SCHEMA, annotations=view, description=(
            "Open/reuse a combat draw, discard or exhaust page, replacing another card page. "
            "Returns the entire pile in display order, never draw order. "
            "Leaves an opened page until close_card_view. Empty piles return cards=[]; unavailable entries return cards=null.")),
        Tool(name="close_card_view", inputSchema=NO_ARGUMENTS, annotations=view, description=(
            "Close the top deck/draw/discard/exhaust browsing page and return a basic observation. "
            "Preserves an underlying map; cannot close card selections or other screens.")),
        Tool(name="inspect_map", inputSchema=MAP_SCHEMA, annotations=view, description=(
            "Open/reuse the current-act map, replacing a covering card page. Leaves it open. "
            "Returns the full graph by default; preset and max_steps limit returned data only. "
            "Does not travel or reveal unknown encounters; close with close_map.")),
        Tool(name="close_map", inputSchema=NO_ARGUMENTS, annotations=view, description=(
            "Close the exposed map using its enabled native back button; return a basic observation. "
            "Cannot close through card pages or force a mandatory map closed.")),
        Tool(name="inspect_selection", inputSchema=SELECTION_SCHEMA, annotations=read_only, description=(
            "Read all browsable candidates, offered buttons and visible previews of the current card selection. "
            "Full card details by default; summary compacts every card, including bundles and previews. "
            "card_ids filters returned card details only; instructions and buttons remain. "
            "Unavailable while the selection is hidden; does not switch views.")),
        Tool(name="select_card", inputSchema=CARD_SCHEMA, annotations=action, description=(
            "Click one current selection candidate. Multi-select clicks toggle that card; "
            "single-choice screens may immediately submit. Use enabled selection.options to confirm when required. "
            "Hand upgrades preview before confirmation; click the selected card to deselect.")),
        Tool(name="selection_option", inputSchema=OPTION_SCHEMA, annotations=action, description=(
            "Click an offered selection button to confirm, cancel a preview, skip or choose a reward alternative. "
            "Choose card bundles with the offered bundle:N option.")),
        Tool(name="set_selection_view", inputSchema=VIEW_SCHEMA, annotations=view, description=(
            "Click the native eye to show battlefield or return to selection. "
            "Battlefield view permits available inspections, never normal combat actions. "
            "Close covering card/map views first.")),
        Tool(name="end_turn", inputSchema=NO_ARGUMENTS, annotations=action, description=(
            "End the player's turn once and wait for the next input boundary, turn or run end. "
            "May stop for a choice before the next turn; inspect and resolve that selection separately.")),
    ]
    if screenshots_enabled:
        definitions.append(Tool(name="capture_screenshot", inputSchema=SCREENSHOT_SCHEMA, annotations=view, description=(
            "Save the current game viewport as PNG in the configured directory; return its path and dimensions. "
            "Does not change the UI or prepare an action.")))
    return definitions
