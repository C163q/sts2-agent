from sts2_mcp.output.observation_details import observation_details
from sts2_mcp.output.value_shapes import project
from sts2_mcp.output.contracts.transition import TRANSITION
from sts2_mcp.output.available_tools import INSPECTIONS, VIEWS, TOOLS_WITHOUT_PERMISSION
from sts2_mcp.output.card_batch_output import card_plays, uncertain_card_plays


REASONS = {"player_ready", "choice_required", "combat_won", "combat_lost", "run_won", "run_lost", "timeout", "interrupted", "selection_resolved", "action_canceled", "action_completed", 'manual_input_required'}
FIELDS = {
    'combat_started': set(),
    'orb_channeled': {'target', 'orb', 'slot_index'},
    'orb_evoked': {'target', 'orb', 'slot_index'},
    'orb_removed': {'target', 'orb', 'slot_index'},
    'orb_slots_changed': {'target', 'before', 'after'},
    "damage": {"target", "hp_loss", "blocked"},
    "hp_changed": {"target", "before", "after"},
    "max_hp_changed": {"target", "before", "after"},
    "gold_changed": {"target", "before", "after"},
    "energy_changed": {"target", "before", "after"},
    "max_energy_changed": {"target", "before", "after"},
    "stars_changed": {"target", "before", "after"},
    "block_changed": {"target", "before", "after"},
    "power_changed": {"target", "name", "change", "before", "after"},
    "died": {"target"}, "revived": {"target"}, "creature_added": {"target"},
    "card_played": {"card", "autoplay"}, "card_drawn": {"card"},
    "card_discarded": {"card"}, "card_exhausted": {"card"},
    "card_selected": {"card"}, "card_deselected": {"card"},
    "card_added": {"card", "pile"},
    "card_moved": {"card", "from_pile", "to_pile"},
    "potion_used": {"potion"}, "potion_discarded": {"potion"},
    "potion_obtained": {"potion"},
    "relic_obtained": {"relic"}, "relic_removed": {"relic"}, "relic_melted": {"relic"},
    "card_removed": {"card", "pile"}, "card_upgraded": {"card", "pile"},
    "card_downgraded": {"card", "pile"}, "card_enchantment_changed": {"card", "pile"},
    "card_stats_changed": {"card", "pile"}, "card_energy_cost_changed": {"card", "pile"},
}


