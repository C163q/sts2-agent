"""Keep the same compact card fields across dedicated inspection tools."""

SUMMARY_FIELDS = frozenset({'id', 'name', 'type', 'energy_cost', 'star_cost',
                            'energy_cost_color', 'star_cost_color', 'unplayable_markers', 'outline', 'enchantment'})


def card_summary(card):
    return {key: value for key, value in card.items() if key in SUMMARY_FIELDS
            and not (key == 'star_cost' and value is None)}
