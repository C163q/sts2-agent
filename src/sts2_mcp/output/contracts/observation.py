"""Base observation contracts and optional domain sections."""
from sts2_mcp.output.value_shapes import nullable, NUMBER, TEXT
from sts2_mcp.output.contracts.combat import PLAYER, ENEMY, ALLY
from sts2_mcp.output.contracts.ui import SCREEN, TOP_BAR
from sts2_mcp.output.contracts.selection import SELECTION_OUTPUT
from sts2_mcp.output.contracts.rooms import REWARDS, REST_SITE, TREASURE, SHOP, ANCIENT, ROOM_EVENT, DIVINATION, CONFIRMATION
from sts2_mcp.output.contracts.map import MAP_SUMMARY
from sts2_mcp.output.contracts.endings import RESULT, EPILOGUE


OBSERVATION = {
    "scene": str, "screen": SCREEN, "turn": NUMBER, "player": nullable(PLAYER),
    "enemies": nullable([ENEMY]), "top_bar": nullable(TOP_BAR),
    "buttons": nullable({"end_turn": nullable({"text": TEXT, "enabled": bool})}),
    "available_actions": [str],
}
OPTIONAL_OBSERVATION = {'allies': nullable([ALLY]), 'run_result': nullable(RESULT), 'epilogue': nullable(EPILOGUE), 'map': nullable(MAP_SUMMARY), 'confirmation': nullable(CONFIRMATION), 'divination': nullable(DIVINATION), "event": nullable(ROOM_EVENT), "ancient": nullable(ANCIENT),"selection": nullable(SELECTION_OUTPUT), 'rewards': nullable(REWARDS), 'rest_site': nullable(REST_SITE), 'treasure': nullable(TREASURE), 'shop': nullable(SHOP)}