def end_turn_details(state):
    result = observation_details(state)
    transition = project(state["transition"], TRANSITION)
    if (set(transition) != set(TRANSITION) or transition["stop_reason"] not in REASONS
            or (transition["stop_reason"] in {"timeout", "interrupted"} and transition["complete"])):
        raise ValueError("Invalid turn transition.")
    previous = 0
    for event in transition["events"]:
        kind = event.get("type")
        if (kind not in FIELDS or not FIELDS[kind] <= event.keys()
                or event.get("sequence", 0) <= previous):
            raise ValueError("Invalid transition event.")
        previous = event["sequence"]
        if kind == 'combat_started' and set(event) != {'sequence', 'type'}:
            raise ValueError('Unexpected gameplay data in a combat boundary.')
        if kind in {'orb_channeled', 'orb_evoked', 'orb_removed', 'orb_slots_changed'}:
            if set(event) != {'sequence', 'type'} | FIELDS[kind] or event['target'].get('kind') != 'player':
                raise ValueError('Invalid public orb event fields.')
            if kind == 'orb_slots_changed':
                before, after = event['before'], event['after']
                if (type(before) is not int or type(after) is not int
                        or not 0 <= before <= 10 or not 0 <= after <= 10 or before == after):
                    raise ValueError('Invalid public orb capacity change.')
            elif set(event['orb']) != {'name'} or not event['orb']['name'] or not 0 <= event['slot_index'] < 10:
                raise ValueError('Invalid public orb identity or position.')
        if kind in {'card_stats_changed', 'card_energy_cost_changed', 'card_enchantment_changed'} and (
                set(event) != {'sequence', 'type', 'card', 'pile'}):
            raise ValueError('Unexpected fields in an identity-only card change.')
        if kind in {'card_selected', 'card_deselected'} and set(event) != {'sequence', 'type', 'card'}:
            raise ValueError('Unexpected fields in a selection change.')
        for key in ("actor", "target"):
            if key in event and (set(event[key]) != {"id", "kind", "name"}
                                or event[key]["kind"] not in {"player", "enemy", "ally"}):
                raise ValueError("Invalid event entity.")
        if event.get("source") is not None and (
                set(event["source"]) != {"kind", "name"}
                or event["source"]["kind"] not in {"card", "power", "relic", "potion"}):
            raise ValueError("Invalid event source.")
        if "card" in event and (set(event["card"]) != {"id", "name"} or event["card"]["id"] < 0):
            raise ValueError("Invalid event card.")
        if "potion" in event and (set(event["potion"]) != {"slot_index", "name"}
                                  or not 0 <= event["potion"]["slot_index"] <= 2147483647):
            raise ValueError("Invalid event potion.")
        if kind == 'card_moved':
            piles = {'hand', 'draw', 'discard', 'exhaust', 'play'}
            if (set(event) != {'sequence', 'type', 'card', 'from_pile', 'to_pile'}
                    or event['from_pile'] not in piles or event['to_pile'] not in piles
                    or event['from_pile'] == event['to_pile']):
                raise ValueError('Invalid public card movement.')
        if kind == 'card_added':
            if event['pile'] not in {None, 'deck', 'hand', 'draw', 'discard', 'exhaust', 'play'}:
                raise ValueError('Invalid public card destination.')
        elif 'pile' in event and (event['pile'] != 'deck' or kind not in {
                'card_removed', 'card_upgraded', 'card_downgraded', 'card_enchantment_changed',
                'card_stats_changed', 'card_energy_cost_changed'}):
            raise ValueError('Invalid permanent card scope.')
        if kind in {'card_removed', 'card_upgraded', 'card_downgraded', 'card_enchantment_changed',
                    'card_stats_changed', 'card_energy_cost_changed'} or event.get('pile') == 'deck':
            if not event['card']['name']:
                raise ValueError('Missing visible permanent card identity.')
        if kind in {'relic_obtained', 'relic_removed', 'relic_melted'} and (
                set(event['relic']) != {'name'} or not event['relic']['name']):
            raise ValueError('Invalid visible relic identity.')
        if kind == 'potion_obtained' and not event['potion']['name']:
            raise ValueError('Missing visible potion identity.')
        if any(event.get(key) is not None and event[key] < 0 for key in ("hp_loss", "blocked")):
            raise ValueError("Invalid event damage.")
        if kind in {"hp_changed", "block_changed"} and any(type(event[key]) is not int for key in ("before", "after")):
            raise ValueError("Invalid event values.")
        if kind in {'max_hp_changed', 'gold_changed', 'energy_changed', 'max_energy_changed', 'stars_changed'}:
            before, after = event['before'], event['after']
            allowed = {'player', 'ally'} if kind == 'max_hp_changed' else {'player'}
            if (event['target']['kind'] not in allowed or type(after) is not int or after < 0
                    or not (type(before) is int and before >= 0 or kind == 'stars_changed' and before is None)):
                raise ValueError('Invalid player resource change.')
        if kind == "power_changed" and event["change"] not in {"applied", "modified", "removed"}:
            raise ValueError("Invalid power change.")
    result["transition"] = transition
    if 'card_plays' in state:
        result['card_plays'] = card_plays(state['card_plays'])
        if transition['complete'] and transition['stop_reason'] in {'player_ready', 'action_completed'} \
                and any(row['status'] in {'queued', 'resolving'} for row in result['card_plays']['results']):
            raise ValueError('A ready action boundary cannot contain pending card plays.')
    uncertain = uncertain_card_plays(result)
    if transition["stop_reason"] not in {"player_ready", "action_completed"} or not transition["complete"] or uncertain:
        result["available_actions"] = [action for action in result["available_actions"]
            if action in (INSPECTIONS | VIEWS) & TOOLS_WITHOUT_PERMISSION or transition["complete"]
            and not uncertain and transition["stop_reason"] == "choice_required"
            and (result.get("selection") or {}).get("status") == "visible"
            and action in {"select_card", "selection_option", "discard_potion"}]
    return result
