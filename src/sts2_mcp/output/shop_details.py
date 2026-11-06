from sts2_mcp.output.value_shapes import project, TIP, TEXT, nullable
from sts2_mcp.output.contracts.rooms import SHOP, SHOP_ITEM, SHOP_CARD
from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.top_bar_summary import top_bar_details
from sts2_mcp.output.card_format import card_summary
from sts2_mcp.output.null_fields import apply_preset


BUY_SCHEMA = {'type': 'object', 'properties': {'item_id': {
    'type': 'integer', 'minimum': 0, 'maximum': 2147483647,
    'description': 'A current shop.items[].id from get_observation or inspect_shop; restocked items have new IDs.',
}},
              'required': ['item_id'], 'additionalProperties': False}


def shop_arguments(operation, arguments):
    if operation != 'buy_item':
        if arguments is not None and (not isinstance(arguments, dict) or arguments):
            raise ValueError('This shop action accepts no arguments.')
        return None
    if (not isinstance(arguments, dict) or set(arguments) != {'item_id'}
            or type(arguments['item_id']) is not int or not 0 <= arguments['item_id'] <= 2147483647):
        raise ValueError('A nonnegative integer item_id is required.')
    return dict(arguments)


def item_shape(kind, full=False, used=False):
    common = {key: SHOP_ITEM[key] for key in ('id', 'kind', 'position', 'price', 'affordable', 'enabled')}
    help_shape = {'description': TEXT, 'hover_tips': [TIP]} if full and not used else {}
    if kind == 'card':
        if full: help_shape = {'description': str, 'hover_tips': nullable([TIP])}
        return {**common, 'on_sale': bool, 'card': {**SHOP_CARD, **help_shape}}
    if kind in {'relic', 'potion', 'card_removal'}:
        return {**common, 'name': str, **({'used': bool} if kind == 'card_removal' else {}), **help_shape}
    raise ValueError('Unsupported shop item.')


def shop_details(value, *, full=False):
    result = project(value, SHOP)
    if set(result) != set(SHOP) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid shop structure.')
    if result['status'] == 'covered':
        if full or any(result[key] is not None for key in ('view', 'items', 'open', 'back', 'proceed')):
            raise ValueError('Hidden shop contents.')
        return result
    if result['view'] not in {'merchant', 'inventory', 'opening', 'closing'}:
        raise ValueError('Invalid shop view.')
    if result['view'] != 'inventory':
        if full or result['items'] is not None or result['back'] is not None:
            raise ValueError('Unopened shop contents.')
    else:
        if result['items'] is None or result['open'] is not None or result['proceed'] is not None:
            raise ValueError('Invalid inventory state.')
        items = []
        ids = set(); positions = set()
        for item in value['items']:
            used = item.get('used') is True and item.get('kind') == 'card_removal'
            shape = item_shape(item['kind'], full, used)
            clean = project(item, shape)
            if (set(clean) != set(shape) or clean['id'] < 0 or clean['id'] in ids or not clean['position']
                    or clean['position'] in positions or clean['price'] is not None and clean['price'] < 0):
                raise ValueError('Invalid shop item identity or price.')
            if used:
                if clean['price'] is not None or clean['affordable'] is not None or clean['enabled']:
                    raise ValueError('Hidden used removal price.')
            elif (clean['price'] is None) != (clean['affordable'] is None) or clean['enabled'] and clean['affordable'] is not True:
                raise ValueError('Invalid item availability.')
            text = clean['card'] if clean['kind'] == 'card' else clean
            required_card = {'name', 'type', 'rarity', 'visual_card_pool', 'energy_cost', 'star_cost'}
            if full: required_card |= {'description', 'hover_tips'}
            if (clean['kind'] == 'card' and not required_card <= text.keys()) or not text.get('name'):
                raise ValueError('Missing visible item details.')
            if full and not used and any(set(tip) != set(TIP) for tip in text['hover_tips'] or []):
                raise ValueError('Invalid shop hover help.')
            if full and not used and clean['kind'] != 'card' and text['description'] is None and text['hover_tips']:
                raise ValueError('Unreadable shop item cannot provide hover text.')
            ids.add(clean['id']); positions.add(clean['position']); items.append(clean)
        result['items'] = items
    for key in ('open', 'back', 'proceed'):
        button = result[key]
        if button is not None and set(button) != ({'text', 'enabled'} if key == 'proceed' else {'enabled'}):
            raise ValueError('Invalid shop button.')
    return result


def inspect_shop_details(state):
    context = scene_context(state)
    if context['scene'] != 'shop' or context['screen'] != {'status': 'visible'}:
        raise ValueError('Invalid shop inspection context.')
    shop = shop_details(state['shop'], full=True)
    expected = ['shop.items.' + str(item['id']) for item in shop['items'] if not item.get('used') and (
        item['card']['hover_tips'] is None if item['kind'] == 'card' else item['description'] is None)]
    sources = state.get('unavailable_hover_sources', [])
    if not isinstance(sources, list) or sources != expected:
        raise ValueError('Invalid or missing unavailable shop hover evidence.')
    complete = state.get('schema_version', 0) >= 43
    if complete and 'top_bar' not in state: raise ValueError('Missing purchasing top bar.')
    result = {**context, 'shop': shop, 'top_bar': top_bar_details(state.get('top_bar'), complete=complete)}
    if sources: result['unavailable_hover_sources'] = list(sources)
    return result


def shop_summary(value):
    """Use the same static merchant format for both validated observation paths."""
    shop = dict(value)
    if shop.get('items') is not None:
        shop['items'] = []
        for item in value['items']:
            row = {key: field for key, field in item.items() if key not in {'description', 'hover_tips'}}
            if item['kind'] == 'card': row['card'] = card_summary(item['card'])
            shop['items'].append(row)
    return apply_preset(shop, 'default', path=('shop',))
