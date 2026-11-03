"""Decode native successes once, independently of permission and output presets."""
from sts2_mcp.output.contracts.observation import OBSERVATION
from sts2_mcp.output.inspection_details import inspection_details
from sts2_mcp.output.observation_details import observation_details
from sts2_mcp.output.public_output import assemble_details


def decode_success(operation, state, native_arguments=None, *, include_observation=False):
    if not isinstance(state, dict):
        raise ValueError('Expected a native state object.')
    details = inspection_details(operation, state, native_arguments)
    if include_observation and set(OBSERVATION) <= state.keys():
        # File clients historically retain a complete native observation, even on actions/page closes.
        # Domain-specific details override the base view (for example inspected shop card effects).
        details = {**observation_details(state), **details}
    return assemble_details(details, operation=operation)
