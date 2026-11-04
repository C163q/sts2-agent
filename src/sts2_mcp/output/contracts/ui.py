"""Shared ui field shapes and constants; no runtime state reads."""
from sts2_mcp.output.value_shapes import nullable, TEXT, NUMBER


RELIC = {"name": TEXT, "counter": NUMBER, "melted": nullable(bool),
         "grayed_out": nullable(bool), "pulsing": nullable(bool)}
TOP_BAR = {
    "hp": NUMBER, "max_hp": NUMBER,
    "gold": NUMBER, "floor": NUMBER, "ascension": NUMBER, "deck_count": NUMBER,
    "room_icon": TEXT, "bosses": [TEXT], "potion_slots": nullable([nullable({"name": TEXT, "usable_here": bool, "bouncing": bool})]),
    "relics": nullable([RELIC]), "relic_count": NUMBER,
    "map_visible": bool, "deck_visible": bool, "settings_visible": bool,
}
SCREEN = {"status": str, "view": str}
