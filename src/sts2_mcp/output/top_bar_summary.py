"""Shared summary fields for an already normalized, readable top bar."""
from sts2_mcp.output.contracts.ui import TOP_BAR
from sts2_mcp.output.value_shapes import project

SUMMARY_FIELDS = frozenset({'gold', 'potion_slots', 'deck_count', 'relic_count'})


def top_bar_summary(top_bar):
    return {key: value for key, value in top_bar.items()
            if key in SUMMARY_FIELDS}


def top_bar_details(value, *, complete=False):
    if value is None: return None
    result = project(value, {key: TOP_BAR[key] for key in SUMMARY_FIELDS})
    if complete and set(result) != SUMMARY_FIELDS:
        raise ValueError('Incomplete purchasing top bar.')
    if any(value is not None and value < 0 for key, value in result.items() if key != 'potion_slots'):
        raise ValueError('Invalid purchasing top bar count.')
    if any(slot is not None and 'name' not in slot for slot in result.get('potion_slots') or []):
        raise ValueError('Invalid purchasing potion slot.')
    return top_bar_summary(result)
