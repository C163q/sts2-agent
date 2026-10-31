from game_output import REST_SITE, REST_OPTION, project
from selection_details import OPTION_SCHEMA, selection_arguments


REST_OPTION_SCHEMA = {**OPTION_SCHEMA, 'properties': {'option_id': {
    **OPTION_SCHEMA['properties']['option_id'],
    'description': 'An enabled rest_site.options[].id from get_observation or inspect_rest_site.',
}}}


def rest_option_arguments(arguments):
    return selection_arguments('selection_option', arguments)


def rest_site_details(value, *, full=False):
    option_shape = {**REST_OPTION, 'description': str} if full else REST_OPTION
    result = project(value, {**REST_SITE, 'options': ([option_shape],)})
    if set(result) != set(REST_SITE) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid rest site structure.')
    if result['status'] == 'covered':
        if full or any(result[key] is not None for key in ('prompt', 'description', 'options', 'proceed')):
            raise ValueError('Hidden rest site contents.')
        return result
    if result['options'] is None:
        raise ValueError('Missing rest options.')
    ids = set()
    for option in result['options']:
        if (set(option) != set(option_shape) or not option['id'].strip() or len(option['id']) > 128
                or option['id'] in ids or not option['text']):
            raise ValueError('Invalid rest option.')
        ids.add(option['id'])
    if result['proceed'] is not None and (set(result['proceed']) != {'text', 'enabled'} or not result['proceed']['text']):
        raise ValueError('Invalid rest site proceed button.')
    return result


def inspect_rest_site_details(state):
    if state.get('scene') != 'rest_site':
        raise ValueError('Invalid rest site inspection scene.')
    return {'scene': 'rest_site', 'rest_site': rest_site_details(state['rest_site'], full=True)}
