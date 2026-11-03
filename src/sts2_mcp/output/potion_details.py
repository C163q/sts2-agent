def potion_details(state):
    def tip_text(tip):
        if (not isinstance(tip, dict)
                or (tip["title"] is not None and not isinstance(tip["title"], str))
                or not isinstance(tip["description"], str)):
            raise ValueError("Invalid potion hover tip.")
        return {"title": tip["title"], "description": tip["description"]}

    common = tip_text(state["slot_tip"])
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
                or not isinstance(potion["description"], str)
                or not isinstance(potion["hover_tips"], list)):
            raise ValueError("Invalid potion details.")
        potions.append({"name": potion["name"], "description": potion["description"],
                        "hover_tips": [tip_text(tip) for tip in potion["hover_tips"]]})
    return {"slot_tip": common, "potion_slots": potions}
