"""Compact visible HUD counters without inventing missing values."""


def resource_summary(payload):
    result = {key: value for key, value in payload.items() if key not in {'energy', 'max_energy'}}
    energy, maximum = payload.get('energy'), payload.get('max_energy')
    if type(energy) is int and type(maximum) is int:
        result['energy'] = f'{energy}/{maximum}'
    return result
