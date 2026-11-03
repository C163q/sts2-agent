from sts2_mcp.output.value_shapes import project, TIP
from sts2_mcp.output.contracts.rooms import REWARDS, REWARD_ITEM


CLAIM_SCHEMA = {
    'type': 'object', 'properties': {'reward_id': {
        'type': 'integer', 'minimum': 0, 'maximum': 2147483647,
        'description': 'A current rewards.items[].id from get_observation or inspect_rewards.',
    }},
    'required': ['reward_id'], 'additionalProperties': False,
}


def reward_arguments(operation, arguments):
    if operation == 'proceed':
        if arguments is not None and (not isinstance(arguments, dict) or arguments):
            raise ValueError('Proceed takes no arguments.')
        return None
    if (not isinstance(arguments, dict) or set(arguments) != {'reward_id'}
            or type(arguments['reward_id']) is not int or not 0 <= arguments['reward_id'] <= 2147483647):
        raise ValueError('Invalid reward ID.')
    return {'reward_id': arguments['reward_id']}


def rewards_details(value, *, full=False):
    item_shape = {**REWARD_ITEM, 'hover_tips': [TIP]} if full else REWARD_ITEM
    result = project(value, {**REWARDS, 'items': ([item_shape],)})
    if set(result) != set(REWARDS) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid rewards structure.')
    if result['status'] == 'covered':
        if result['title'] is not None or result['items'] is not None or result['proceed'] is not None or full:
            raise ValueError('Hidden reward contents.')
        return result
    if result['items'] is None:
        raise ValueError('Missing reward rows.')
    ids = set()
    for item in result['items']:
        if (set(item) != set(item_shape) or not 0 <= item['id'] <= 2147483647 or item['id'] in ids
                or item['type'] not in {'gold', 'potion', 'relic', 'card', 'special_card', 'card_removal', 'unsupported'}
                or not item['text'] or (item['linked_group'] is not None and item['linked_group'] < 0)):
            raise ValueError('Invalid reward row.')
        ids.add(item['id'])
        if full and any(set(tip) != set(TIP) for tip in item['hover_tips']):
            raise ValueError('Invalid reward hover help.')
    if result['proceed'] is not None and (set(result['proceed']) != {'text', 'enabled', 'skips_remaining'}
                                          or not result['proceed']['text']):
        raise ValueError('Invalid reward proceed button.')
    return result


def inspect_rewards_details(state):
    if state.get('scene') != 'rewards':
        raise ValueError('Invalid rewards inspection scene.')
    return {'scene': 'rewards', 'rewards': rewards_details(state['rewards'], full=True)}
