"""Action result validation composes observations and outcome-specific fields."""
from sts2_mcp.output.value_shapes import project
from sts2_mcp.output.transition_details import end_turn_details


def claim_reward_details(state):
    result = end_turn_details(state)
    outcome = project(state['reward_result'], {'reward_id': int, 'status': str})
    if (set(outcome) != {'reward_id', 'status'} or not 0 <= outcome['reward_id'] <= 2147483647
            or outcome['status'] not in {'claimed', 'not_claimed', 'pending', 'not_obtained'}):
        raise ValueError('Invalid reward outcome.')
    result['reward_result'] = outcome
    return result


def purchase_details(state):
    result = end_turn_details(state)
    if 'purchase_result' in state:
        purchase = project(state['purchase_result'], {'item_id': int, 'status': str})
        if (set(purchase) != {'item_id', 'status'} or purchase['item_id'] < 0 or purchase['status'] not in {
                'success', 'failure_space', 'failure_forbidden', 'failure_gold', 'failure_out_of_stock', 'canceled'}):
            raise ValueError('Invalid purchase result.')
        result['purchase_result'] = purchase
    return result
