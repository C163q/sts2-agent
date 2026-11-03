from sts2_mcp.output.value_shapes import project, TIP
from sts2_mcp.output.contracts.ui import TOP_BAR
from sts2_mcp.output.contracts.endings import OPTION, RESULT, EPILOGUE, PHASES, EPILOGUE_TOOLS
import re


OPTION_SCHEMA = {'type': 'object', 'properties': {'option_id': {
    'type': 'string', 'minLength': 1, 'pattern': r'^[a-z][a-z0-9_]*(?::[0-9]+)?$',
    'description': 'An enabled run_result.options[].id from get_observation or inspect_run_result; use the exact offered value.',
}},
                 'required': ['option_id'], 'additionalProperties': False}


def option_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'option_id'}
            or not isinstance(arguments['option_id'], str)
            or not re.fullmatch(r'[a-z][a-z0-9_]*(?::[0-9]+)?', arguments['option_id'])):
        raise ValueError('Invalid run result option.')
    return arguments


def result_details(value, full=False):
    shape = RESULT
    if full:
        shape = {**RESULT, 'hover_tips': [{'source': str, **TIP}],
                 'cards': [{**RESULT['cards'][0], 'hover_tips': [TIP]}],
                 'relics': [{'name': (str,), 'description': str, 'hover_tips': [TIP]}],
                 'potions': [{'name': (str,), 'description': str, 'hover_tips': [TIP]}]}
    result = project(value, shape)
    if not set(RESULT) <= result.keys() or result['status'] not in {'visible', 'covered', 'not_ready'}:
        raise ValueError('Invalid result state.')
    if result['phase'] not in PHASES:
        raise ValueError('Invalid result phase.')
    ids = [option['id'] for option in result['options']]
    if len(set(ids)) != len(ids): raise ValueError('Duplicate result buttons.')
    for option in result['options']: option_arguments({'option_id': option['id']})
    if result['phase'] == 'outcome' and (result['score_lines'] or result['badges'] or result['discoveries'] or result['cards'] or result['relics'] or result['potions']):
        raise ValueError('Premature summary.')
    if any(b['rarity'] not in {'bronze', 'silver', 'gold'} for b in result['badges']): raise ValueError('Invalid badge rarity.')
    if any(d['count'] < 0 for d in result['discoveries']): raise ValueError('Invalid discovery count.')
    if result['status'] == 'covered' and (result['title'] is not None or result['texts']
            or result['score_lines'] or result['badges'] or result['discoveries'] or result['options'] or result['cards'] or result['relics'] or result['potions']):
        raise ValueError('Covered result contents.')
    return result


def epilogue_details(value):
    result = project(value, EPILOGUE)
    if not set(EPILOGUE) <= result.keys() or result['status'] not in {'visible', 'covered', 'not_ready'}:
        raise ValueError('Invalid epilogue.')
    if result['status'] == 'covered' and any(result[k] is not None for k in ('dialogue', 'continue', 'proceed')):
        raise ValueError('Covered dialogue contents.')
    return result


def validate_ending(result):
    for key in ('epilogue', 'run_result'):
        if result.get(key) is None:
            if result['scene'] == key or result['screen'].get('view') == key:
                raise ValueError('Missing ending screen.')
            continue
        result[key] = epilogue_details(result[key]) if key == 'epilogue' else result_details(result[key])
        value = result[key]
        if result['scene'] != key: raise ValueError('Ending scene mismatch.')
        if key == 'run_result' and 'inspect_ui' in result['available_actions'] and result.get('top_bar') is None:
            raise ValueError('Result UI help has no exposed top bar.')
        if value['status'] == 'visible':
            if result['screen'] != {'status': 'visible', 'view': key}: raise ValueError('Ending screen mismatch.')
            if key == 'run_result':
                if any(result.get(k) is not None for k in ('turn', 'player', 'enemies', 'buttons', 'event',
                        'selection', 'rewards', 'shop', 'treasure', 'rest_site', 'ancient', 'divination', 'confirmation', 'map')):
                    raise ValueError('Exposed underlying result contents.')
                if result.get('top_bar') is not None and not (set(TOP_BAR) - {'relic_count'}) <= result['top_bar'].keys():
                    raise ValueError('Incomplete result top bar.')
                enabled = any(o['enabled'] for o in value['options'])
                if any(a not in {'run_result_option', 'inspect_run_result', 'inspect_potions', 'inspect_relics', 'inspect_ui'} for a in result['available_actions']) \
                        or 'run_result_option' in result['available_actions'] and not enabled:
                    raise ValueError('Unavailable result action.')
            else:
                for action, field in [('advance_dialogue', 'continue'), ('proceed', 'proceed')]:
                    if action in result['available_actions'] and not (value[field] or {}).get('enabled'):
                        raise ValueError('Unavailable dialogue action.')
                if any(a not in EPILOGUE_TOOLS for a in result['available_actions']):
                    raise ValueError('Unexpected dialogue action.')
        elif result['available_actions'] and not (
                key == 'run_result' and value['status'] == 'not_ready'
                    and result['screen'] == {'status': 'visible', 'view': 'run_result'}
                    and set(result['available_actions']) <= {'inspect_potions', 'inspect_relics', 'inspect_ui'}
                or key == 'epilogue' and (result.get('map') is not None
                    or value['status'] == 'not_ready' and set(result['available_actions']) <= EPILOGUE_TOOLS - {'advance_dialogue', 'proceed'}
                    or value['status'] == 'covered' and result['screen'] == {'status': 'covered', 'view': 'deck'}
                        and set(result['available_actions']) <= {
                            'inspect_deck', 'close_card_view', 'inspect_map', 'inspect_potions', 'inspect_relics', 'inspect_ui'})):
            raise ValueError('Covered or unready ending actions.')
    if 'run_result_option' in result['available_actions'] and result.get('run_result') is None:
        raise ValueError('Missing result actions.')
    return result


def inspect_result_details(state):
    value = result_details(state['run_result'], full=True)
    if state.get('scene') != 'run_result' or value['status'] != 'visible':
        raise ValueError('Result details are unavailable.')
    return {'scene': 'run_result', 'run_result': value}
