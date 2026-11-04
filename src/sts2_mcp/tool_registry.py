"""Single tool registry; explicit lazy bindings keep metadata independent of assembly."""
from dataclasses import dataclass
from copy import deepcopy
from importlib import import_module

from sts2_mcp.output.ui_presets import UI_SCHEMA
from sts2_mcp.output.observation_presets import OBSERVATION_SCHEMA
from sts2_mcp.output.hand_presets import HAND_SCHEMA
from sts2_mcp.output.selection_presets import SELECTION_SCHEMA
from sts2_mcp.output.relic_presets import RELIC_SCHEMA
from sts2_mcp.output.potion_presets import POTION_SCHEMA as POTION_INSPECTION_SCHEMA
from sts2_mcp.output.combatant_presets import COMBATANT_SCHEMA
from sts2_mcp.output.run_ending_details import OPTION_SCHEMA as RESULT_OPTION_SCHEMA
from sts2_mcp.output.map_details import MAP_SCHEMA, TRAVEL_SCHEMA
from sts2_mcp.output.deck_presets import DECK_SCHEMA
from sts2_mcp.output.pile_presets import PILE_SCHEMA
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

NO_ARGUMENTS = {"type": "object", "properties": {}, "additionalProperties": False}
read_only = {'readOnlyHint': True, 'openWorldHint': False}
view = {'readOnlyHint': False, 'destructiveHint': False, 'idempotentHint': False, 'openWorldHint': False}
action = {'readOnlyHint': False, 'destructiveHint': True, 'idempotentHint': False, 'openWorldHint': False}


def binding(path):
    module, member = path.split(':')
    package = 'sts2_mcp.' if module == 'screenshot_tool' else 'sts2_mcp.output.'
    return getattr(import_module(package + module), member)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    schema: dict
    description: str
    annotations: dict
    category: str
    effect: str
    requires_permission: bool
    returns_transition: bool
    records_events: bool
    operation: str = ''
    reader: str | None = None
    parser: str | None = None
    parser_operation: bool = False
    projector: str | None = None
    native_keys: tuple | None = None
    native_renames: tuple = ()
    reader_argument: str | None = None
    changes_view_with_arguments: bool = False
    refreshes_permission: bool = True
    media: bool = False
    unsubmitted_rejection_unchanged: bool = False
    unchanged_view_rejections: bool = False

    def effect_for(self, native_arguments):
        return 'view' if self.changes_view_with_arguments and native_arguments else self.effect

    @property
    def native_operation(self):
        return self.operation or self.name

    @property
    def presets(self):
        if self.category == 'screenshot': return ()
        return ('default', *self.schema['properties'].get('preset', {}).get('enum', ['full']))

    @property
    def input_schema(self):
        result = deepcopy(self.schema)
        if self.category != 'screenshot':
            previous = result['properties'].get('preset', {})
            result['properties']['preset'] = {
                **previous, 'type': 'string', 'enum': list(self.presets), 'default': 'default',
                'description': 'default omits ordinary null fields; full preserves nulls. ' + previous.get('description', '')}
            for key in ('oneOf', 'anyOf', 'allOf'):
                if key in result:
                    result[key] = [{**branch, 'properties': {**branch.get('properties', {}),
                                   'preset': result['properties']['preset']}} for branch in result[key]]
        return result


