"""Project validated reward rows using stable IDs and the basic observation format."""
from sts2_mcp.output.filtering import optional_filter
from sts2_mcp.output.reward_details import rewards_details


REWARD_SCHEMA = {'type':'object', 'properties':{
    'preset':{'type':'string', 'enum':['full','summary'], 'default':'full',
              'description':'summary keeps static reward rows and the page button, omitting hover help.'},
    'reward_ids':{'type':['array','null'], 'items':{'type':'integer','minimum':0,'maximum':2147483647},
                  'description':'Reward IDs on the current page. Omit/null for all; [] for none. Results keep native order; missing IDs are grouped in errors.'}},
    'additionalProperties':False}


def reward_inspection_arguments(arguments):
    arguments = {} if arguments is None else arguments
    return {'preset':arguments.get('preset','full'),
            'reward_ids':optional_filter(arguments.get('reward_ids'),'reward_ids',integers=True)}


def reward_preset(payload, preset, reward_ids):
    if 'error' in payload or preset == 'full' and reward_ids is None:
        return payload
    rewards = rewards_details(payload['rewards']) if preset == 'summary' else dict(payload['rewards'])
    result = {**payload, 'rewards':rewards}
    if reward_ids is not None:
        known = {item['id'] for item in rewards['items']}
        selected = set(reward_ids)
        rewards['items'] = [item for item in rewards['items'] if item['id'] in selected]
        missing = [identifier for identifier in reward_ids if identifier not in known]
        if missing:
            result['errors'] = [{'code':'reward_ids_not_found','reward_ids':missing}]
    return result
