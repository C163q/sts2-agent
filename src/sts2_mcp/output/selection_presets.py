from sts2_mcp.output.filtering import optional_filter, linked_help, filter_indices
"""Project validated selection details without changing native input or state."""
from sts2_mcp.output.card_play_details import CARD_ID
from sts2_mcp.output.selection_summary import PREVIEW_LISTS, selection_summary


SELECTION_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full keeps card descriptions and hover help; summary uses hand-summary fields for every candidate, bundle and preview card. Selection instructions and buttons remain.'},
        'card_ids': {'type': ['array', 'null'], 'items': {
            **CARD_ID, 'description': 'A current selection card ID from candidates, bundle contents or a visible preview; previews use the original card ID.'},
                     'description': 'Current selection card IDs, including bundle contents and visible previews. Omit/null for all; [] returns no card details. Instructions and buttons remain. Duplicates are ignored; native order remains. Previews use the original card ID. Unavailable IDs are grouped in errors[].card_ids alongside valid results.'},
        'view_upgrades': {'type': 'boolean',
                          'description': 'Toggle the native upgrade-preview checkbox when available; omit to keep its current state. Leaves the UI in that state. Unsupported screens return current cards plus errors[].code=upgrade_view_unavailable.'},
    },
    'additionalProperties': False,
}


def selection_inspection_arguments(arguments):
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'card_ids', 'view_upgrades'}:
        raise ValueError('Invalid selection inspection arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid selection inspection preset.')
    card_ids = arguments.get('card_ids')
    card_ids = optional_filter(card_ids, 'card_ids', integers=True)
    if 'view_upgrades' in arguments and type(arguments['view_upgrades']) is not bool:
        raise ValueError('Invalid selection upgrade option.')
    result = {'preset': preset, 'card_ids': None if card_ids is None else list(dict.fromkeys(card_ids))}
    if 'view_upgrades' in arguments:
        result['view_upgrades'] = arguments['view_upgrades']
    return result


def selection_preset(payload, preset, card_ids=None):
    if 'error' in payload or preset == 'full' and card_ids is None:
        return payload
    choice = dict(payload['selection'])
    known = {card['id'] for card in choice['cards']}
    known.update(card['id'] for bundle in choice.get('bundles', []) for card in bundle['cards'])
    if choice.get('upgrade_preview') is not None:
        known.add(choice['upgrade_preview']['before']['id'])
    for field in PREVIEW_LISTS:
        known.update(pair['before']['id'] for pair in choice.get(field, []))
    selected = known if card_ids is None else set(card_ids)

    def cards(items):
        return [card for card in items if card['id'] in selected]

    choice['cards'] = cards(choice['cards'])
    if 'bundles' in choice:
        choice['bundles'] = [{**bundle, 'cards': cards(bundle['cards'])}
                             for bundle in choice['bundles']]

    if choice.get('upgrade_preview') is not None:
        pair = choice['upgrade_preview']
        choice['upgrade_preview'] = pair if pair['before']['id'] in selected else None
    for field in PREVIEW_LISTS:
        if field in choice:
            choice[field] = [pair for pair in choice[field] if pair['before']['id'] in selected]
    result = {**payload, 'selection': choice}
    if preset == 'summary':
        result['selection'] = selection_summary(choice)
        result.pop('hover_tips', None)
    else:
        result['hover_tips'] = linked_help(payload['hover_tips'], 'card_ids', selected.__contains__)
    missing = [card_id for card_id in card_ids or [] if card_id not in known]
    if missing:
        result['errors'] = [*result.get('errors', []), {'code': 'cards_not_in_selection', 'card_ids': missing}]
    return result
