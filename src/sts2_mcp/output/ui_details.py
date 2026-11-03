from sts2_mcp.output.scene_context import scene_context


def ui_details(state):
    context = scene_context(state)
    tips = state.get("hover_tips")
    if not isinstance(tips, list):
        raise ValueError("Invalid UI details.")
    for tip in tips:
        if (not isinstance(tip, dict)
                or (tip.get("title") is not None and not isinstance(tip["title"], str))
                or not isinstance(tip.get("description"), str)
                or not isinstance(tip.get("sources"), list) or not tip["sources"]
                or any(not isinstance(source, str) or not source for source in tip["sources"])):
            raise ValueError("Invalid UI hover tip.")
    return {**context, "hover_tips": [
        {key: tip[key] for key in ("title", "description", "sources")} for tip in tips]}
