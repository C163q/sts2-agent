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
from sts2_mcp.output.run_ending_details import OPTION_SCHEMA as RESULT_OPTION_SCHEMA, INSPECTION_SCHEMA as RESULT_INSPECTION_SCHEMA
from sts2_mcp.output.map_details import MAP_SCHEMA, TRAVEL_SCHEMA
from sts2_mcp.output.deck_presets import DECK_SCHEMA
from sts2_mcp.output.pile_presets import PILE_SCHEMA
from sts2_mcp.output.selection_details import CARD_SCHEMA, OPTION_SCHEMA, VIEW_SCHEMA
from sts2_mcp.output.card_play_details import PLAY_SCHEMA, TARGET_SCHEMA
from sts2_mcp.output.card_batch_details import BATCH_SCHEMA
from sts2_mcp.output.potion_action_details import POTION_SCHEMA, USE_SCHEMA
from sts2_mcp.screenshot_tool import SCREENSHOT_SCHEMA
from sts2_mcp.output.reward_details import CLAIM_SCHEMA
from sts2_mcp.output.reward_presets import REWARD_SCHEMA
from sts2_mcp.output.rest_site_details import REST_OPTION_SCHEMA
from sts2_mcp.output.rest_site_presets import REST_SCHEMA
from sts2_mcp.output.treasure_details import LOOT_SCHEMA
from sts2_mcp.output.treasure_presets import TREASURE_SCHEMA
from sts2_mcp.output.shop_details import BUY_SCHEMA
from sts2_mcp.output.shop_presets import SHOP_SCHEMA
from sts2_mcp.output.ancient_details import ANCIENT_OPTION_SCHEMA
from sts2_mcp.output.ancient_presets import ANCIENT_SCHEMA
from sts2_mcp.output.event_details import EVENT_OPTION_SCHEMA
from sts2_mcp.output.event_presets import EVENT_SCHEMA
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
        schema=RESULT_INSPECTION_SCHEMA,
        description='Read the current result or associated unlock page. summary keeps names and tip titles without effect text; not_ready marks an updating display.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='run_ending_details:inspect_result_details',
        projector='run_ending_details:result_preset',
        native_keys=()),
    ToolSpec(
        name='run_result_option',
        schema=RESULT_OPTION_SCHEMA,
        description='Click one enabled result button or timeline entry. Stops at the next page; only scene=main_menu confirms return to menu.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        unsubmitted_rejection_unchanged=True,
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
        unsubmitted_rejection_unchanged=True,
        reader='transition_details:end_turn_details',
        parser='map_details:travel_arguments',
        parser_operation=False),
    ToolSpec(
        name='respond_to_confirmation',
        schema=CONFIRMATION_SCHEMA,
        description='Respond to the visible Trial confirmation: confirm abandons this run; cancel returns to the event.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='confirmation_details:confirmation_arguments',
        parser_operation=False,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='set_divination_tool',
        schema=TOOL_SCHEMA,
        description='Switch between big (3x3) and small (one cell) divination without spending a reveal.',
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='observation_details:observation_details',
        parser='divination_details:divination_arguments',
        parser_operation=True,
        projector='observation_presets:actions_only_result',
        unchanged_view_rejections=True),
    ToolSpec(
        name='divine',
        schema=DIVINE_SCHEMA,
        description='Reveal a # cell with the current divination tool, spending one reveal. May pause for rewards or choices.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='divination_details:divination_arguments',
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='inspect_event',
        schema=EVENT_SCHEMA,
        description='Read current event text, options and hover help, or the visible divination text board. '
            'summary omits narrative/help; include_image optionally attaches the board PNG.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='event_details:inspect_event_details',
        projector='event_presets:inspect_event_preset',
        native_keys=(),
        media=True),
    ToolSpec(
        name='choose_event_option',
        schema=EVENT_OPTION_SCHEMA,
        description='Choose one enabled event option by ID. Follow the resulting selection, reward, divination or combat screen; '
            'use proceed after the event is finished.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        unsubmitted_rejection_unchanged=True,
        reader='transition_details:end_turn_details',
        parser='event_details:event_arguments',
        parser_operation=True),
    ToolSpec(
        name='inspect_ancient',
        schema=ANCIENT_SCHEMA,
        description='Read the current ancient dialogue, displayed gift options and their hover help.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='ancient_details:inspect_ancient_details',
        parser='ancient_presets:ancient_inspection_arguments',
        projector='ancient_presets:ancient_preset',
        native_keys=()),
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
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
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
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
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
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='close_shop',
        schema=NO_ARGUMENTS,
        description='Close shop inventory and return to the merchant.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='shop_details:shop_arguments',
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='inspect_shop',
        schema=SHOP_SCHEMA,
        description='Read displayed shop goods and purchasing top bar. summary omits effects and hover help; item_ids and kinds filter goods. Open the shop first.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='shop_details:inspect_shop_details',
        parser='shop_presets:shop_inspection_arguments',
        projector='shop_presets:shop_preset',
        native_keys=()),
    ToolSpec(
        name='buy_item',
        schema=BUY_SCHEMA,
        description='Buy one current item_id; restocked goods have new IDs. purchase_result reports the outcome; '
            'pending requires finishing the current selection or rewards. Canceling card removal costs nothing.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='action_details:purchase_details',
        reader_argument='request',
        parser='shop_details:shop_arguments',
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='get_observation',
        schema=OBSERVATION_SCHEMA,
        description="Read the current screen overview and available tool names. "
            "Card effects and hover help are available through dedicated inspections; exposed selections include all browsable candidates.",
        annotations=read_only,
        category='observation',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        operation='get_state',
        reader='observation_details:observation_details',
        projector='observation_presets:observation_preset',
        native_keys=()),
    ToolSpec(
        name='inspect_rewards',
        schema=REWARD_SCHEMA,
        description='Read current reward rows and hover help. summary keeps static rows; use inspect_selection for opened card rewards.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='reward_details:inspect_rewards_details',
        parser='reward_presets:reward_inspection_arguments',
        projector='reward_presets:reward_preset',
        native_keys=()),
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
        reader_argument='request',
        parser='reward_details:reward_arguments',
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
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
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='loot_treasure',
        schema=LOOT_SCHEMA,
        description='Open a single-player chest and take its relic, or take the relic already shown. '
            'Stops for rewards, choices or dialogs; call again for any remaining relic. '
            'Use open_only to inspect first and proceed to leave.',
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='transition_details:end_turn_details',
        parser='treasure_details:loot_arguments',
        parser_operation=False,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='inspect_treasure',
        schema=TREASURE_SCHEMA,
        description='Read the exposed chest and displayed relic help. summary keeps static room data without hover text.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='treasure_details:inspect_treasure_details',
        projector='treasure_presets:treasure_preset',
        native_keys=()),
    ToolSpec(
        name='inspect_rest_site',
        schema=REST_SCHEMA,
        description='Read displayed rest options and hover help, including disabled options. summary omits descriptions; option_ids filters by native ID.',
        annotations=read_only,
        category='inspection',
        effect='read',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='rest_site_details:inspect_rest_site_details',
        parser='rest_site_presets:rest_inspection_arguments',
        projector='rest_site_presets:rest_site_preset',
        native_keys=()),
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
        parser_operation=False,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='inspect_hand',
        schema=HAND_SCHEMA,
        description="Read current visible hand card details, HUD energy/stars and pile counts. "
            "Playability markers do not guarantee a legal play; use inspect_targets for targeting hints.",
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
        description="Show targeting hints and usability for a hand card or potion. "
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
        name='play_cards',
        schema=BATCH_SCHEMA,
        description='Queue current hand cards in order using native rules. Invalidated plays may be skipped. '
            "Choices can pause or cancel queued plays; unsubmitted entries are not saved for later. Check card_plays for each card's status.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='card_batch_details:play_cards_details',
        reader_argument='request',
        parser='card_batch_details:batch_arguments',
        unsubmitted_rejection_unchanged=True),
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
        description="Read hover help for exposed top-bar and combat UI. summary keeps titles and source paths; sources filters tips in any preset. "
            "Use default/full with sources to read selected descriptions. Use dedicated inspections for combatants, cards, potions and relics.",
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
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='discard_potion',
        schema=POTION_SCHEMA,
        description="Discard one potion, including automatic potions, when removal is allowed. "
            "During a choice it may queue until the choice is resolved; potion_discard reports this request's status. "
            "Read current state after unknown or not_discarded.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        returns_transition=True,
        records_events=True,
        reader='potion_discard_output:discard_potion_details',
        reader_argument='request',
        parser='potion_action_details:potion_arguments',
        parser_operation=True,
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='inspect_combatants',
        schema=COMBATANT_SCHEMA,
        description="Read exposed combatant health, poison/Doom health-bar previews, Block, powers, intents, orbs and floating Sovereign Blades. "
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
            "Read routes and selectable nodes; close with close_map. Travel with travel_to_node.",
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
        native_keys=(),
        unchanged_view_rejections=True),
    ToolSpec(
        name='close_map',
        schema=NO_ARGUMENTS,
        description="Close the exposed map using its enabled native back button; return actions_only context. "
            "Cannot close through card pages or force a mandatory map closed.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='view_details:closed_map',
        projector='observation_presets:actions_only_result',
        native_keys=(),
        unchanged_view_rejections=True),
    ToolSpec(
        name='inspect_selection',
        schema=SELECTION_SCHEMA,
        description="Read all browsable candidates, bundles, offered buttons and visible previews of the exposed card selection. "
            "view_upgrades can change the native preview setting. Use select_card or selection_option to choose.",
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
        changes_view_with_arguments=True,
        unchanged_view_rejections=True),
    ToolSpec(
        name='select_card',
        schema=CARD_SCHEMA,
        description="Click one current selection candidate. Multi-select clicks toggle that card; "
            "single-choice screens may immediately submit. Use enabled selection.options to confirm when required. "
            "Hand upgrades preview before confirmation; click the selected card to deselect. "
            "Accepted selections and deselections appear in transition.events.",
        annotations=action,
        category='action',
        effect='action',
        requires_permission=True,
        unsubmitted_rejection_unchanged=True,
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
        unsubmitted_rejection_unchanged=True,
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
            "Close covering card/map views first. Returns scene/screen, available_actions and selection type/status.",
        annotations=view,
        category='view',
        effect='view',
        requires_permission=False,
        returns_transition=False,
        records_events=False,
        reader='observation_details:observation_details',
        parser='selection_details:selection_arguments',
        parser_operation=True,
        projector='observation_presets:actions_only_result',
        unchanged_view_rejections=True,
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
        reader='transition_details:end_turn_details',
        unsubmitted_rejection_unchanged=True),
    ToolSpec(
        name='capture_screenshot',
        schema=SCREENSHOT_SCHEMA,
        description="Save the current game viewport as a PNG in the configured directory; return its local file path and pixel dimensions.",
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
