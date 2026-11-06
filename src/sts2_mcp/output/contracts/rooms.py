"""Shared rooms field shapes and constants; no runtime state reads."""
from sts2_mcp.output.value_shapes import nullable, TEXT, NUMBER
from sts2_mcp.output.contracts.cards import CARD_FACE as CARD


REWARD_ITEM = {'id': int, 'type': str, 'text': str, 'enabled': bool, 'linked_group': NUMBER}
REWARDS = {'status': str, 'title': TEXT, 'items': nullable([REWARD_ITEM]),
           'proceed': nullable({'text': str, 'enabled': bool, 'skips_remaining': bool})}
REST_OPTION = {'id': str, 'text': str, 'enabled': bool}
REST_SITE = {'status': str, 'prompt': TEXT, 'description': TEXT, 'options': nullable([REST_OPTION]),
             'proceed': nullable({'text': str, 'enabled': bool})}
TREASURE_RELIC = {'name': str, 'enabled': bool}
TREASURE = {'status': str, 'chest': TEXT, 'relic': nullable(TREASURE_RELIC),
            'proceed': nullable({'text': str, 'enabled': bool, 'skips_remaining': bool})}
SHOP_CARD = {key: shape for key, shape in CARD.items() if key != "id"}
SHOP_ITEM = {'id': int, 'kind': str, 'position': str, 'price': NUMBER, 'affordable': nullable(bool),
             'enabled': bool, 'name': str, 'used': bool, 'on_sale': bool, 'card': SHOP_CARD}
SHOP = {'status': str, 'view': TEXT, 'items': nullable([SHOP_ITEM]),
        'open': nullable({'enabled': bool}), 'back': nullable({'enabled': bool}),
        'proceed': nullable({'text': str, 'enabled': bool})}
ANCIENT_OPTION = {'id': int, 'title': str, 'description': str, 'enabled': bool}
ROOM_EVENT_OPTION = {**ANCIENT_OPTION, 'lethal_warning': bool}
ROOM_EVENT = {'status': str, 'name': TEXT, 'description': TEXT, 'options': nullable([ROOM_EVENT_OPTION]),
              'proceed': nullable({'text': str, 'enabled': bool})}
DIVINATION = {'status': str, 'phase': TEXT, 'remaining': NUMBER, 'tool': TEXT,
              'tools': nullable([{'id': str, 'text': str, 'enabled': bool}]),
              'instructions': nullable({'title': str, 'description': str}), 'dialogue': TEXT,
              'grid': nullable({'columns': int, 'rows': int, 'covered_rows': [str],
                                'image': {'width': int, 'height': int}}),
              'proceed': nullable({'text': str, 'enabled': bool})}
DIVINATION_TEXT_GRID = {'columns': int, 'rows': int, 'cell_rows': [str],
                       'visible_fragments': [{'x': int, 'y': int, 'appearance': str}],
                       'image': {'width': int, 'height': int}}
ANCIENT = {'status': str, 'name': TEXT, 'epithet': TEXT, 'description': TEXT, 'dialogue': nullable([{'speaker': str, 'text': str}]),
           'options': nullable([ANCIENT_OPTION]), 'continue': nullable({'text': TEXT, 'enabled': bool}),
           'proceed': nullable({'text': str, 'enabled': bool})}
CONFIRMATION = {'status': str, 'type': str, 'title': str, 'description': str,
                'options': [{'id': str, 'text': str, 'enabled': bool}]}
