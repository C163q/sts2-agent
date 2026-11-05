from sts2_mcp.output.value_shapes import project, TEXT
from sts2_mcp.output.scene_context import scene_context
from sts2_mcp.output.contracts.rooms import REST_SITE, REST_OPTION
from sts2_mcp.output.selection_details import OPTION_SCHEMA, selection_arguments


REST_OPTION_SCHEMA = {**OPTION_SCHEMA, 'properties': {'option_id': {
    **OPTION_SCHEMA['properties']['option_id'],
    'description': 'An enabled rest_site.options[].id from get_observation or inspect_rest_site.',
}}}


def rest_option_arguments(arguments):
    return selection_arguments('selection_option', arguments)


def rest_site_details(value, *, full=False):
    option_shape = {**REST_OPTION, 'description': TEXT} if full else REST_OPTION
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


def rest_site_summary(value):
    result = rest_site_details(value)
    result.pop('description')
    return result


def inspect_rest_site_details(state):
    context = scene_context(state)
    if context['scene'] != 'rest_site' or context['screen'] != {'status': 'visible'}:
        raise ValueError('Invalid rest site inspection context.')
    rest = rest_site_details(state['rest_site'], full=True)
    sources = state.get('unavailable_hover_sources', [])
    expected = ['rest_site.options.' + option['id'] for option in rest['options'] if option['description'] is None]
    if not isinstance(sources, list) or sources != expected:
        raise ValueError('Invalid or missing unavailable rest option hover evidence.')
    result = {**context, 'rest_site': rest}
    if sources: result['unavailable_hover_sources'] = list(sources)
    return result
