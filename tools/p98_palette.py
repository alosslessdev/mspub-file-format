#!/usr/bin/env python3
"""Dump Publisher 95/97/98 PALETTE records (chunk type marker 0x0047).

Usage:
    python tools/p98_palette.py <root-or-file> [...]

A PALETTE record is a fixed 192-byte (0xC0) record that lives in the Contents
stream of a publication.  Layout recovered in notes/p98/slices/palette-chunk.md:

    0x00 u16  0x0047              record type marker
    0x02 u16  0x9696              record signature/tag (constant per marker)
    0x04 u16  0                  always 0 in every sample
    0x06 u32  0 or 0xFFFFFFFF    varies (see slice; 0xFFFFFFFF only on "(Custom)")
    0x0A u16  0 or 4             varies
    0x0C u16  0                  always 0
    0x0E ...  UTF-16LE name, NUL terminated, zero filled to 0x8F
    0x90 16 bytes  constant block 01 00 00 00 00 00 08 00 08 00 04 00 00 00 00 00
    0xA0 8 x u32  colour entries, high byte = tag, low 24 bits = value

Colour entry decoding (same encoding as shape colour fields):
    tag 0x00 / 0x80 -> index into the built-in palette (observed 0..0x37)
    tag 0x20 / 0x90 -> literal RGB, bytes [R][G][B] then tag
    anything else   -> reported verbatim

Note: the record is *not* a TLV list; the 0x95/0x97 chunk payloads are fixed
records (see notes/chunk-markers-by-version.md).
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

MARKER = 0x0047
SIZE = 0xC0
NAME_OFF = 0x0E
AUX_OFF = 0x90
ARR_OFF = 0xA0
ARR_N = 8


def decode_entry(v):
    tag = (v >> 24) & 0xFF
    val = v & 0xFFFFFF
    if tag in (0x00, 0x80):
        return "idx 0x%02x (%d)" % (val, val)
    if tag in (0x20, 0x90):
        return "RGB(%02x,%02x,%02x) tag %02x" % (v & 0xFF, (v >> 8) & 0xFF,
                                                 (v >> 16) & 0xFF, tag)
    return "tag 0x%02x value 0x%06x" % (tag, val)


def iter_publications(root):
    if os.path.isfile(root):
        yield root
        return
    for d, _dirs, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            try:
                with open(p, "rb") as fh:
                    if fh.read(8) != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
                        continue
            except OSError:
                continue
            yield p


def dump(path):
    try:
        doc = pubcore.parse_contents(path)
    except Exception:
        return 0
    n = 0
    for c in doc.chunks:
        if c.type_marker != MARKER:
            continue
        n += 1
        b = c.data
        name = b[NAME_OFF:AUX_OFF].decode("utf-16le", "replace").split("\x00")[0]
        print("%s: id=0x%03x parent=%d size=%d" % (path, c.id, c.parent, len(b)))
        print("  name            %r" % name)
        print("  header 04..0d   %s" % b[4:14].hex(" "))
        print("  aux    90..9f   %s" % b[AUX_OFF:AUX_OFF + 16].hex(" "))
        for i in range(ARR_N):
            v = struct.unpack_from("<I", b, ARR_OFF + 4 * i)[0]
            print("  [%d] +%03x %08x  %s" % (i, ARR_OFF + 4 * i, v, decode_entry(v)))
        if len(b) != SIZE:
            print("  !! unexpected size (expected %d)" % SIZE)
    return n


def main(argv):
    total = 0
    for root in argv[1:]:
        for p in iter_publications(root):
            total += dump(p)
    print("# %d palette record(s)" % total)


if __name__ == "__main__":
    main(sys.argv)
