"""Compatibility projection for callers without an explicit native response contract."""
from sts2_mcp.output.game_output import gameplay_fields
from sts2_mcp.output.error_output import error_result
from sts2_mcp.output.public_output import (
    CARD_VALUE_NOTE, ENEMY_ATTACK_INTENT_NOTE, assemble_details,
    share_hand_tips, share_indexed_tips, share_potion_tips,
)


def player_result(response, *, operation=None):
    if response['ok']:
        return assemble_details(gameplay_fields(response['state'], operation=operation), operation=operation)
    return error_result(response['error'])
