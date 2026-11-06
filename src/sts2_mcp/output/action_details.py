"""Action result validation composes observations and outcome-specific fields."""
from sts2_mcp.output.value_shapes import project
from sts2_mcp.output.transition_details import end_turn_details


def claim_reward_details(state, arguments=None):
    result = end_turn_details(state)
    outcome = project(state['reward_result'], {'reward_id': int, 'status': str})
    if (set(outcome) != {'reward_id', 'status'} or not 0 <= outcome['reward_id'] <= 2147483647
            or outcome['status'] not in {'claimed', 'not_claimed', 'pending', 'not_obtained'}
            or arguments is not None and outcome['reward_id'] != arguments['reward_id']):
        raise ValueError('Invalid reward outcome.')
    result['reward_result'] = outcome
    return result


def purchase_details(state, arguments=None):
    result = end_turn_details(state)
    transition = result['transition']
    reason = transition['stop_reason']
    selection = result.get('selection') or {}
    rewards = result.get('rewards') or {}
    awaiting_input = (reason == 'choice_required' and selection.get('status') == 'visible'
                      or reason == 'action_completed' and rewards.get('status') == 'visible')
    if 'purchase_result' in state:
        purchase = project(state['purchase_result'], {'item_id': int, 'status': str})
        if (set(purchase) != {'item_id', 'status'} or not 0 <= purchase['item_id'] <= 2147483647
                or arguments is not None and purchase['item_id'] != arguments['item_id']
                or purchase['status'] not in {'success', 'failure_space', 'failure_forbidden', 'failure_gold',
                    'failure_out_of_stock', 'canceled', 'pending'}
                or purchase['status'] == 'pending' and not awaiting_input):
            raise ValueError('Invalid purchase result.')
        result['purchase_result'] = purchase
    elif state.get('schema_version', 0) >= 44 and reason in {'action_completed', 'choice_required'}:
        raise ValueError('Missing purchase result at a known boundary.')
    return result
