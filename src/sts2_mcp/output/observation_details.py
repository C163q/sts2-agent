from sts2_mcp.output.value_shapes import project
from sts2_mcp.output.contracts.observation import OBSERVATION, OPTIONAL_OBSERVATION
from sts2_mcp.output.contracts.combat import HEALTH
from sts2_mcp.output.scene_context import SCENES as OBSERVATION_SCENES, scene_context
from sts2_mcp.output.available_tools import public_tools
from sts2_mcp.output.card_format import format_game_cards
from sts2_mcp.output.combat_fields import validate_identities, blade_refs, orb_slots
from sts2_mcp.output.selection_details import selection_details


def observation_details(state):
    result = project(state, {**OBSERVATION, **OPTIONAL_OBSERVATION})
    if (not set(OBSERVATION) <= result.keys() or "status" not in result["screen"]
            or result["scene"] not in OBSERVATION_SCENES
            or result["screen"]["status"] not in ("visible", "covered", "hidden", "not_ready", "not_applicable")):
        raise ValueError("Invalid observation structure.")
    result.update(scene_context(state))
    from sts2_mcp.output.deck_details import deck_observation
    result.update(deck_observation(state))
    from sts2_mcp.output.pile_details import pile_observation
    result.update(pile_observation(state))
    result['available_actions'] = public_tools(result['available_actions'])
    count = (result.get('top_bar') or {}).get('relic_count')
    if count is not None and count < 0:
        raise ValueError('Invalid relic count.')
    if result['player'] is not None and 'orb_slots' in result['player']:
        result['player']['orb_slots'] = orb_slots(result['player']['orb_slots'])
    if result['player'] is not None and 'sovereign_blades' in result['player']:
        result['player']['sovereign_blades'] = blade_refs(result['player']['sovereign_blades'])
    if result.get('allies') is not None:
        validate_identities(result['allies'], 4294967295)
        for ally in result['allies']:
            if not {'id', 'name', *HEALTH, 'powers'} <= ally.keys() or ally.get('block_shared_with', 'player') != 'player':
                raise ValueError('Invalid public ally.')
    if result.get('map') is not None:
        from sts2_mcp.output.map_details import map_observation
        result['map'] = map_observation(state['map'], scene_context(state),
            require_graph=state.get('schema_version', 0) >= 41)
        map_tools = {'travel_to_node', 'inspect_map', 'close_map', 'inspect_deck', 'inspect_relics', 'inspect_potions', 'inspect_ui'}
        if result['scene'] != 'combat':
            map_tools |= {'inspect_targets', 'use_potion', 'discard_potion'}
        if (result['screen'] != {'status': 'covered', 'view': 'map'}
                or any(a not in map_tools for a in result['available_actions'])
                or ('travel_to_node' in result['available_actions']) != result['map']['can_travel']):
            raise ValueError('Map is not the exposed action screen.')
    # During native travel the map page can still be identified without a readable summary.
    elif 'travel_to_node' in result['available_actions'] or result['screen'] == {'status': 'visible', 'view': 'map'}:
        raise ValueError('Missing map summary.')
    if result.get("selection") is not None:
        result["selection"] = selection_details(result["selection"])
    if result.get('rewards') is not None:
        from sts2_mcp.output.reward_details import rewards_details
        result['rewards'] = rewards_details(result['rewards'])
    elif result['scene'] == 'rewards':
        raise ValueError('Missing rewards state.')
    if result.get('rest_site') is not None:
        from sts2_mcp.output.rest_site_details import rest_site_summary
        result['rest_site'] = rest_site_summary(result['rest_site'])
    elif result['scene'] == 'rest_site':
        raise ValueError('Missing rest site state.')
    if result.get('treasure') is not None:
        from sts2_mcp.output.treasure_details import treasure_details
        result['treasure'] = treasure_details(result['treasure'])
    elif result['scene'] == 'treasure':
        raise ValueError('Missing treasure state.')
    if result.get('shop') is not None:
        from sts2_mcp.output.shop_details import shop_details
        result['shop'] = shop_details(result['shop'])
    elif result['scene'] == 'shop':
        raise ValueError('Missing shop state.')
    if result.get('ancient') is not None:
        from sts2_mcp.output.ancient_details import ancient_details
        result['ancient'] = ancient_details(result['ancient'])
    elif result['scene'] == 'ancient':
        raise ValueError('Missing ancient state.')
    if result.get('event') is not None:
        from sts2_mcp.output.event_details import event_details
        result['event'] = event_details(result['event'])
    elif result['scene'] == 'event':
        raise ValueError('Missing event state.')
    if result.get('divination') is not None:
        from sts2_mcp.output.divination_details import divination_details
        result['divination'] = divination_details(result['divination'])
        if result['divination']['status'] == 'visible' and (result['scene'] != 'event'
                or result['screen'] != {'status': 'visible', 'view': 'divination'}
                or (result.get('event') or {}).get('status') != 'covered'):
            raise ValueError('Divination is not the exposed screen.')
    if result['screen'].get('view') == 'divination' and result.get('divination') is None:
        raise ValueError('Missing divination state.')
    if result.get('confirmation') is not None:
        from sts2_mcp.output.confirmation_details import confirmation_details
        result['confirmation'] = confirmation_details(result['confirmation'])
        if (result['scene'] != 'event' or result['screen'] != {'status': 'visible', 'view': 'confirmation'}
                or (result.get('event') or {}).get('status') != 'covered'
                or any(action != 'respond_to_confirmation' for action in result['available_actions'])
                or any(result.get(key) is not None for key in ('turn', 'player', 'enemies', 'top_bar', 'buttons',
                                                              'selection', 'rewards', 'rest_site', 'treasure', 'shop', 'ancient', 'divination'))
                or result['available_actions'] and not any(option['enabled'] for option in result['confirmation']['options'])):
            raise ValueError('Confirmation is not the exposed screen.')
    elif ('respond_to_confirmation' in result['available_actions']
          or result['screen'] == {'status': 'visible', 'view': 'confirmation'}):
        raise ValueError('Missing event confirmation.')
    from sts2_mcp.output.run_ending_details import validate_ending
    return format_game_cards(validate_ending(result), shop_mode="face_full", deck_mode='face_full', pile_mode='face_full')
