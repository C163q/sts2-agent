"""Pure media carrier and PNG envelope validation."""
import base64
import binascii
import struct
import zlib


MAX_PNG_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 16_777_216


class ImagePayload(dict):
    """Validated gameplay JSON with media kept outside the JSON object."""
    def __init__(self, payload, image):
        super().__init__(payload)
        self.image = image


def png_data(state):
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
