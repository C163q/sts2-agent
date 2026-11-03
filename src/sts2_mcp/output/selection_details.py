from sts2_mcp.output.value_shapes import project, TIP
from sts2_mcp.output.contracts.cards import CARD_FULL as HAND_CARD
from sts2_mcp.output.contracts.selection import SELECTION_OUTPUT, SELECTION, UPGRADE_PREVIEW, SELECTION_OPTION
from sts2_mcp.output.scene_context import SCENES as OBSERVATION_SCENES


CARD_SCHEMA = {"type": "object", "properties": {"card_id": {
    "type": "integer", "minimum": 0, "maximum": 2147483647,
    "description": "A current selection.cards[].id from get_observation or inspect_selection; not a candidate position.",
}},
               "required": ["card_id"], "additionalProperties": False}
OPTION_SCHEMA = {"type": "object", "properties": {"option_id": {
    "type": "string", "minLength": 1, "maxLength": 128,
    "description": "An enabled selection.options[].id from get_observation or inspect_selection; use the exact offered value.",
}},
                 "required": ["option_id"], "additionalProperties": False}
VIEW_SCHEMA = {"type": "object", "properties": {"view": {
    "type": "string", "enum": ["battlefield", "selection"],
    "description": "battlefield hides the pending selection for inspection; selection returns to its candidates and buttons.",
}},
               "required": ["view"], "additionalProperties": False}


def selection_arguments(operation, arguments):
    field = {"select_card": "card_id", "selection_option": "option_id", "set_selection_view": "view"}[operation]
    if not isinstance(arguments, dict) or set(arguments) != {field}:
        raise ValueError("Invalid selection arguments.")
    value = arguments[field]
    if (field == "card_id" and (type(value) is not int or not 0 <= value <= 2147483647)
            or field == "option_id" and (not isinstance(value, str) or not value.strip() or len(value) > 128)
            or field == "view" and value not in ("battlefield", "selection")):
        raise ValueError("Invalid selection argument.")
    return {field: value}