SPECS = (
    ToolSpec(
        name='inspect_run_result',
        schema=NO_ARGUMENTS,
        description='Read the current run result page, badge/discovery hover help and revealed unlock details. Does not advance pages.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='run_ending_details:inspect_result_details'),
    ToolSpec(
        name='run_result_option',
        schema=RESULT_OPTION_SCHEMA,
        description='Click one offered result button or unlock entry. Stops at the next page; only scene=main_menu confirms return to menu. '
            'Does not start a new run.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='run_ending_details:option_arguments',
        parser_operation=False),
    ToolSpec(
        name='travel_to_node',
        schema=TRAVEL_SCHEMA,
        description='Travel to one currently selectable map node. Leaves the room and forfeits unclaimed rewards. '
            'Uses native routes and Winged Boots charges; stops at the next input boundary.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='map_details:travel_arguments',
        parser_operation=False),
    ToolSpec(
        name='respond_to_confirmation',
        schema=CONFIRMATION_SCHEMA,
        description='Respond to the visible Trial event confirmation. Confirm abandons this run; cancel returns to the event. '
            'Other dialogs require manual input.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='confirmation_details:confirmation_arguments',
        parser_operation=False),
    ToolSpec(
        name='set_divination_tool',
        schema=TOOL_SCHEMA,
        description='Switch the divination reveal size without spending a reveal. Returns an action receipt and can continue under the action rules.',
        annotations=view,
        category='action',
        effect='view',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='divination_details:divination_arguments',
        parser_operation=True),
    ToolSpec(
        name='divine',
        schema=DIVINE_SCHEMA,
        description='Spend one reveal centered on a covered divination cell. Read the updated board image and grid with inspect_event '
            'or full get_observation; the action receipt omits them. May pause for rewards or choices.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='divination_details:divination_arguments',
        parser_operation=True),
    ToolSpec(
        name='inspect_event',
        schema=NO_ARGUMENTS,
        description='Read current event text, options and hover help, or the visible divination board and PNG image. '
            'Divination requires an image-capable client and model.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='event_details:inspect_event_details',
        media=True),
    ToolSpec(
        name='choose_event_option',
        schema=EVENT_OPTION_SCHEMA,
        description='Choose one enabled event option; lethal_warning marks the visible red warning. '
            'Handle subsequent card selections, rewards or combat separately.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='event_details:event_arguments',
        parser_operation=True),
    ToolSpec(
        name='inspect_ancient',
        schema=NO_ARGUMENTS,
        description='Read the current ancient dialogue, displayed gift options and their hover help.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='ancient_details:inspect_ancient_details'),
    ToolSpec(
        name='choose_ancient_option',
        schema=ANCIENT_OPTION_SCHEMA,
        description='Choose one enabled ancient gift option. Handle subsequent card selections or rewards separately.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='ancient_details:ancient_arguments',
        parser_operation=True),
    ToolSpec(
        name='advance_dialogue',
        schema=NO_ARGUMENTS,
        description='Advance the current ancient or Architect dialogue once. Does not choose a gift or press the final Proceed.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='ancient_details:ancient_arguments',
        parser_operation=True),
    ToolSpec(
        name='open_shop',
        schema=NO_ARGUMENTS,
        description='Click the exposed merchant to open the shop. Read items and prices with inspect_shop or get_observation.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='shop_details:shop_arguments',
        parser_operation=True),
    ToolSpec(
        name='close_shop',
        schema=NO_ARGUMENTS,
        description='Click the open shop back button to return to the merchant. Does not proceed or travel.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='shop_details:shop_arguments',
        parser_operation=True),
    ToolSpec(
        name='inspect_shop',
        schema=NO_ARGUMENTS,
        description='Read all currently displayed shop items, card effects and hover help. Open the shop first.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='shop_details:inspect_shop_details'),
    ToolSpec(
        name='buy_item',
        schema=BUY_SCHEMA,
        description='Buy one shop item; restocked goods have new IDs. Card removal opens a selection and canceling costs nothing. '
            'Full potion slots or gain restrictions can block purchase without spending gold. Check purchase_result for the outcome.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='action_details:purchase_details',
        parser='shop_details:shop_arguments',
        parser_operation=True),
    ToolSpec(
        name='get_observation',
        schema=OBSERVATION_SCHEMA,
        description="Read an overview of the current visible screen. Includes available inspection/action names, excluding this tool and screenshots. "
            "Exposed selections include all browsable candidates. summary compacts top bars, combat, and selection cards; top_bar adds top-bar values without relic details. "
            "Use inspect_relics for relic details. Ordinary hand effects and hover help require dedicated inspections.",
        annotations=read_only,
        category='observation',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        operation='get_state',
        reader='observation_details:observation_details',
        projector='observation_presets:observation_preset',
        native_keys=(),
        media=True),
    ToolSpec(
        name='inspect_rewards',
        schema=NO_ARGUMENTS,
        description='Read the current browsable reward rows and their hover help. Does not reveal unopened card reward candidates.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='reward_details:inspect_rewards_details'),
    ToolSpec(
        name='claim_reward',
        schema=CLAIM_SCHEMA,
        description='Claim one reward row. Card rewards open a selection. '
            'A full potion belt leaves the reward unclaimed; discard or use a potion separately if desired. '
            'Blocked potion gain can consume the reward without obtaining it (not_obtained).',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='action_details:claim_reward_details',
        parser='reward_details:reward_arguments',
        parser_operation=True),
    ToolSpec(
        name='proceed',
        schema=NO_ARGUMENTS,
        description='Click the enabled Skip/Proceed at rewards, treasure, rest sites, events, ancients, a closed shop or the Architect. '
            'May forfeit unclaimed rewards, open the map, resume an event, change act or finish the run.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='reward_details:reward_arguments',
        parser_operation=True),
    ToolSpec(
        name='loot_treasure',
        schema=LOOT_SCHEMA,
        description='Open a single-player chest and take its relic by default, or take the relic from an already opened chest. '
            'Does not proceed; handle subsequent rewards, choices or dialogs separately.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='treasure_details:loot_arguments',
        parser_operation=False),
    ToolSpec(
        name='inspect_treasure',
        schema=NO_ARGUMENTS,
        description='Read the exposed treasure room and visible relic hover help. Closed chests reveal no contents.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='treasure_details:inspect_treasure_details'),
    ToolSpec(
        name='inspect_rest_site',
        schema=NO_ARGUMENTS,
        description='Read visible rest-site options and their current hover descriptions, including disabled options.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='rest_site_details:inspect_rest_site_details'),
    ToolSpec(
        name='choose_rest_option',
        schema=REST_OPTION_SCHEMA,
        description='Choose one enabled rest-site option. Some options take effect immediately; '
            'card choices use selection tools. Smith previews require confirmation; use offered cancel buttons to go back.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='rest_site_details:rest_option_arguments',
        parser_operation=False),
    ToolSpec(
        name='inspect_hand',
        schema=HAND_SCHEMA,
        description="Read current visible hand cards and HUD energy/stars, optionally filtering cards by card_ids. full includes effects and hover help; "
            "summary keeps identity, visible costs, enchantments, afflictions and UI markers. Unavailable IDs are grouped in errors; valid cards remain. "
            "Markers do not guarantee a legal play.",
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='hand_details:hand_details',
        parser='hand_presets:hand_arguments',
        parser_operation=False,
        projector='hand_presets:hand_preset',
        native_keys=()),
    ToolSpec(
        name='inspect_targets',
        schema=TARGET_SCHEMA,
        description="Query exactly one hand card or potion for usability, requires_target and targeting range. "
            "Does not enter aiming or resolve randomness; targets do not predict every effect.",
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='card_play_details:target_details',
        parser='card_play_details:card_play_arguments',
        parser_operation=True,
        reader_argument='request'),
    ToolSpec(
        name='play_card',
        schema=PLAY_SCHEMA,
        description="Play one current hand card. Use inspect_targets when target requirements are unknown. "
            "Stops at choices; continue with selection tools.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='card_play_details:card_play_arguments',
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='inspect_ui',
        schema=UI_SCHEMA,
        description="Read help for exposed top-bar and combat UI. summary lists titles and sources; sources selects descriptions. Use inspect_combatants for occupied orbs; "
            "use dedicated inspections for cards, potions and relics.",
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='ui_details:ui_details',
        parser='ui_presets:ui_arguments',
        parser_operation=False,
        projector='ui_presets:ui_preset',
        native_keys=()),
    ToolSpec(
        name='inspect_potions',
        schema=POTION_INSPECTION_SCHEMA,
        description="Read potion descriptions and hover help. summary matches basic slot data. slot_indices selects original belt positions; null entries are empty slots.",
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='potion_details:potion_details',
        reader_argument='request',
        parser='potion_presets:potion_arguments',
        projector='potion_presets:potion_preset',
        native_keys=('level',)),
    ToolSpec(
        name='use_potion',
        schema=USE_SCHEMA,
        description="Use one potion, in or out of combat when usable. Use inspect_targets when target requirements are unknown. "
            "Stops at choices; continue with selection tools.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='potion_action_details:potion_arguments',
        parser_operation=True),
    ToolSpec(
        name='discard_potion',
        schema=POTION_SCHEMA,
        description="Discard one potion through the native action. "
            "Allowed only when potions can be removed; automatic potions may be discarded.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='potion_action_details:potion_arguments',
        parser_operation=True),
    ToolSpec(
        name='inspect_combatants',
        schema=COMBATANT_SCHEMA,
        description="Read exposed combatant powers, intents, orbs and floating Sovereign Blades. "
            "summary keeps static data without hover help. sources selects objects or groups by canonical paths; [] selects none. "
            "Full hover help is unavailable during card drag/aim/play; disabled icons remain with a note.",
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='combatant_details:combatant_details',
        parser='combatant_presets:combatant_arguments',
        parser_operation=False,
        projector='combatant_presets:combatant_preset',
        native_keys=('preset',), native_renames=(('preset', 'level'),)),
    ToolSpec(
        name='inspect_relics',
        schema=RELIC_SCHEMA,
        description="Read displayed owned relics. Unavailable hover help is noted; "
            "summary keeps basic fields. relic_indices filters by positions in the current unfiltered inspection.",
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='relic_details:relic_details',
        reader_argument='request',
        parser='relic_presets:relic_arguments',
        parser_operation=False,
        projector='relic_presets:relic_preset',
        native_keys=('level',)),
    ToolSpec(
        name='inspect_deck',
        schema=DECK_SCHEMA,
        description="Open/reuse the native full-deck page when its entry is available and read the entire browsable deck. "
            "card_ids filters returned details only. Upgrade preview does not upgrade owned cards. "
            "Leaves the page open; close with close_card_view.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='deck_details:deck_details',
        parser='deck_presets:deck_arguments',
        parser_operation=False,
        projector='deck_presets:deck_preset',
        native_keys=('view_upgrades', 'sort_by', 'descending'),
        unchanged_view_rejections=True),
    ToolSpec(
        name='inspect_pile',
        schema=PILE_SCHEMA,
        description="Open/reuse a combat draw, discard or exhaust page, replacing another card page. "
            "Returns the entire pile in display order, never draw order. "
            "card_ids filters returned details only. Leaves opened pages until close_card_view; "
            "status distinguishes opened, empty and unavailable entries.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='pile_details:pile_details',
        parser='pile_presets:pile_arguments',
        parser_operation=False,
        projector='pile_presets:pile_preset',
        native_keys=('pile',),
        reader_argument='pile',
        unchanged_view_rejections=True),
    ToolSpec(
        name='close_card_view',
        schema=NO_ARGUMENTS,
        description="Close the top deck/draw/discard/exhaust browsing page and return actions_only context. "
            "Preserves an underlying map; cannot close card selections or other screens.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='observation_details:observation_details',
        projector='observation_presets:actions_only_result',
        native_keys=(),
        unchanged_view_rejections=True),
    ToolSpec(
        name='inspect_map',
        schema=MAP_SCHEMA,
        description="Open/reuse the current-act map, replacing a covering card page. Leaves it open. "
            "Returns the full graph by default; preset and max_steps limit returned data only. "
            "Does not travel or reveal unknown encounters; close with close_map.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='map_details:map_details',
        parser='map_details:map_arguments',
        parser_operation=False,
        projector='map_details:map_preset',
        native_keys=()),
    ToolSpec(
        name='close_map',
        schema=NO_ARGUMENTS,
        description="Close the exposed map using its enabled native back button; return a basic observation. "
            "Cannot close through card pages or force a mandatory map closed.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='view_details:closed_map',
        media=True),
    ToolSpec(
        name='inspect_selection',
        schema=SELECTION_SCHEMA,
        description="Read all browsable candidates, offered buttons and visible previews of the current card selection. "
            "Card descriptions and hover help by default; summary compacts every card, including bundles and previews. "
            "card_ids filters returned card details only; instructions and buttons remain. "
            "view_upgrades toggles an available native checkbox and keeps that UI state; unsupported screens return current data plus errors. "
            "Unavailable while the selection is hidden; never selects or confirms a card.",
        annotations=view,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='selection_details:inspect_selection_details',
        parser='selection_presets:selection_inspection_arguments',
        parser_operation=False,
        projector='selection_presets:selection_preset',
        native_keys=('view_upgrades',),
        changes_view_with_arguments=True),
    ToolSpec(
        name='select_card',
        schema=CARD_SCHEMA,
        description="Click one current selection candidate. Multi-select clicks toggle that card; "
            "single-choice screens may immediately submit. Use enabled selection.options to confirm when required. "
            "Hand upgrades preview before confirmation; click the selected card to deselect.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='selection_details:selection_arguments',
        parser_operation=True),
    ToolSpec(
        name='selection_option',
        schema=OPTION_SCHEMA,
        description="Click an offered selection button to confirm, cancel a preview, skip or choose a reward alternative. "
            "Choose card bundles with the offered bundle:N option.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='selection_details:selection_arguments',
        parser_operation=True),
    ToolSpec(
        name='set_selection_view',
        schema=VIEW_SCHEMA,
        description="Click the native eye to show battlefield or return to selection. "
            "Battlefield view permits available inspections, never normal combat actions. "
            "Close covering card/map views first.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='observation_details:observation_details',
        parser='selection_details:selection_arguments',
        parser_operation=True,
        media=True),
    ToolSpec(
        name='end_turn',
        schema=NO_ARGUMENTS,
        description="End the player's turn once and wait for the next input boundary, turn or run end. "
            "May stop for a choice before the next turn; inspect and resolve that selection separately.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details'),
    ToolSpec(
        name='capture_screenshot',
        schema=SCREENSHOT_SCHEMA,
        description="Save the current game viewport as PNG in the configured directory; return its path and dimensions. "
            "Does not change the UI or prepare an action.",
        annotations=view,
        category='screenshot',
        effect='file',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        parser='screenshot_tool:screenshot_arguments',
        parser_operation=False,
        refreshes_permission=False, media=True),
)
TOOLS = {spec.name: spec for spec in SPECS}
NATIVE_TOOLS = {spec.native_operation: spec for spec in SPECS}
