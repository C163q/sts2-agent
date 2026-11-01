"""Project validated selection details without changing native input or state."""
from sts2_mcp.output.card_summary import card_summary


SELECTION_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'summary'], 'default': 'full',
                   'description': 'full keeps card descriptions and hover help; summary uses hand-summary fields for every candidate, bundle and preview card. Selection instructions and buttons remain.'},
    },
    'additionalProperties': False,
}


def selection_inspection_arguments(arguments):
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset'}:
        raise ValueError('Invalid selection inspection arguments.')
    preset = arguments.get('preset', 'full')
    if not isinstance(preset, str) or preset not in ('full', 'summary'):
        raise ValueError('Invalid selection inspection preset.')
    return preset


def selection_preset(payload, preset):
    if 'error' in payload or preset == 'full':
        return payload
    choice = {**payload['selection'], 'cards': [card_summary(card) for card in payload['selection']['cards']]}
    if 'bundles' in choice:
        choice['bundles'] = [{**bundle, 'cards': [card_summary(card) for card in bundle['cards']]}
                             for bundle in choice['bundles']]

    def preview(pair):
        return {**pair, **{side: None if pair[side] is None else card_summary(pair[side])
                          for side in ('before', 'after')}}

    if choice.get('upgrade_preview') is not None:
        choice['upgrade_preview'] = preview(choice['upgrade_preview'])
    for field in ('upgrade_previews', 'enchant_previews', 'transform_previews'):
        if field in choice:
            choice[field] = [preview(pair) for pair in choice[field]]
    result = {**payload, 'selection': choice}
    result.pop('hover_tips', None)
    return result
