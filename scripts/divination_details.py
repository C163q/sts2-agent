import base64
import struct
import zlib

from game_output import DIVINATION, project
from screenshot_tool import _png_data


TOOL_SCHEMA = {'type': 'object', 'properties': {'tool': {
    'type': 'string', 'enum': ['big', 'small'],
    'description': 'big reveals a centered 3x3 area clipped to the board; small reveals one cell.',
}},
               'required': ['tool'], 'additionalProperties': False}
DIVINE_SCHEMA = {'type': 'object', 'properties': {
    'x': {'type': 'integer', 'minimum': 0, 'maximum': 10,
          'description': 'Zero-based column, increasing right from the top-left (0,0). Choose a # cell in divination.grid.covered_rows.'},
    'y': {'type': 'integer', 'minimum': 0, 'maximum': 10,
          'description': 'Zero-based row, increasing down from the top-left (0,0).'},
},
                 'required': ['x', 'y'], 'additionalProperties': False}


class ImagePayload(dict):
    """Validated gameplay JSON with media kept outside the JSON object."""
    def __init__(self, payload, image):
        super().__init__(payload)
        self.image = image


def divination_arguments(operation, arguments):
    if not isinstance(arguments, dict): raise ValueError('Arguments are required.')
    if operation == 'set_divination_tool':
        if set(arguments) != {'tool'} or arguments['tool'] not in ('big', 'small'):
            raise ValueError('Expected big or small tool.')
    elif set(arguments) != {'x', 'y'} or any(type(arguments[k]) is not int or not 0 <= arguments[k] <= 10 for k in ('x', 'y')):
        raise ValueError('Expected integer coordinates from 0 to 10.')
    return dict(arguments)


def divination_details(value):
    result = project(value, DIVINATION)
    if set(result) != set(DIVINATION) or result['status'] not in {'visible', 'covered'}:
        raise ValueError('Invalid divination state.')
    if result['status'] == 'covered':
        if any(result[k] is not None for k in result if k != 'status'): raise ValueError('Hidden divination contents.')
        return result
    if result['phase'] not in {'playing', 'settling', 'finished'} or result['tool'] not in {None, 'big', 'small'} \
            or result['remaining'] is not None and not 0 <= result['remaining'] <= 6:
        raise ValueError('Invalid divination phase or tool.')
    grid = result['grid']
    if (not grid or set(grid) != {'columns', 'rows', 'covered_rows', 'image'}
            or grid['columns'] != 11 or grid['rows'] != 11 or len(grid['covered_rows']) != 11
            or any(len(row) != 11 or set(row) - {'#', '.'} for row in grid['covered_rows'])
            or set(grid['image']) != {'width', 'height'} or min(grid['image'].values()) <= 0):
        raise ValueError('Invalid divination grid.')
    if result['tools'] is not None and (len(result['tools']) != 2
            or {t.get('id') for t in result['tools']} != {'big', 'small'}
            or any(set(t) != {'id', 'text', 'enabled'} for t in result['tools'])):
        raise ValueError('Invalid divination tools.')
    if result['instructions'] is not None and set(result['instructions']) != {'title', 'description'}:
        raise ValueError('Invalid divination instructions.')
    if result['proceed'] is not None and set(result['proceed']) != {'text', 'enabled'}:
        raise ValueError('Invalid divination proceed.')
    return result


def attach_divination_image(payload, state):
    current = payload.get('divination') or {}
    if current.get('status') != 'visible': return payload
    data, width, height = _png_data(state['divination_image'])
    if current['grid']['image'] != {'width': width, 'height': height}:
        raise ValueError('Divination image dimensions do not match the grid.')
    # Godot emits noninterlaced 8-bit RGB(A); validate pixels before granting action permission.
    depth, color, compression, filtering, interlace = struct.unpack_from('>BBBBB', data, 24)
    if depth != 8 or color not in {2, 6} or (compression, filtering, interlace) != (0, 0, 0):
        raise ValueError('Unsupported divination PNG format.')
    compressed = bytearray()
    offset = 8
    while offset < len(data):
        length, kind = struct.unpack_from('>I4s', data, offset)
        if kind == b'IDAT': compressed.extend(data[offset + 8:offset + 8 + length])
        offset += length + 12
    stride = width * (3 if color == 2 else 4) + 1
    expected = stride * height
    try:
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed, expected + 1)
    except zlib.error as error:
        raise ValueError('Invalid divination PNG pixels.') from error
    if (len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail
            or any(pixels[offset] > 4 for offset in range(0, expected, stride))):
        raise ValueError('Incomplete or oversized divination PNG pixels.')
    return ImagePayload(payload, base64.b64encode(data).decode('ascii'))
