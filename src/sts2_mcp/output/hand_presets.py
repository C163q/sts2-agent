from sts2_mcp.output.filtering import optional_filter, linked_help, filter_indices
"""Project validated hand details without changing the game's observation token."""
from sts2_mcp.output.card_play_details import CARD_ID
from sts2_mcp.output.card_format import card_summary
from sts2_mcp.output.resource_summary import resource_summary


HAND_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full includes card descriptions and shared hover help; summary keeps identity, visible costs, enchantments, afflictions and UI markers, without effects or hover help.'},
        'card_ids': {'type': ['array', 'null'], 'items': CARD_ID,
                     'description': 'Optional current hand IDs. Omit/null for all visible hand cards; [] returns none. Duplicates are ignored; results keep hand order. Unavailable IDs are grouped in errors[].card_ids alongside valid cards.'},
    },
    'additionalProperties': False,
}


def hand_arguments(arguments):
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'card_ids'}:
        raise ValueError('inspect_hand accepts only preset and card_ids.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid hand preset.')
    card_ids = arguments.get('card_ids')
    card_ids = optional_filter(card_ids, 'card_ids', integers=True)
    return {'preset': preset, 'card_ids': None if card_ids is None else list(dict.fromkeys(card_ids))}


def hand_preset(payload, preset, card_ids):
    if 'error' in payload or preset == 'full' and card_ids is None:
        return payload
    known = {card['id'] for card in payload['hand']}
    selected = known if card_ids is None else set(card_ids)
    cards = [card for card in payload['hand'] if card['id'] in selected]
    result = {**payload, 'hand': cards}
    if preset == 'summary':
        result = resource_summary(result)
        result['hand'] = [card_summary(card) for card in cards]
        result.pop('hover_tips', None)
    else:
        result['hover_tips'] = linked_help(payload['hover_tips'], 'card_ids', selected.__contains__)
    if preset == 'summary' or not cards:
        notes = {key: value for key, value in result.get('notes', {}).items() if key != 'card_values'}
        result.pop('notes', None)
        if notes:
            result['notes'] = notes
    missing = [card_id for card_id in card_ids or [] if card_id not in known]
    if missing:
        result['errors'] = [{'code': 'cards_not_in_hand', 'card_ids': missing}]
    return result
