"""Deck arguments and output-only identity filtering."""
import re

from sts2_mcp.output.card_format import browse_preset
from sts2_mcp.output.filtering import optional_filter, linked_help


SORT_KEYS = ('obtained', 'type', 'cost', 'name')
DECK_ID = {'type': 'string', 'pattern': r'^deck:(0|[1-9][0-9]*)$'}
DECK_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full includes card effects and shared hover help; summary uses compact card fields.'},
        'card_ids': {'type': ['array', 'null'], 'items': DECK_ID,
                     'description': 'Current deck:N instance IDs. Omit/null for all; [] returns none. Duplicates are ignored; native order remains. Missing IDs are grouped in errors[].card_ids; shared help is filtered too.'},
        'view_upgrades': {'type': 'boolean', 'description': 'Preview upgrades. Omit to keep the current page setting.'},
        'sort_by': {'type': 'string', 'enum': list(SORT_KEYS),
                    'description': "Change the native page's primary sort. Omit to keep it."},
        'descending': {'type': 'boolean', 'description': 'Requires sort_by; an explicit sort defaults to ascending.'},
    },
    'dependentRequired': {'descending': ['sort_by']},
    'additionalProperties': False,
}


def deck_arguments(arguments):
    arguments = {} if arguments is None else arguments
    if not isinstance(arguments, dict) or set(arguments) - DECK_SCHEMA['properties'].keys():
        raise ValueError('Invalid deck arguments.')
    preset = arguments.get('preset', 'full')
    if preset not in ('full', 'summary'):
        raise ValueError('Invalid browse preset.')
    if 'sort_by' in arguments and arguments['sort_by'] not in SORT_KEYS:
        raise ValueError('Invalid sorting key.')
    for key in ('view_upgrades', 'descending'):
        if key in arguments and type(arguments[key]) is not bool:
            raise ValueError('Invalid boolean option.')
    if 'descending' in arguments and 'sort_by' not in arguments:
        raise ValueError('Sorting direction requires a key.')
    ids = optional_filter(arguments.get('card_ids'), 'card_ids')
    if ids is not None and any(re.fullmatch(r'deck:(0|[1-9][0-9]*)', value) is None for value in ids):
        raise ValueError('card_ids must contain current deck:N instance IDs.')
    return {**arguments, 'preset': preset, 'card_ids': ids}


def deck_preset(payload, preset, card_ids=None):
    if 'error' in payload or preset == 'full' and card_ids is None:
        return payload
    known = {card['id'] for card in payload['deck']}
    selected = known if card_ids is None else set(card_ids)
    result = {**payload, 'deck': [card for card in payload['deck'] if card['id'] in selected]}
    result['hover_tips'] = linked_help(payload['hover_tips'], 'card_ids', selected.__contains__)
    missing = [value for value in card_ids or [] if value not in known]
    if missing:
        result['errors'] = [{'code': 'cards_not_in_deck', 'card_ids': missing}]
    return browse_preset(result, preset)
