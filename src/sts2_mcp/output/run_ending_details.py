from sts2_mcp.output.value_shapes import project, TIP
from sts2_mcp.output.contracts.ui import TOP_BAR
from sts2_mcp.output.contracts.endings import OPTION, RESULT, EPILOGUE, PHASES, EPILOGUE_TOOLS
import re


OPTION_SCHEMA = {'type': 'object', 'properties': {'option_id': {
    'type': 'string', 'minLength': 1, 'pattern': r'^[a-z][a-z0-9_]*(?::[0-9]+)?$',
    'description': 'An enabled run_result.options[].id from get_observation or inspect_run_result; use the exact offered value.',
}},
                 'required': ['option_id'], 'additionalProperties': False}


INSPECTION_SCHEMA = {'type': 'object', 'properties': {'preset': {
    'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
    'description': 'summary keeps current text, item names and hover titles without effect descriptions.',
}}, 'additionalProperties': False}


def option_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'option_id'}
            or not isinstance(arguments['option_id'], str)
            or not re.fullmatch(r'[a-z][a-z0-9_]*(?::[0-9]+)?', arguments['option_id'])):
        raise ValueError('Invalid run result option.')
    return arguments


def result_details(value, full=False, *, require_complete=False):
    base_tip = {'source': str, 'title': (str,)}
    shape = {**RESULT, 'hover_tips': [base_tip]}
    if full:
        shape = {**shape, 'hover_tips': [{'source': str, **TIP}],
                 'cards': [{**RESULT['cards'][0], 'hover_tips': [TIP]}],
                 'relics': [{'name': (str,), 'description': (str,), 'hover_tips': [TIP]}],
                 'potions': [{'name': (str,), 'description': (str,), 'hover_tips': [TIP]}]}
    result = project(value, shape)
    required = set(RESULT) | ({'hover_tips'} if full or require_complete else set())
    if not required <= result.keys() or result['status'] not in {'visible', 'covered', 'not_ready'}:
        raise ValueError('Invalid result state.')
    if result['phase'] not in PHASES:
        raise ValueError('Invalid result phase.')
    for key, fields in [('score_lines', {'label', 'value'}), ('badges', {'name', 'rarity'}),
                        ('discoveries', {'kind', 'count'}), ('options', {'id', 'text', 'enabled'})]:
        if any(set(item) != fields for item in result[key]):
            raise ValueError('Incomplete result entry.')
    ids = [option['id'] for option in result['options']]
    if len(set(ids)) != len(ids): raise ValueError('Duplicate result buttons.')
    for option in result['options']: option_arguments({'option_id': option['id']})
    if result['phase'] == 'outcome' and any(result[key] for key in ('score_lines','badges','discoveries','cards','relics','potions')):
        raise ValueError('Premature summary.')
    if any(b['rarity'] not in {'bronze', 'silver', 'gold'} for b in result['badges']): raise ValueError('Invalid badge rarity.')
    if any(d['count'] < 0 for d in result['discoveries']): raise ValueError('Invalid discovery count.')
    card_ids = set()
    for card in result['cards']:
        fields = {'id','name'}
        if full: fields |= {'description','hover_tips'}
        if require_complete: fields |= {'type','rarity','visual_card_pool','energy_cost','star_cost','enchantment','affliction'}
        if not fields <= card.keys() or not re.fullmatch(r'card:[0-9]+', card['id']) or card['id'] in card_ids:
            raise ValueError('Incomplete or duplicate result card.')
        card_ids.add(card['id'])
        if require_complete and (
                card['enchantment'] is not None and not {'name','dimmed'} <= card['enchantment'].keys()
                or card['affliction'] is not None and set(card['affliction']) != {'name'}):
            raise ValueError('Incomplete result card appearance.')
        if full and any(set(tip) != set(TIP) for tip in card['hover_tips']):
            raise ValueError('Incomplete result card help.')
    for key in ('relics','potions'):
        fields = {'name','description','hover_tips'} if full else {'name'}
        for item in result[key]:
            if set(item) != fields or full and (any(set(tip) != set(TIP) for tip in item['hover_tips'])
                    or item['description'] is None and item['hover_tips']):
                raise ValueError('Incomplete result item help.')
    sources = []
    for tip in result.get('hover_tips', []):
        if set(tip) != set(shape['hover_tips'][0]) or not tip['source'] or tip['source'] in sources:
            raise ValueError('Incomplete or duplicate result hover help.')
        sources.append(tip['source'])
    if require_complete:
        rendered = value.get('hover_sources')
        unavailable = value.get('unavailable_hover_sources')
        if (not isinstance(rendered, list) or any(not isinstance(source, str) or not source for source in rendered)
                or len(set(rendered)) != len(rendered) or not isinstance(unavailable, list)
                or any(not isinstance(source, str) for source in unavailable)
                or len(set(unavailable)) != len(unavailable)):
            raise ValueError('Invalid result hover associations.')

        def validate_tip_reference(source):
            if source.startswith('badge:'):
                suffix = source.removeprefix('badge:')
                if not suffix.isdecimal() or not 0 <= int(suffix) < len(result['badges']):
                    raise ValueError('Invalid result badge reference.')
            elif source.startswith('discovery:'):
                if source.removeprefix('discovery:') not in {item['kind'] for item in result['discoveries']}:
                    raise ValueError('Invalid result discovery reference.')
            elif source.startswith('epoch:') and not re.fullmatch(r'epoch:[0-9]+', source):
                raise ValueError('Invalid result epoch reference.')

        for source in rendered: validate_tip_reference(source)
        missing_tips = set()
        for path in unavailable:
            if path.startswith('run_result.hover_tips.'):
                source = path.removeprefix('run_result.hover_tips.')
                if source not in rendered or source in sources:
                    raise ValueError('Conflicting result hover availability.')
                validate_tip_reference(source); missing_tips.add(source)
            elif path.startswith('run_result.cards.'):
                identity = path.removeprefix('run_result.cards.')
                if identity not in card_ids or next(card for card in result['cards'] if card['id'] == identity).get('hover_tips'):
                    raise ValueError('Invalid unavailable result card reference.')
            else:
                match = re.fullmatch(r'run_result\.(relics|potions)\.([0-9]+)', path)
                if match is None: raise ValueError('Invalid unavailable result source.')
                kind, index = match[1], int(match[2])
                if index >= len(result[kind]): raise ValueError('Invalid unavailable result item reference.')
                item = result[kind][index]
                if full and (item['description'] is not None or item['hover_tips']):
                    raise ValueError('Conflicting result item hover availability.')
        if set(rendered) != set(sources) | missing_tips or set(sources) - set(rendered):
            raise ValueError('Invalid result hover associations.')
    if result['status'] == 'covered' and (result['title'] is not None or any(result[key] for key in (
            'texts','score_lines','badges','discoveries','options','cards','relics','potions','hover_tips'))):
        raise ValueError('Covered result contents.')
    return result


