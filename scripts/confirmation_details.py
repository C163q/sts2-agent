from game_output import CONFIRMATION, project


CONFIRMATION_SCHEMA = {'type': 'object', 'properties': {'option': {
    'type': 'string', 'enum': ['confirm', 'cancel'],
    'description': 'confirm abandons the run; cancel dismisses the Trial confirmation and returns to the event.',
}},
                       'required': ['option'], 'additionalProperties': False}


def confirmation_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'option'}
            or type(arguments['option']) is not str or arguments['option'] not in {'confirm', 'cancel'}):
        raise ValueError('Expected confirm or cancel.')
    return dict(arguments)


def confirmation_details(value):
    result = project(value, CONFIRMATION)
    if (set(result) != set(CONFIRMATION) or result['status'] != 'visible' or result['type'] != 'abandon_run'
            or not result['title'] or not result['description'] or len(result['options']) != 2
            or {option.get('id') for option in result['options']} != {'confirm', 'cancel'}
            or any(set(option) != {'id', 'text', 'enabled'} or not option['text'] for option in result['options'])):
        raise ValueError('Invalid event confirmation.')
    return result
