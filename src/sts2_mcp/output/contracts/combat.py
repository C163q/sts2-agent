"""Shared combat field shapes and constants; no runtime state reads."""
from sts2_mcp.output.value_shapes import nullable, TEXT, NUMBER
from sts2_mcp.output.contracts.cards import CARD_FACE as CARD


POWER = {"name": TEXT, "amount": NUMBER}
INTENT = {"category": TEXT, "value": TEXT}
HEALTH = {"hp": NUMBER, "max_hp": NUMBER, "hp_display": str, "block": NUMBER}
ORB = {"name": str, "passive": NUMBER, "evoke": NUMBER}
ORB_SLOTS = nullable([nullable(ORB)])
BLADE = {"id": int, "name": TEXT}
PLAYER = {
    **HEALTH, "character": TEXT, "energy": NUMBER, "max_energy": NUMBER, "stars": NUMBER,
    "powers": nullable([POWER]), "hand": nullable([CARD]),
    "orb_slots": ORB_SLOTS,
    "sovereign_blades": nullable([BLADE]),
    "draw_count": NUMBER, "discard_count": NUMBER, "exhaust_count": NUMBER,
}
ENEMY = {
    **HEALTH, "id": NUMBER, "name": TEXT, "powers": nullable([POWER]),
    "intents": nullable([INTENT]),
}
ALLY = {**HEALTH, "id": int, "name": TEXT, "powers": nullable([POWER]), "block_shared_with": str}