def result_summary(value, *, card_mode='summary'):
    from sts2_mcp.output.card_format import format_card
    result = dict(value)
    result['cards'] = [format_card(card, card_mode) for card in value['cards']]
    for key in ('relics','potions'):
        result[key] = [{'name': item['name']} for item in value[key]]
    if 'hover_tips' in value:
        result['hover_tips'] = [{key: tip[key] for key in ('source','title')} for tip in value['hover_tips']]
    return result


def result_preset(payload, preset):
    if 'error' in payload or preset != 'summary': return payload
    from sts2_mcp.output.null_fields import apply_preset
    result = dict(payload)
    result['run_result'] = result_summary(payload['run_result'])
    notes = dict(result.get('notes', {}))
    notes.pop('hover_tips_unavailable', None)
    if notes: result['notes'] = notes
    else: result.pop('notes', None)
    return apply_preset(result, 'default')


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
        if value['status'] in {'visible', 'not_ready'}:
            if result['screen'] != {'status': 'visible', 'view': key}: raise ValueError('Ending screen mismatch.')
            if key == 'run_result':
                if any(result.get(k) is not None for k in ('turn', 'player', 'enemies', 'buttons', 'event',
                        'selection', 'rewards', 'shop', 'treasure', 'rest_site', 'ancient', 'divination', 'confirmation', 'map')):
                    raise ValueError('Exposed underlying result contents.')
                if result.get('top_bar') is not None and not (set(TOP_BAR) - {'relic_count'}) <= result['top_bar'].keys():
                    raise ValueError('Incomplete result top bar.')
                enabled = any(o['enabled'] for o in value['options'])
                if any(a not in ({'inspect_run_result', 'inspect_potions', 'inspect_relics', 'inspect_ui'}
                        | ({'run_result_option'} if value['status'] == 'visible' else set())) for a in result['available_actions']) \
                        or 'run_result_option' in result['available_actions'] and not enabled:
                    raise ValueError('Unavailable result action.')
            else:
                for action, field in [('advance_dialogue', 'continue'), ('proceed', 'proceed')]:
                    if action in result['available_actions'] and not (value[field] or {}).get('enabled'):
                        raise ValueError('Unavailable dialogue action.')
                if any(a not in (EPILOGUE_TOOLS if value['status'] == 'visible' else EPILOGUE_TOOLS - {'advance_dialogue', 'proceed'}) for a in result['available_actions']):
                    raise ValueError('Unexpected dialogue action.')
        elif result['available_actions'] and not (
                key == 'run_result' and value['status'] == 'not_ready'
                    and result['screen'] == {'status': 'visible', 'view': 'run_result'}
                    and set(result['available_actions']) <= {'inspect_potions', 'inspect_relics', 'inspect_ui', 'inspect_run_result'}
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
    from sts2_mcp.output.scene_context import scene_context
    context = scene_context(state)
    if context != {'scene': 'run_result', 'screen': {'status': 'visible', 'view': 'run_result'}}:
        raise ValueError('Invalid run result inspection context.')
    value = result_details(state['run_result'], full=True, require_complete=state.get('schema_version', 0) >= 47)
    if value['status'] not in {'visible', 'not_ready'}:
        raise ValueError('Result details are unavailable.')
    result = {**context, 'run_result': value}
    unavailable = state['run_result'].get('unavailable_hover_sources', [])
    if unavailable: result['unavailable_hover_sources'] = list(unavailable)
    return result
