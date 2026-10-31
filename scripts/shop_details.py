from game_output import SHOP, SHOP_ITEM, SHOP_CARD, TIP, project


BUY_SCHEMA = {'type': 'object', 'properties': {'item_id': {
    'type': 'integer', 'minimum': 0,
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
    help_shape = {'description': str, 'hover_tips': [TIP]} if full and not used else {}
    if kind == 'card':
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
            if clean['kind'] == 'card' and set(text) != set(shape['card']) or not text.get('name'):
                raise ValueError('Missing visible item details.')
            if full and not used and any(set(tip) != set(TIP) for tip in text['hover_tips']):
                raise ValueError('Invalid shop hover help.')
            ids.add(clean['id']); positions.add(clean['position']); items.append(clean)
        result['items'] = items
    for key in ('open', 'back', 'proceed'):
        button = result[key]
        if button is not None and set(button) != ({'text', 'enabled'} if key == 'proceed' else {'enabled'}):
            raise ValueError('Invalid shop button.')
    return result


def inspect_shop_details(state):
    if state.get('scene') != 'shop': raise ValueError('Invalid shop inspection scene.')
    return {'scene': 'shop', 'shop': shop_details(state['shop'], full=True)}


def purchase_details(state):
    from transition_details import end_turn_details
    result = end_turn_details(state)
    if 'purchase_result' in state:
        purchase = project(state['purchase_result'], {'item_id': int, 'status': str})
        if (set(purchase) != {'item_id', 'status'} or purchase['item_id'] < 0 or purchase['status'] not in {
                'success', 'failure_space', 'failure_forbidden', 'failure_gold', 'failure_out_of_stock', 'canceled'}):
            raise ValueError('Invalid purchase result.')
        result['purchase_result'] = purchase
    return result
