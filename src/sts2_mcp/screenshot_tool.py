from sts2_mcp.output.media import png_data as _png_data, MAX_PNG_BYTES, MAX_PIXELS
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


class ScreenshotError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


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
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.directory, prefix=".capture-", delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            # Publish a complete file without replacing an existing file or symlink.
            try:
                os.link(temporary, target)
            except FileExistsError as error:
                raise ScreenshotError("file_exists") from error
        except OSError as error:
            raise ScreenshotError("screenshot_save_failed") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return {"path": str(target), "width": width, "height": height}
