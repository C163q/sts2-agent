"""Page-close response adapters, above room readers."""
from sts2_mcp.output.observation_details import observation_details
from sts2_mcp.output.scene_context import scene_context


def legacy_view_observation(state):
    """Keep the file close_deck and map adapter contracts separate from card closes."""
    from sts2_mcp.output.contracts.observation import OBSERVATION
    from sts2_mcp.output.value_shapes import project
    from sts2_mcp.output.card_format import format_game_cards
    result = {**scene_context(state), **{key: state[key] for key in
        ('turn', 'player', 'enemies', 'top_bar', 'buttons', 'available_actions')}}
    if not isinstance(result['available_actions'], list) or any(type(x) is not str for x in result['available_actions']):
        raise ValueError('Invalid view close observation.')
    return format_game_cards(project(result, OBSERVATION))


def closed_map(state):
    result = legacy_view_observation(state)
    if result['screen'].get('view') in {'divination', 'epilogue'}:
        return observation_details(state)
    if "view" in result["screen"]:
        raise ValueError("Map close left a browsing page open.")
    return result
