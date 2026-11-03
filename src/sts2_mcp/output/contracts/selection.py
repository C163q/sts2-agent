"""Shared selection field shapes and constants; no runtime state reads."""
from sts2_mcp.output.value_shapes import nullable, TEXT, NUMBER
from sts2_mcp.output.contracts.cards import CARD_FULL as HAND_CARD


SELECTION_CARD = HAND_CARD
SELECTION_OPTION = {"id": str, "text": TEXT, "enabled": bool}
UPGRADE_PREVIEW = {"before": SELECTION_CARD, "after": SELECTION_CARD}
SELECTION = {
    "type": str, "status": str, "prompt": TEXT, "min_select": NUMBER, "max_select": NUMBER,
    "selected_ids": nullable([int]), "cards": nullable([SELECTION_CARD]),
    "options": [SELECTION_OPTION], "can_view_battlefield": bool,
}
SELECTION_OUTPUT = {**SELECTION, 'can_view_upgrades': bool, 'view_upgrades': nullable(bool),
                    "enchantment": nullable({"title": str, "description": str}), "enchant_previews": [UPGRADE_PREVIEW],
                    "transform_previews": [{"before": SELECTION_CARD, "after": nullable(SELECTION_CARD), "random": bool}],
                    "bundles": [{"id": str, "cards": [SELECTION_CARD]}], "upgrade_preview": nullable(UPGRADE_PREVIEW), "upgrade_previews": [UPGRADE_PREVIEW]}
