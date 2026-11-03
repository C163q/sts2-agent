"""Compact every selection card while preserving the native choice context."""
from sts2_mcp.output.card_format import card_summary


PREVIEW_LISTS = ('upgrade_previews', 'enchant_previews', 'transform_previews')


def selection_summary(selection):
    result = dict(selection)
    if result.get('cards') is not None:
        result['cards'] = [card_summary(card) for card in result['cards']]
    if 'bundles' in result:
        result['bundles'] = [{**bundle, 'cards': [card_summary(card) for card in bundle['cards']]}
                             for bundle in result['bundles']]

    def preview(pair):
        return {**pair, **{side: None if pair[side] is None else card_summary(pair[side])
                          for side in ('before', 'after')}}

    if result.get('upgrade_preview') is not None:
        result['upgrade_preview'] = preview(result['upgrade_preview'])
    for key in PREVIEW_LISTS:
        if key in result:
            result[key] = [preview(pair) for pair in result[key]]
    for key in ('bundles', *PREVIEW_LISTS):
        if result.get(key) == []:
            result.pop(key)
    return result
