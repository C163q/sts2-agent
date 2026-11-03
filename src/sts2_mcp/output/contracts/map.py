"""Shared map field shapes and constants; no runtime state reads."""


MAP_SUMMARY = {'status': str, 'act': int, 'current_node': (str,), 'can_travel': bool, 'selectable_nodes': [str]}
