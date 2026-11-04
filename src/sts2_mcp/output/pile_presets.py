"""Combat pile arguments and output-only identity filtering."""
import re

from sts2_mcp.output.card_format import browse_preset
from sts2_mcp.output.filtering import optional_filter, linked_help


PILES = ('draw', 'discard', 'exhaust')
PILE_SCHEMA = {
    'type': 'object',
    'properties': {
        'pile': {'type': 'string', 'enum': list(PILES), 'description': 'The combat pile to inspect.'},
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full includes card effects and shared hover help; summary keeps compact cards and omits fixed page help.'},
        'card_ids': {'type': ['array', 'null'], 'items': {'type': 'string', 'pattern': r'^pile:(0|[1-9][0-9]*)$'},
                     'description': 'Current pile:N instance IDs in this pile. Omit/null for all; [] returns none. Duplicates are ignored; native order remains. Missing IDs are grouped in errors[].card_ids; shared help is filtered too. Unavailable piles do not check membership.'},
    },
    'required': ['pile'],
    'additionalProperties': False,
}


def pile_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) - PILE_SCHEMA['properties'].keys()
            or arguments.get('pile') not in PILES or arguments.get('preset', 'full') not in ('full', 'summary')):
        raise ValueError('Invalid pile arguments.')
    ids = optional_filter(arguments.get('card_ids'), 'card_ids')
    if ids is not None and any(re.fullmatch(r'pile:(0|[1-9][0-9]*)', value) is None for value in ids):
        raise ValueError('card_ids must contain current pile:N instance IDs.')
    return {**arguments, 'preset': arguments.get('preset', 'full'), 'card_ids': ids}


def pile_preset(payload, preset, card_ids=None):
    if 'error' in payload or preset == 'full' and card_ids is None:
        return payload
    result = dict(payload)
    if payload['status'] != 'unavailable' and card_ids is not None:
        known = {card['id'] for card in payload['cards']}
        selected = set(card_ids)
        result['cards'] = [card for card in payload['cards'] if card['id'] in selected]
        result['hover_tips'] = linked_help(payload['hover_tips'], 'card_ids', selected.__contains__)
        missing = [value for value in card_ids if value not in known]
        if missing:
            result['errors'] = [{'code': 'cards_not_in_pile', 'card_ids': missing}]
    result = browse_preset(result, preset)
    if preset == 'summary' and payload['status'] == 'opened':
        result.pop('message', None)
    return result
