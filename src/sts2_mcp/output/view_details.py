"""Page-close response adapters, above room readers."""
from sts2_mcp.output.observation_details import observation_details
from sts2_mcp.output.scene_context import scene_context


def legacy_view_observation(state):
    """Keep the legacy file-only close_deck contract separate from public closes."""
    from sts2_mcp.output.contracts.observation import OBSERVATION
    from sts2_mcp.output.value_shapes import project
    from sts2_mcp.output.card_format import format_game_cards
    result = {**scene_context(state), **{key: state[key] for key in
        ('turn', 'player', 'enemies', 'top_bar', 'buttons', 'available_actions')}}
    if not isinstance(result['available_actions'], list) or any(type(x) is not str for x in result['available_actions']):
        raise ValueError('Invalid view close observation.')
    return format_game_cards(project(result, OBSERVATION))


def closed_map(state):
    result = observation_details(state)
    if result['screen'].get('view') not in (None, 'divination', 'epilogue') or result.get('map') is not None:
        raise ValueError("Map close left a browsing page open.")
    return result
