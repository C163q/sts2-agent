"""Validate one discard request without predicting later queue execution."""
from sts2_mcp.output.value_shapes import project


DISCARD = {'slot_index': int, 'name': str, 'status': str}
STATUSES = {'queued', 'discarded', 'not_discarded', 'unknown'}


def potion_discard_requires_observation(payload):
    return (payload.get('potion_discard') or {}).get('status') in {'unknown', 'not_discarded'}


def discard_potion_details(state, arguments=None):
    from sts2_mcp.output.transition_details import end_turn_details
    from sts2_mcp.output.available_tools import INSPECTIONS, VIEWS, TOOLS_WITHOUT_PERMISSION

    result = end_turn_details(state)
    discard = project(state['potion_discard'], DISCARD)
    if (set(discard) != set(DISCARD) or not 0 <= discard['slot_index'] <= 2147483647
            or not discard['name'].strip() or discard['status'] not in STATUSES
            or arguments is not None and discard['slot_index'] != arguments['potion_slot']):
        raise ValueError('Invalid potion discard result.')
    transition = result['transition']
    witnessed = any(e['type'] == 'potion_discarded'
        and e['potion']['slot_index'] == discard['slot_index']
        and e['potion']['name'] == discard['name'] for e in transition['events'])
    if discard['status'] == 'discarded' and not witnessed:
        raise ValueError('A discarded result requires a visible discard event.')
    if discard['status'] in {'queued', 'not_discarded'} and witnessed:
        raise ValueError('A pending or canceled discard cannot already have a discard event.')
    if discard['status'] == 'queued' and (transition['stop_reason'] != 'choice_required'
            or not transition['complete'] or (result.get('selection') or {}).get('status') != 'visible'
            or result['selection']['type'] in {'unsupported', 'view_cards'}):
        raise ValueError('A queued discard requires a complete visible choice boundary.')
    result['potion_discard'] = discard
    if potion_discard_requires_observation(result):
        result['available_actions'] = [a for a in result['available_actions']
            if a in (INSPECTIONS | VIEWS) & TOOLS_WITHOUT_PERMISSION]
    return result
