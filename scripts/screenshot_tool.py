import base64
import binascii
import os
import struct
import tempfile
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path


SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {"filename": {"type": "string", "minLength": 5, "maxLength": 128,
                                "description": "PNG filename only, e.g. 01-before.png. Omit for a unique name; existing files are never overwritten."}},
    "additionalProperties": False,
}
MAX_PNG_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 16_777_216


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


def _png_data(state):
    width, height, encoded = state["width"], state["height"], state["png_base64"]
    if (type(width) is not int or type(height) is not int or width <= 0 or height <= 0
            or width * height > MAX_PIXELS or not isinstance(encoded, str)
            or len(encoded) > 4 * ((MAX_PNG_BYTES + 2) // 3)):
        raise ValueError("Invalid screenshot dimensions or data size.")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ValueError("Invalid screenshot encoding.") from error
    if len(data) > MAX_PNG_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid screenshot PNG.")
    offset, has_pixels = 8, False
    while offset + 12 <= len(data):
        length, kind = struct.unpack_from(">I4s", data, offset)
        end = offset + 12 + length
        if end > len(data):
            break
        body = data[offset + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        if zlib.crc32(kind + body) != crc:
            break
        if offset == 8:
            if kind != b"IHDR" or length != 13 or struct.unpack_from(">II", body) != (width, height):
                break
        elif kind == b"IHDR":
            break
        if kind == b"IDAT":
            has_pixels = True
        if kind == b"IEND":
            if length == 0 and end == len(data) and has_pixels:
                return data, width, height
            break
        offset = end
    raise ValueError("Incomplete or inconsistent screenshot PNG.")


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
