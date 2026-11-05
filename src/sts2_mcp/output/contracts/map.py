"""Shared map field shapes and constants; no runtime state reads."""

NODE_TYPES = ("ancient", "boss", "monster", "elite", "shop", "treasure", "rest_site", "unknown", "unrecognized")
MAP_CONTEXT = {'status': str, 'act': int, 'current_node': (str,), 'can_travel': bool, 'selectable_nodes': [str]}
MAP_SUMMARY = {**MAP_CONTEXT, 'nodes_by_type': {kind: [str] for kind in NODE_TYPES}}
