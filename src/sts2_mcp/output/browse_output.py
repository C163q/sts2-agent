"""File-client card browsing adapter; card formatting stays independent."""
from sts2_mcp.output.card_format import browse_preset
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.output.error_output import error_result
from sts2_mcp.output.null_fields import apply_preset


def browse_result(response, operation, arguments=None, preset='default'):
    if not response['ok']:
        return error_result(response['error'])
    payload = decode_success(operation, response['state'], arguments, include_observation=True)
    payload = browse_preset(payload, 'summary' if preset == 'summary' else 'full')
    return apply_preset(payload, 'full' if preset == 'full' else 'default')
