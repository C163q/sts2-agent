from sts2_mcp.output.contracts.map import MAP_SUMMARY
from sts2_mcp.output.value_shapes import project
from sts2_mcp.output.scene_context import scene_context
import re




NODE_TYPES = ("ancient", "boss", "monster", "elite", "shop", "treasure", "rest_site", "unknown", "unrecognized")
REVEALED_TYPES = ("monster", "elite", "shop", "treasure", "rest_site")
NODE_ID = re.compile(r'map:([1-9][0-9]*):(0|[1-9][0-9]*):(0|[1-9][0-9]*)')
MAP_SCHEMA = {
    'type': 'object',
    'properties': {
        'preset': {'type': 'string', 'enum': ['full', 'selectable'], 'default': 'full',
                   'description': 'full returns the map graph and route context; selectable returns only current candidates with node details, omitting links and visited_path. selectable overrides max_steps.'},
        'max_steps': {'type': 'integer', 'minimum': 0, 'maximum': 2147483647, 'default': 0,
                      'description': '0 keeps the entire graph. Positive N keeps the current node and nodes within N drawn directed links, clipping links at the boundary. Before first entry, the lowest row counts as step 1. Route context and native selectable IDs stay unfiltered; off-link flight choices are not added to the subgraph.'},
    },
    'additionalProperties': False,
}


def valid_node_id(value, act=None):
    match = NODE_ID.fullmatch(value) if isinstance(value, str) else None
    return bool(match and all(len(v) <= 10 and int(v) <= 2147483647 for v in match.groups())
                and (act is None or int(match[1]) == act))


def travel_arguments(arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'node_id'}
            or not valid_node_id(arguments['node_id'])):
        raise ValueError('A canonical map node_id is required.')
    return {'node_id': arguments['node_id']}


TRAVEL_SCHEMA = {'type': 'object', 'properties': {'node_id': {
    'type': 'string', 'description': 'An exact node ID from the current map.selectable_nodes; not an arbitrary connected or visited node.',
}},
                 'required': ['node_id'], 'additionalProperties': False}


def map_summary(value):
    result = project(value, MAP_SUMMARY)
    if (set(result) != set(MAP_SUMMARY) or result['status'] != 'visible'
            or not 1 <= result['act'] <= 2147483647
            or result['current_node'] is not None and not valid_node_id(result['current_node'], result['act'])
            or any(not valid_node_id(i, result['act']) for i in result['selectable_nodes'])
            or len(set(result['selectable_nodes'])) != len(result['selectable_nodes'])
            or result['can_travel'] != bool(result['selectable_nodes'])):
        raise ValueError('Invalid map summary.')
    return result


def map_arguments(arguments):
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict) or set(arguments) - {'preset', 'max_steps'}:
        raise ValueError('Invalid map arguments.')
    preset = arguments.get('preset', 'full')
    steps = arguments.get('max_steps', 0)
    if not isinstance(preset, str) or preset not in ('full', 'selectable') \
            or type(steps) is not int or not 0 <= steps <= 2147483647:
        raise ValueError('Invalid map preset or step limit.')
    return {'preset': preset, 'max_steps': steps}


def map_preset(payload, preset, max_steps):
    if 'error' in payload or preset == 'full' and max_steps == 0:
        return payload
    if preset == 'selectable':
        choices = set(payload['selectable_nodes'])
        return {**{key: payload[key] for key in ('scene', 'screen', 'act', 'current_node', 'can_travel', 'selectable_nodes')},
                'preset': preset, 'nodes': [{key: value for key, value in node.items() if key != 'next'}
                                          for node in payload['nodes'] if node['id'] in choices]}
    nodes = {node['id']: node for node in payload['nodes']}
    if payload['current_node'] is not None:
        included = {payload['current_node']}
        remaining = max_steps
    else:
        first_row = min(node['row'] for node in nodes.values())
        included = {node['id'] for node in nodes.values() if node['row'] == first_row}
        remaining = max_steps - 1
    frontier = included
    while frontier and remaining > 0:
        frontier = {child for parent in frontier for child in nodes[parent]['next']} - included
        included.update(frontier)
        remaining -= 1
    return {**payload, 'max_steps': max_steps,
            'nodes': [{**node, 'next': [child for child in node['next'] if child in included]}
                      for node in payload['nodes'] if node['id'] in included]}


def identifiers(values, known):
    if (not isinstance(values, list) or any(not isinstance(value, str) or value not in known for value in values)
            or len(values) != len(set(values))):
        raise ValueError("Invalid map node references.")
    return list(values)


def map_details(state):
    context = scene_context(state)
    screen = context["screen"]
    act = state["act"]
    if (not isinstance(screen, dict)
            or screen.get("status") != "visible" or screen.get("view") != "map"
            or type(act) is not int or act < 1 or type(state["can_travel"]) is not bool
            or not isinstance(state["nodes"], list) or not state["nodes"]):
        raise ValueError("Invalid map details.")
    nodes = []
    for node in state["nodes"]:
        if (not isinstance(node, dict) or type(node["row"]) is not int or node["row"] < 0
                or type(node["column"]) is not int or node["column"] < 0
                or node["id"] != f"map:{act}:{node['row']}:{node['column']}" or node["type"] not in NODE_TYPES):
            raise ValueError("Invalid map node.")
        result = {key: node[key] for key in ("id", "row", "column", "type")}
        if node["type"] in ("ancient", "boss") and "name" in node:
            if not isinstance(node["name"], str) or not node["name"].strip():
                raise ValueError("Invalid map node name.")
            result["name"] = node["name"]
        if "revealed_type" in node:
            if node["type"] != "unknown" or node["revealed_type"] not in REVEALED_TYPES:
                raise ValueError("Invalid revealed map icon.")
            result["revealed_type"] = node["revealed_type"]
        if "marked" in node:
            if node["marked"] is not True:
                raise ValueError("Invalid map marker.")
            result["marked"] = True
        nodes.append(result)
    known = {node["id"] for node in nodes}
    if len(known) != len(nodes):
        raise ValueError("Duplicate map node IDs.")
    for raw, projected in zip(state["nodes"], nodes):
        projected["next"] = identifiers(raw["next"], known)
    visited = identifiers(state["visited_path"], known)
    current = state["current_node"]
    if current != (visited[-1] if visited else None):
        raise ValueError("Invalid current map node.")
    choices = identifiers(state["selectable_nodes"], known)
    if state["can_travel"] != bool(choices):
        raise ValueError("Invalid map travel availability.")
    return {**context, "act": act,
            "current_node": current, "visited_path": visited, "can_travel": state["can_travel"],
            "selectable_nodes": choices, "nodes": nodes}
