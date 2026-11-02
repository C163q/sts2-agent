"""Shared summary fields for an already normalized, readable top bar."""


def top_bar_summary(top_bar):
    return {key: value for key, value in top_bar.items()
            if key in {'gold', 'potion_slots', 'deck_count', 'relic_count'}}
