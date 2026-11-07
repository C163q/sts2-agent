from sts2_mcp.output.presentation_status import PAGE_STATUSES, READABLE_STATUSES
from sts2_mcp.output.value_shapes import project, TEXT, TIP
from sts2_mcp.output.contracts.rooms import DIVINATION, DIVINATION_TEXT_GRID
import base64
import json
import struct
import zlib
from importlib.resources import files

from sts2_mcp.output.media import ImagePayload, png_data as _png_data

_PATTERNS = json.loads(files('sts2_mcp').joinpath('data/divination_patterns.json').read_text())['patterns']
APPEARANCES = {'unrecognized', 'card.upper_left', 'card.upper_right'} | {part for pattern in _PATTERNS for row in pattern['parts'] for part in row}


TOOL_SCHEMA = {'type': 'object', 'properties': {'tool': {
    'type': 'string', 'enum': ['big', 'small'],
    'description': 'big reveals a centered 3x3 area clipped to the board; small reveals one cell.',
}},
               'required': ['tool'], 'additionalProperties': False}
DIVINE_SCHEMA = {'type': 'object', 'properties': {
    'x': {'type': 'integer', 'minimum': 0, 'maximum': 10,
          'description': 'Zero-based column, increasing right from the top-left (0,0). Choose a # cell in divination.grid.cell_rows.'},
    'y': {'type': 'integer', 'minimum': 0, 'maximum': 10,
          'description': 'Zero-based row, increasing down from the top-left (0,0).'},
},
                 'required': ['x', 'y'], 'additionalProperties': False}




def divination_arguments(operation, arguments):
    if not isinstance(arguments, dict): raise ValueError('Arguments are required.')
    if operation == 'set_divination_tool':
        if set(arguments) != {'tool'} or arguments['tool'] not in ('big', 'small'):
            raise ValueError('Expected big or small tool.')
    elif set(arguments) != {'x', 'y'} or any(type(arguments[k]) is not int or not 0 <= arguments[k] <= 10 for k in ('x', 'y')):
        raise ValueError('Expected integer coordinates from 0 to 10.')
    return dict(arguments)


def divination_details(value, *, require_text=False):
    text = require_text or isinstance(value, dict) and 'cell_rows' in (value.get('grid') or {})
    shape = {**DIVINATION, 'grid': (DIVINATION_TEXT_GRID,)} if text else DIVINATION
    result = project(value, shape)
    if set(result) != set(DIVINATION) or result['status'] not in PAGE_STATUSES:
        raise ValueError('Invalid divination state.')
    if result['status'] == 'covered':
        if any(result[k] is not None for k in result if k != 'status'): raise ValueError('Hidden divination contents.')
        return result
    if result['phase'] not in {'playing', 'settling', 'finished'} or result['tool'] not in {None, 'big', 'small'} \
            or result['remaining'] is not None and not 0 <= result['remaining'] <= 6:
        raise ValueError('Invalid divination phase or tool.')
    grid = result['grid']
    row_key = 'cell_rows' if text else 'covered_rows'
    if (not grid or set(grid) != set(DIVINATION_TEXT_GRID if text else DIVINATION['grid'][0])
            or grid['columns'] != 11 or grid['rows'] != 11 or len(grid[row_key]) != 11
            or any(len(row) != 11 or set(row) - ({'#', '.', 's', 'S'} if text else {'#', '.'}) for row in grid[row_key])
            or set(grid['image']) != {'width', 'height'} or min(grid['image'].values()) <= 0):
        raise ValueError('Invalid divination grid.')
    if text:
        seen = set()
        for fragment in grid['visible_fragments']:
            x, y = fragment.get('x'), fragment.get('y')
            if (set(fragment) != {'x', 'y', 'appearance'} or not 0 <= x < 11 or not 0 <= y < 11
                    or (x, y) in seen or grid[row_key][y][x] not in {'s', 'S'}
                    or fragment['appearance'] not in APPEARANCES):
                raise ValueError('Invalid visible divination fragment.')
            seen.add((x, y))
        if seen != {(x, y) for y, row in enumerate(grid[row_key]) for x, cell in enumerate(row) if cell in 'sS'}:
            raise ValueError('Missing visible divination fragments.')
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
    if current.get('status') not in READABLE_STATUSES: return payload
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
