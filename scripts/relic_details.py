def relic_details(state):
    def tip_text(tip):
        if (not isinstance(tip, dict)
                or (tip["title"] is not None and not isinstance(tip["title"], str))
                or not isinstance(tip["description"], str)):
            raise ValueError("Invalid relic hover tip.")
        return {"title": tip["title"], "description": tip["description"]}

    relics = state["relics"]
    if not isinstance(relics, list):
        raise ValueError("Invalid relic list.")
    details = []
    for relic in relics:
        if (not isinstance(relic, dict)
                or (relic["name"] is not None and not isinstance(relic["name"], str))
                or (relic["counter"] is not None and (type(relic["counter"]) is not int
                    or not -2147483648 <= relic["counter"] <= 2147483647))
                or not isinstance(relic["description"], str)
                or not isinstance(relic["hover_tips"], list)):
            raise ValueError("Invalid relic details.")
        details.append({"name": relic["name"], "counter": relic["counter"], "description": relic["description"],
                        "hover_tips": [tip_text(tip) for tip in relic["hover_tips"]]})
        if 'melted' in relic:
            if relic['melted'] is not None and type(relic['melted']) is not bool:
                raise ValueError('Invalid visible melted state.')
            details[-1]['melted'] = relic['melted']
    return {"relics": details}
