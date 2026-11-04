def relic_details(state, arguments=None):
    summary = (arguments or {}).get("level") == "summary"
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
                or relic["description"] is not None and not isinstance(relic["description"], str)
                or not isinstance(relic["hover_tips"], list)):
            raise ValueError("Invalid relic details.")
        details.append({"name": relic["name"], "counter": relic["counter"], "description": relic["description"],
                        "hover_tips": [tip_text(tip) for tip in relic["hover_tips"]]})
        for field in ('melted', 'grayed_out', 'pulsing'):
            if field in relic:
                if relic[field] is not None and type(relic[field]) is not bool:
                    raise ValueError(f'Invalid visible relic {field} state.')
                details[-1][field] = relic[field]
    if any(relic['description'] is None and relic['hover_tips'] for relic in details):
        raise ValueError('Hover tips require a readable relic description.')
    result = {"relics": details}
    sources = state.get('unavailable_hover_sources', [])
    if (not isinstance(sources, list) or any(not isinstance(source, str) for source in sources)
            or len(set(sources)) != len(sources)):
        raise ValueError('Invalid unavailable relic hover sources.')
    allowed = {f'relics.{index}' for index, relic in enumerate(details)
               if relic['description'] is None and not relic['hover_tips']}
    if any(source not in allowed for source in sources):
        raise ValueError('Invalid unavailable relic hover source.')
    if not summary and allowed != set(sources):
        raise ValueError('Missing unavailable relic hover evidence.')
    if sources: result['unavailable_hover_sources'] = list(sources)
    return result
