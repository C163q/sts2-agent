"""Shared cards field shapes and constants; no runtime state reads."""
from sts2_mcp.output.value_shapes import nullable, TEXT, TIP


CARD_FACE = {
    "id": int, "name": TEXT, "type": TEXT, "rarity": TEXT, "visual_card_pool": TEXT,
    "energy_cost": TEXT, "star_cost": TEXT, "energy_cost_color": str, "star_cost_color": str,
    "unplayable_markers": [str], "outline": str,
    "enchantment": nullable({"name": TEXT, "amount": int, "dimmed": bool}),
    "affliction": nullable({"name": str}),
}
CARD_FULL = {**CARD_FACE, "description": TEXT, "hover_tips": nullable([TIP])}
BROWSED_CARD = {**CARD_FULL, "id": str}
