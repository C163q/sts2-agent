from deck_details import closed_card_view


NODE_TYPES = ("ancient", "boss", "monster", "elite", "shop", "treasure", "rest_site", "unknown", "unrecognized")
REVEALED_TYPES = ("monster", "elite", "shop", "treasure", "rest_site")


def map_arguments(arguments):
    if arguments is not None and (not isinstance(arguments, dict) or arguments):
        raise ValueError("Map tools do not accept arguments.")


def identifiers(values, known):
    if (not isinstance(values, list) or any(not isinstance(value, str) or value not in known for value in values)
            or len(values) != len(set(values))):
        raise ValueError("Invalid map node references.")
    return list(values)


def map_details(state):
    screen = state["screen"]
    act = state["act"]
    if (state["scene"] != "map" or not isinstance(screen, dict)
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
    return {"scene": "map", "screen": {"status": "visible", "view": "map"}, "act": act,
            "current_node": current, "visited_path": visited, "can_travel": state["can_travel"],
            "selectable_nodes": choices, "nodes": nodes}


def closed_map(state):
    result = closed_card_view(state)
    if result['screen'].get('view') == 'divination':
        from game_output import observation_details
        return observation_details(state)
    if "view" in result["screen"]:
        raise ValueError("Map close left a browsing page open.")
    return result
