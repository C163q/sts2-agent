"""Strict batch receipt format independent of tool readers."""
from sts2_mcp.output.value_shapes import project, TEXT, NUMBER


RESULT = {'index': int, 'card_id': int, 'target_id': NUMBER, 'status': str, 'reason': TEXT}
BATCH = {'batch_id': str, 'results': [RESULT]}
STATUSES = {'not_submitted', 'queued', 'resolving', 'played', 'not_played', 'unknown'}


def uncertain_card_plays(payload):
    return any(row['status'] == 'unknown' for row in payload.get('card_plays', {}).get('results', []))


def card_plays(value):
    result = project(value, BATCH)
    if set(result) != set(BATCH) or not result['batch_id'].strip() or not result['results']:
        raise ValueError('Invalid card play batch.')
    seen = set()
    for index, row in enumerate(result['results']):
        if (set(row) != set(RESULT) or row['index'] != index or not 0 <= row['card_id'] <= 2147483647
                or row['card_id'] in seen or row['status'] not in STATUSES
                or row['target_id'] is not None and not 0 <= row['target_id'] <= 4294967295):
            raise ValueError('Invalid card play result.')
        if row['status'] in {'not_submitted', 'not_played', 'unknown'}:
            if not row['reason'] or not row['reason'].strip():
                raise ValueError('Missing unplayed card explanation.')
        elif row['reason'] is not None:
            raise ValueError('Unexpected card play explanation.')
        seen.add(row['card_id'])
    return result
