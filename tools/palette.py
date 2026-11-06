"""Default Publisher 95-98 palette: index -> RGB.

Generated from the table in spec/09-chunk-palette.md (9.2). The spec lists each
entry as 0xRRGGBB; the binary stores the same colour as a COLORREF (0x00BBGGRR).

Regenerate with tools/gen_palette.py.
"""

PALETTE = {
    0x00: (  0,   0,   0),
    0x01: (255, 255, 255),
    0x02: (255,   0,   0),
    0x03: (  0, 255,   0),
    0x04: (  0,   0, 255),
    0x05: (255, 255,   0),
    0x06: (  0, 255, 255),
    0x07: (255,   0, 255),
    0x08: (128, 128, 128),
    0x09: (192, 192, 192),
    0x0A: (128,   0,   0),
    0x0B: (  0, 128,   0),
    0x0C: (  0,   0, 128),
    0x0D: (128, 128,   0),
    0x0E: (  0, 128, 128),
    0x0F: (128,   0, 128),
    0x10: (255, 153,  51),
    0x11: ( 51,   0,  51),
    0x12: (  0,   0, 153),
    0x13: (  0, 153,   0),
    0x14: (153, 153,   0),
    0x15: (204, 102,   0),
    0x16: (153,   0,   0),
    0x17: (204, 153, 204),
    0x18: (102, 102, 255),
    0x19: (102, 255, 102),
    0x1A: (255, 255, 102),
    0x1B: (255, 204, 153),
    0x1C: (255, 102, 102),
    0x1D: (255, 153,   0),
    0x1E: (  0, 102, 255),
    0x1F: (255, 204,   0),
    0x20: (153,   0,  51),
    0x21: (102,  51,   0),
    0x22: ( 66,  66,  66),
    0x23: (255, 153, 102),
    0x24: (153,  51,   0),
    0x25: (255, 102,   0),
    0x26: ( 51,  51,   0),
    0x27: (153, 204,   0),
    0x28: (255, 255, 153),
    0x29: (  0,  51,   0),
    0x2A: ( 51, 153, 102),
    0x2B: (204, 255, 204),
    0x2C: (  0,  51, 102),
    0x2D: ( 51, 204, 204),
    0x2E: (204, 255, 255),
    0x2F: ( 51, 102, 255),
    0x30: (  0, 204, 255),
    0x31: (153, 204, 255),
    0x32: ( 51,  51, 153),
    0x33: (102, 102, 153),
    0x34: (153,  51, 102),
    0x35: (204, 153, 255),
    0x36: ( 51,  51,  51),
    0x37: (150, 150, 150),
}


def resolve_palette(index: int):
    """Palette index -> RGB, or None if outside the table."""
    return PALETTE.get(index & 0xFF)


def decode_colorref(ref: int, palette=None):
    """Decode a 32-bit Publisher colour reference (spec 9.1).

    Returns (r, g, b) or None when the reference needs a lookup table this module
    does not have (derived/automatic colours).
    """
    table = PALETTE if palette is None else palette
    tag = (ref >> 24) & 0xFF
    top = tag >> 5
    if top == 0b000:
        return table.get(ref & 0xFFFF)
    if top == 0b001:
        return (ref & 0xFF, (ref >> 8) & 0xFF, (ref >> 16) & 0xFF)
    if top == 0b101 and (ref & 0xFFFF) == 0:
        return (0xD7, 0xB7, 0x73)  # 0x4737B automatic colour, spec 9.1
    return None
