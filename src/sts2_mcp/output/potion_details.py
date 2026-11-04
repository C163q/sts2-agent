def potion_details(state, arguments=None):
    summary = (arguments or {}).get("level") == "summary"
    def tip_text(tip):
        if (not isinstance(tip, dict)
                or (tip["title"] is not None and not isinstance(tip["title"], str))
                or not isinstance(tip["description"], str)):
            raise ValueError("Invalid potion hover tip.")
        return {"title": tip["title"], "description": tip["description"]}

    common = None if summary and state["slot_tip"] is None else tip_text(state["slot_tip"])
    slots = state["potion_slots"]
    if not isinstance(slots, list):
        raise ValueError("Invalid potion slots.")
    potions = []
    for potion in slots:
        if potion is None:
            potions.append(None)
            continue
        if (not isinstance(potion, dict)
                or (potion["name"] is not None and not isinstance(potion["name"], str))
                or potion["description"] is not None and not isinstance(potion["description"], str)
                or not isinstance(potion["hover_tips"], list)):
            raise ValueError("Invalid potion details.")
        potions.append({"name": potion["name"], "description": potion["description"],
                        "hover_tips": [tip_text(tip) for tip in potion["hover_tips"]]})
        for field in ('bouncing', 'usable_here'):
            if field in potion:
                if type(potion[field]) is not bool:
                    raise ValueError('Invalid visible potion flag.')
                potions[-1][field] = potion[field]
    if any(slot is not None and slot['description'] is None and slot['hover_tips'] for slot in potions):
        raise ValueError('Hover tips require a readable potion description.')
    sources = state.get('unavailable_hover_sources', [])
    if (not isinstance(sources, list) or any(not isinstance(source, str) for source in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError('Invalid unavailable potion hover sources.')
    allowed = {f'potion_slots.{index}' for index, slot in enumerate(potions)
               if slot is not None and slot['description'] is None and not slot['hover_tips']}
    if any(source not in allowed for source in sources) or not summary and set(sources) != allowed:
        raise ValueError('Invalid or missing unavailable potion hover evidence.')
    result = {"slot_tip": common, "potion_slots": potions}
    if sources: result['unavailable_hover_sources'] = list(sources)
    return result
