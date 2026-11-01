"""Project validated hand details without changing the game's observation token."""
from card_play_details import CARD_ID


HAND_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full includes card descriptions and shared hover help; summary keeps identity, visible costs, cost colors and playability markers, without effects or hover help.'},
        'card_ids': {'type': 'array', 'items': CARD_ID,
                     'description': 'Optional current hand IDs. Omit for all visible hand cards; [] returns none. Duplicates are ignored; results keep hand order. Unavailable IDs are grouped in errors[].card_ids alongside valid cards.'},
    },
    'additionalProperties': False,
}
SUMMARY_FIELDS = frozenset({'id', 'name', 'type', 'energy_cost', 'star_cost',
                            'energy_cost_color', 'star_cost_color', 'unplayable_markers', 'outline'})


def hand_arguments(arguments):
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'card_ids'}:
        raise ValueError('Invalid hand arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid hand preset.')
    card_ids = arguments.get('card_ids')
    if 'card_ids' in arguments and (not isinstance(card_ids, list) or any(
            type(card_id) is not int or not 0 <= card_id <= 2147483647 for card_id in card_ids)):
        raise ValueError('Invalid hand card IDs.')
    return {'preset': preset, 'card_ids': None if card_ids is None else list(dict.fromkeys(card_ids))}


def hand_preset(payload, preset, card_ids):
    if 'error' in payload or preset == 'full' and card_ids is None:
        return payload
    known = {card['id'] for card in payload['hand']}
    selected = known if card_ids is None else set(card_ids)
    cards = [card for card in payload['hand'] if card['id'] in selected]
    result = {**payload, 'hand': cards}
    if preset == 'summary':
        result['hand'] = [{key: value for key, value in card.items() if key in SUMMARY_FIELDS
                           and not (key == 'star_cost' and value is None)} for card in cards]
        result.pop('hover_tips', None)
    else:
        result['hover_tips'] = [{**tip, 'card_ids': [i for i in tip['card_ids'] if i in selected]}
                                for tip in payload['hover_tips'] if any(i in selected for i in tip['card_ids'])]
    if preset == 'summary' or not cards:
        notes = {key: value for key, value in result.get('notes', {}).items() if key != 'card_values'}
        result.pop('notes', None)
        if notes:
            result['notes'] = notes
    missing = [card_id for card_id in card_ids or [] if card_id not in known]
    if missing:
        result['errors'] = [{'code': 'cards_not_in_hand', 'card_ids': missing}]
    return result
