"""Filter validated merchant rows and share static summaries with observations."""
from sts2_mcp.output.filtering import optional_filter
from sts2_mcp.output.shop_details import shop_summary

KINDS = ('card', 'relic', 'potion', 'card_removal')
SHOP_SCHEMA = {'type': 'object', 'properties': {
    'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
        'description': 'summary keeps static goods and compact cards, omitting descriptions and hover help.'},
    'item_ids': {'type': ['array', 'null'], 'items': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647},
        'description': 'Current shop item IDs. Omit/null for all; [] for none. Missing IDs are grouped in errors.'},
    'kinds': {'type': ['array', 'null'], 'items': {'type': 'string', 'enum': list(KINDS)},
        'description': 'Optional goods categories. Omit/null for all; [] for none. Combined with item_ids by intersection.'}},
    'additionalProperties': False}


def shop_inspection_arguments(arguments):
    arguments = {} if arguments is None else arguments
    ids = optional_filter(arguments.get('item_ids'), 'item_ids', integers=True)
    kinds = optional_filter(arguments.get('kinds'), 'kinds')
    if kinds is not None and any(kind not in KINDS for kind in kinds):
        raise ValueError('kinds accepts card, relic, potion and card_removal.')
    return {'preset': arguments.get('preset', 'full'), 'item_ids': ids, 'kinds': kinds}


def shop_preset(payload, preset, item_ids, kinds):
    if 'error' in payload or preset == 'full' and item_ids is None and kinds is None:
        return payload
    shop = shop_summary(payload['shop']) if preset == 'summary' else dict(payload['shop'])
    result = {**payload, 'shop': shop}
    known = {item['id'] for item in shop['items']}
    selected = known if item_ids is None else set(item_ids)
    categories = set(KINDS if kinds is None else kinds)
    shop['items'] = [item for item in shop['items'] if item['id'] in selected and item['kind'] in categories]
    missing = [identifier for identifier in item_ids or [] if identifier not in known]
    if missing: result['errors'] = [{'code': 'item_ids_not_found', 'item_ids': missing}]
    notes = dict(result.get('notes', {}))
    unavailable = notes.pop('hover_tips_unavailable', None)
    if unavailable and preset != 'summary':
        wanted = {'shop.items.' + str(item['id']) for item in shop['items']}
        sources = [source for source in unavailable['sources'] if source in wanted]
        if sources: notes['hover_tips_unavailable'] = {**unavailable, 'sources': sources}
    if notes: result['notes'] = notes
    else: result.pop('notes', None)
    return result
