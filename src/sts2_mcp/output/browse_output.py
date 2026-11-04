"""File-client card browsing adapter; card formatting stays independent."""
from sts2_mcp.output.response_pipeline import decode_success
from sts2_mcp.output.error_output import error_result


def browse_result(response, operation, arguments=None, preset='default'):
    if not response['ok']:
        return error_result(response['error'])
    from sts2_mcp.request_arguments import normalize_request
    from sts2_mcp.tool_registry import NATIVE_TOOLS
    request = normalize_request(NATIVE_TOOLS[operation], {**(arguments or {}), 'preset': preset})
    payload = decode_success(operation, response['state'], request.native_arguments, include_observation=True)
    return request.project(payload)
