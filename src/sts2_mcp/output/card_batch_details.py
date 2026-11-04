"""Validate batch inputs and native per-card outcomes before public compaction."""
from sts2_mcp.output.card_play_details import PLAY_SCHEMA, card_play_arguments
from sts2_mcp.output.card_batch_output import card_plays


BATCH_SCHEMA = {'type': 'object', 'properties': {
    'cards': {'type': 'array', 'minItems': 1, 'items': PLAY_SCHEMA,
              'description': 'Current hand cards in submission order. Each card_id may appear once.'}},
    'required': ['cards'], 'additionalProperties': False}


def batch_arguments(arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'cards'} \
            or not isinstance(arguments['cards'], list) or not arguments['cards']:
        raise ValueError('cards must be a nonempty array of card play objects.')
    cards, seen = [], set()
    for index, item in enumerate(arguments['cards']):
        try:
            card = card_play_arguments('play_card', item)
        except ValueError as error:
            raise ValueError(f'cards[{index}]: {error}') from error
        if card['card_id'] in seen:
            raise ValueError(f'cards[{index}].card_id duplicates an earlier hand card ID.')
        seen.add(card['card_id'])
        cards.append(card)
    return {'cards': cards}


def play_cards_details(state, arguments):
    from sts2_mcp.output.transition_details import end_turn_details
    result = end_turn_details(state)
    if 'card_plays' not in result:
        raise ValueError('Missing card play batch receipt.')
    expected = batch_arguments(arguments)['cards']
    rows = result['card_plays']['results']
    if len(rows) != len(expected) or any(row['card_id'] != item['card_id']
            or row['target_id'] != item.get('target_id') for row, item in zip(rows, expected, strict=True)):
        raise ValueError('Card play results do not match the submitted batch.')
    return result