def selection_details(value):
    result = project(value, SELECTION_OUTPUT)
    if (not set(SELECTION) <= result.keys() or result["type"] not in
            {"choose_one", "reward", "grid", "combat_pile", "deck", "deck_upgrade", "deck_enchant", "deck_transform", "bundle", "view_cards", "hand", "hand_upgrade", "unsupported"}
            or result["status"] not in {"visible", "battlefield", "covered", "unsupported"}):
        raise ValueError("Invalid card selection.")
    upgrade_fields = {'can_view_upgrades', 'view_upgrades'}
    if upgrade_fields & result.keys():
        if (not upgrade_fields <= result.keys()
                or result['status'] != 'visible' and (result['can_view_upgrades'] or result['view_upgrades'] is not None)
                or result['status'] == 'visible' and result['view_upgrades'] is None
                or (result['can_view_upgrades'] or result['view_upgrades'] is True)
                    and result['type'] not in {'deck_upgrade', 'deck_transform', 'view_cards'}):
            raise ValueError('Invalid selection upgrade view.')
    preview = result.get("upgrade_preview")
    if result["type"] == "hand_upgrade":
        if "upgrade_preview" not in result:
            raise ValueError("Missing upgrade preview state.")
        if preview is not None and (set(preview) != set(UPGRADE_PREVIEW)
                or any(not {"id", "name", "description"} <= card.keys() or card['id'] < 0
                       for card in preview.values())
                or result["selected_ids"] != [preview['before']['id']]
                or preview['before']['id'] != preview['after']['id']):
            raise ValueError("Invalid upgrade preview.")
    elif preview is not None:
        raise ValueError("Unexpected upgrade preview.")
    previews = result.get('upgrade_previews', [])
    if result['type'] == 'deck_upgrade':
        if 'upgrade_previews' not in result:
            raise ValueError('Missing deck upgrade previews.')
        preview_ids = []
        for pair in previews:
            if (set(pair) != set(UPGRADE_PREVIEW) or any(not {'id', 'name', 'description'} <= c.keys() or c['id'] < 0
                                                       for c in pair.values())
                    or pair['before']['id'] != pair['after']['id']):
                raise ValueError('Invalid deck upgrade preview identity.')
            preview_ids.append(pair['before']['id'])
        if len(set(preview_ids)) != len(preview_ids) or previews and set(preview_ids) != set(result['selected_ids'] or []):
            raise ValueError('Invalid deck upgrade preview selection.')
    elif previews:
        raise ValueError('Unexpected deck upgrade previews.')
    transformations = result.get('transform_previews', [])
    if result['type'] == 'deck_transform':
        if 'transform_previews' not in result: raise ValueError('Missing transform previews.')
        preview_ids = []
        for pair in transformations:
            if (set(pair) != {'before', 'after', 'random'} or not {'id', 'name', 'description'} <= pair['before'].keys()
                    or pair['before']['id'] < 0 or pair['random'] != (pair['after'] is None)
                    or pair['after'] is not None and (not {'id', 'name', 'description'} <= pair['after'].keys()
                                                     or pair['after']['id'] != pair['before']['id'])):
                raise ValueError('Invalid transform preview.')
            preview_ids.append(pair['before']['id'])
        if len(set(preview_ids)) != len(preview_ids) or transformations and set(preview_ids) != set(result['selected_ids'] or []):
            raise ValueError('Invalid transform selection.')
    elif transformations: raise ValueError('Unexpected transform previews.')
    bundles = result.get('bundles', [])
    if result['type'] == 'bundle':
        if 'bundles' not in result or any(set(b) != {'id', 'cards'} or not b['id'].startswith('bundle:')
                                         or any(not {'id', 'name'} <= c.keys() for c in b['cards']) for b in bundles):
            raise ValueError('Invalid bundles.')
        if len({b['id'] for b in bundles}) != len(bundles): raise ValueError('Repeated bundle.')
    elif bundles: raise ValueError('Unexpected bundles.')
    enchantment = result.get('enchantment')
    enchanted = result.get('enchant_previews', [])
    if result['type'] == 'deck_enchant':
        if 'enchantment' not in result or 'enchant_previews' not in result:
            raise ValueError('Missing enchantment preview state.')
        if enchantment is not None and set(enchantment) != {'title', 'description'}:
            raise ValueError('Invalid enchantment help.')
        preview_ids = []
        for pair in enchanted:
            if (set(pair) != set(UPGRADE_PREVIEW) or any(not {'id', 'name', 'description'} <= c.keys() or c['id'] < 0
                                                      for c in pair.values()) or pair['before']['id'] != pair['after']['id']):
                raise ValueError('Invalid enchantment preview identity.')
            preview_ids.append(pair['before']['id'])
        if len(set(preview_ids)) != len(preview_ids) or enchanted and set(preview_ids) != set(result['selected_ids'] or []):
            raise ValueError('Invalid enchantment preview selection.')
    elif enchantment is not None or enchanted:
        raise ValueError('Unexpected enchantment preview.')
    if result["status"] != "visible":
        if (any(result[key] is not None for key in
                ("prompt", "min_select", "max_select", "selected_ids", "cards")) or result["options"] or preview is not None or previews or enchantment is not None or enchanted or transformations or bundles):
            raise ValueError("Hidden selection contents.")
        return result
    minimum, maximum = result["min_select"], result["max_select"]
    if (type(minimum) is not int or type(maximum) is not int or not 0 <= minimum <= maximum
            or result["cards"] is None or result["selected_ids"] is None
            or any(i < 0 for i in result["selected_ids"])
            or len(set(result["selected_ids"])) != len(result["selected_ids"])):
        raise ValueError("Invalid selection rules.")
    ids = []
    for card in result["cards"]:
        if not {"id", "name"} <= card.keys() or card["id"] < 0:
            raise ValueError("Invalid selection card.")
        ids.append(card["id"])
    if len(set(ids)) != len(ids):
        raise ValueError("Repeated selection card.")
    options = []
    for option in result["options"]:
        if set(option) != set(SELECTION_OPTION) or not option["id"]:
            raise ValueError("Invalid selection option.")
        options.append(option["id"])
    if len(set(options)) != len(options):
        raise ValueError("Repeated selection option.")
    return result


def inspect_selection_details(state):
    if state.get("scene") not in OBSERVATION_SCENES:
        raise ValueError("Invalid selection inspection scene.")
    raw = state["selection"]
    selection = selection_details(raw)
    if selection["status"] != "visible":
        raise ValueError("Selection inspection is hidden.")
    selection["cards"] = project(raw["cards"], [HAND_CARD])
    for card in selection["cards"]:
        if (not {"description", "hover_tips"} <= card.keys()
                or any(set(tip) != set(TIP) for tip in card["hover_tips"] or [])):
            raise ValueError("Incomplete selection detail.")
    if selection['type'] == 'bundle':
        selection['bundles'] = project(raw['bundles'], [{'id': str, 'cards': [HAND_CARD]}])
        if any(not {'description', 'hover_tips'} <= c.keys() for b in selection['bundles'] for c in b['cards']):
            raise ValueError('Incomplete bundle details.')
    result = {"scene": state["scene"], "selection": selection}
    if 'errors' in state:
        if (not isinstance(state['errors'], list) or state['errors'] != [{'code': 'upgrade_view_unavailable'}]
                or selection.get('can_view_upgrades') is not False):
            raise ValueError('Invalid selection upgrade warning.')
        result['errors'] = [{'code': 'upgrade_view_unavailable'}]
    return result
