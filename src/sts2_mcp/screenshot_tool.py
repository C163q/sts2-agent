from sts2_mcp.output.media import png_data as _png_data, MAX_PNG_BYTES, MAX_PIXELS
from sts2_mcp.output.error_output import error_result
import errno
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {"filename": {"type": "string", "minLength": 5, "maxLength": 128,
                                "description": "PNG filename only, e.g. 01-before.png. Omit for a unique name; existing files are never overwritten."}},
    "additionalProperties": False,
}


STORAGE_REASONS = {
    'not_directory': ('The configured screenshot directory or one of its parents is a file. Configure a directory and restart the MCP connection.', 'check_screenshot_directory'),
    'name_too_long': ('The screenshot filename or path is too long for this filesystem. Use a shorter filename or configured directory.', 'change_filename'),
    'directory_too_long': ('The configured screenshot directory path is too long for this filesystem. Shorten it in the MCP config and restart the connection.', 'check_screenshot_directory'),
    'permission': ('The MCP process lacks permission to save screenshots in this directory. Check directory permissions.', 'check_screenshot_directory'),
    'read_only': ('The screenshot directory is on a read-only filesystem. Choose a writable screenshot directory and restart the MCP connection.', 'check_screenshot_directory'),
    'space': ('There is not enough free space or quota to save the screenshot. Free space or choose another screenshot directory.', 'check_screenshot_directory'),
    'cleanup': ('The screenshot temporary file could not be removed; the target PNG may already exist. Check directory permissions before retrying.', 'check_screenshot_directory'),
}


def screenshots_disabled():
    return {'error': {'code': 'invalid_request',
        'message': 'Screenshot capture is disabled. Enable screenshots.enabled in the MCP config and restart the connection.',
        'recovery': 'check_configuration'}}


class ScreenshotError(Exception):
    def __init__(self, code, reason=None):
        super().__init__(code)
        self.code = code
        self.reason = reason

    @property
    def known_refusal(self):
        return self.code == 'file_exists' or self.code == 'screenshot_save_failed' and self.reason in STORAGE_REASONS and self.reason != 'cleanup'

    def public_result(self):
        result = error_result({'code': self.code})
        if self.code == 'screenshot_save_failed' and not self.known_refusal:
            result['error']['outcome'] = 'unknown'
        if self.code == 'screenshot_save_failed' and self.reason in STORAGE_REASONS:
            message, recovery = STORAGE_REASONS[self.reason]
            result['error'].update(message=message, recovery=recovery)
        return result


def storage_failure(error, stage):
    reason = None
    if error.errno == errno.ENOTDIR or stage == 'directory' and error.errno == errno.EEXIST:
        reason = 'not_directory'
    elif error.errno == errno.ENAMETOOLONG: reason = 'name_too_long' if stage == 'publish' else 'directory_too_long'
    elif error.errno in {errno.EACCES, errno.EPERM}: reason = 'permission'
    elif error.errno == errno.EROFS: reason = 'read_only'
    elif error.errno in {errno.ENOSPC, errno.EDQUOT}: reason = 'space'
    return ScreenshotError('screenshot_save_failed', reason)


def screenshot_arguments(arguments):
    if arguments is None:
        return {}
    if not isinstance(arguments, dict) or arguments.keys() - {"filename"}:
        raise ValueError("Invalid screenshot arguments.")
    if "filename" in arguments:
        name = arguments["filename"]
        if (not isinstance(name, str) or not 5 <= len(name) <= 128 or not name.endswith(".png")
                or any(character in name for character in ("/", "\\", "\0"))
                or any(ord(character) < 32 or ord(character) == 127 for character in name)):
            raise ValueError("Expected a PNG filename without directory components.")
    return dict(arguments)




class ScreenshotStore:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()

    def save(self, state, arguments):
        arguments = screenshot_arguments(arguments)
        data, width, height = _png_data(state)
        name = arguments.get("filename") or (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ-") + uuid.uuid4().hex[:8] + ".png")
        target = self.directory / name
        temporary = None
        stage = 'directory'
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            stage = 'write'
            with tempfile.NamedTemporaryFile(dir=self.directory, prefix=".capture-", delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            # Publish a complete file without replacing an existing file or symlink.
            stage = 'publish'
            try:
                os.link(temporary, target)
            except FileExistsError as error:
                raise ScreenshotError("file_exists") from error
        except OSError as error:
            raise storage_failure(error, stage) from error
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError as error:
                    raise ScreenshotError('screenshot_save_failed', 'cleanup') from error
        return {"path": str(target), "width": width, "height": height}
