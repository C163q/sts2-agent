from sts2_mcp.output.contracts.cards import CARD_FACE, CARD_FULL, BROWSED_CARD
"""Fixed card content modes; visibility is decided by the native page reader."""
from sts2_mcp.output.value_shapes import project
from sts2_mcp.output.card_summary import card_summary as compact_card



def format_card(card, mode, *, path=()):
    if mode not in {'face_full', 'face_default', 'full', 'default', 'summary'}:
        raise ValueError('Invalid internal card mode.')
    result = project(card, {**CARD_FULL, 'id': frozenset({int, str})})
    if mode.startswith('face_'):
        result.pop('description', None)
        result.pop('hover_tips', None)
    elif mode == 'summary':
        result = compact_card(result)
    if mode in {'default', 'face_default'}:
        from sts2_mcp.output.null_fields import apply_preset
        result = apply_preset(result, 'default', path=path)
    return result


def format_game_cards(payload, *, shop_mode="face_full", deck_mode='full'):
    """Route validated page card objects, keeping references and choice metadata separate."""
    def cards(items, mode):
        return None if items is None else [format_card(card, mode) for card in items]

    player = payload.get('player')
    if player is not None and 'hand' in player:
        player['hand'] = cards(player['hand'], 'face_full')
    if payload.get('hand') is not None:
        payload['hand'] = cards(payload['hand'], 'full')
    if payload.get('deck') is not None:
        payload['deck'] = cards(payload['deck'], deck_mode)
    if payload.get('cards') is not None:
        payload['cards'] = cards(payload['cards'], 'full')
    selection = payload.get('selection')
    if selection is not None:
        def candidates(items):
            return [format_card(card, 'full') for card in items]
        if selection.get('cards') is not None:
            selection['cards'] = candidates(selection['cards'])
        for bundle in selection.get('bundles', []):
            bundle['cards'] = candidates(bundle['cards'])
        pairs = [selection['upgrade_preview']] if selection.get('upgrade_preview') is not None else []
        for key in ('upgrade_previews', 'enchant_previews', 'transform_previews'):
            pairs.extend(selection.get(key, []))
        for pair in pairs:
            for side in ('before', 'after'):
                if pair[side] is not None:
                    pair[side] = format_card(pair[side], 'full')
    if payload.get('run_result') is not None:
        payload['run_result']['cards'] = cards(payload['run_result']['cards'], 'full')
    for item in (payload.get('shop') or {}).get('items') or []:
        if item['kind'] == 'card':
            item['card'] = format_card(item['card'], shop_mode)
    return payload


def browse_preset(payload, preset):
    if 'error' in payload or preset == 'full':
        return payload
    result = dict(payload)
    for key in ('deck', 'cards'):
        if result.get(key) is not None:
            result[key] = [format_card(card, 'summary') for card in result[key]]
    result.pop('hover_tips', None)
    return result


def card_summary(card):
    return format_card(card, "summary")
