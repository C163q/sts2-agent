"""Keep public rejection reasons separate from private execution diagnostics."""


MESSAGES = {
    'stale_state': ('The observation is outdated. Read the current state before choosing an action.', 'get_state'),
    'illegal_action': ('The requested action is unavailable.', 'get_state'),
    'invalid_request': ('The request arguments are invalid. Correct them before submitting again.', 'correct_request'),
    'expired_request': ('The request expired before execution; no action was submitted.', 'get_state'),
    'timeout': ('The request timed out; execution outcome is unknown. Read the current state and do not retry the action automatically.', 'get_state'),
    'game_error': ('The game could not complete the request; execution outcome is unknown. Read the current state and do not retry the action automatically.', 'get_state'),
    'transport_error': ('The local game connection failed. Check the connection before reading the current state.', 'check_connection'),
    'screenshot_unavailable': ('The game viewport cannot be captured. Use a running graphical game instance.', 'check_game_window'),
    'file_exists': ('That screenshot filename already exists. Choose another filename; existing files are never overwritten.', 'change_filename'),
    'screenshot_save_failed': ('The screenshot could not be saved. Check the configured directory, permissions and free space.', 'check_screenshot_directory'),
}
KNOWN_OUTCOME = {'stale_state', 'illegal_action', 'invalid_request', 'expired_request',
                 'screenshot_unavailable', 'file_exists', 'screenshot_save_failed'}


def error_result(error):
    code = error['code']
    message, recovery = MESSAGES.get(code, (
        'The request failed; execution outcome is unknown. Read the current state and do not retry the action automatically.',
        'get_state'))
    # Only explicit adapter rejections opt in; exception messages remain private.
    if (code in {'illegal_action', 'invalid_request'}
            and isinstance(error.get('public_message'), str) and error['public_message'].strip()):
        message = error['public_message']
    result = {'code': code, 'message': message, 'recovery': recovery}
    if code not in KNOWN_OUTCOME:
        result['outcome'] = 'unknown'
    return {'error': result}


def invalid_request(message):
    return {'error': {'code': 'invalid_request', 'message': message, 'recovery': 'correct_request'}}


def retained_rejection(payload):
    if payload['error']['code'] in {'illegal_action', 'expired_request'}:
        return {'error': {**payload['error'], 'recovery': 'choose_legal_action'}}
    return payload
