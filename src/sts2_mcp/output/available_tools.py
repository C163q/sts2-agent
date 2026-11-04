"""Public classifications derive from the tool registry, never from annotations."""
from sts2_mcp.tool_registry import SPECS

INSPECTIONS = frozenset(spec.name for spec in SPECS if spec.category == 'inspection')
VIEWS = frozenset(spec.name for spec in SPECS if spec.category == 'view')
GAME_ACTIONS = frozenset(spec.name for spec in SPECS if spec.returns_transition)
TOOLS_WITHOUT_PERMISSION = frozenset(spec.name for spec in SPECS if not spec.requires_permission)
PUBLIC_TOOLS = INSPECTIONS | VIEWS | GAME_ACTIONS


def public_tools(actions):
    return list(dict.fromkeys(action for action in actions if action in PUBLIC_TOOLS))
