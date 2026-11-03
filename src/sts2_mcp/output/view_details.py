"""Page-close response adapters, above room readers."""
from sts2_mcp.output.deck_details import closed_card_view
from sts2_mcp.output.observation_details import observation_details


def closed_map(state):
    result = closed_card_view(state)
    if result['screen'].get('view') in {'divination', 'epilogue'}:
        return observation_details(state)
    if "view" in result["screen"]:
        raise ValueError("Map close left a browsing page open.")
    return result
