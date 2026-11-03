"""Shared endings field shapes and constants; no runtime state reads."""
from sts2_mcp.output.contracts.cards import BROWSED_CARD


OPTION = {'id': str, 'text': str, 'enabled': bool}
RESULT = {'status': str, 'phase': str, 'title': (str,), 'texts': [str],
          'score_lines': [{'label': str, 'value': str}], 'badges': [{'name': str, 'rarity': str}],
          'discoveries': [{'kind': str, 'count': int}], 'options': [OPTION],
          'cards': [BROWSED_CARD],
          'relics': [{'name': (str,)}], 'potions': [{'name': (str,)}]}
EPILOGUE = {'status': str, 'dialogue': ({'speaker': str, 'text': str},),
            'continue': ({'text': str, 'enabled': bool},), 'proceed': ({'text': str, 'enabled': bool},)}
PHASES = {'outcome', 'summary', 'history', 'leaderboard', 'timeline', 'epoch', 'unlock', 'tutorial'}
EPILOGUE_TOOLS = {'advance_dialogue', 'proceed', 'inspect_map', 'inspect_potions', 'inspect_targets',
                  'use_potion', 'discard_potion', 'inspect_ui', 'inspect_combatants', 'inspect_relics', 'inspect_deck'}
