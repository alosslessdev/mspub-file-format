"""Annotated dump of a Publisher chunk (TLV block walker).

The TLV framing is `{u8 id, u8 type, payload}` where the payload width is implied
by `type`. The table below starts from libmspub's hypothesis and every unknown
type is reported instead of silently skipped, so the table can be extended from
evidence rather than assumption.

Usage:
    python pubdump.py <file.pub> [--chunk-id 0x100 | --type 0x15] [--limit N]
"""
from __future__ import annotations

import argparse
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

# type -> payload length; None = variable (u32 length prefix, length includes the 4 bytes)
TYPE_LEN = {
    0x00: 0, 0x01: 0, 0x02: 0, 0x03: 0, 0x04: 0, 0x05: 0, 0x06: 0, 0x07: 2,
    0x08: 0, 0x09: 0, 0x0A: 0, 0x0C: 2, 0x0E: 2, 0x10: 2, 0x12: 2, 0x18: 2,
    0x1A: 2, 0x1C: 2, 0x1E: 2, 0x20: 4, 0x22: 4, 0x24: 2, 0x26: 2, 0x28: 8,
    0x2A: 2, 0x2C: 2, 0x2E: 4, 0x30: 4, 0x32: 2, 0x34: 2, 0x36: 2, 0x38: 16,
    0x3A: 2, 0x44: 4, 0x46: 4, 0x48: 24, 0x58: 4, 0x68: 4, 0x70: 4, 0xB8: 4,
    0x80: None, 0x82: None, 0x88: None, 0x8A: None, 0x90: None, 0x98: None,
    0xA0: None, 0xC0: None,
}

KNOWN_IDS = {}


def hexdump(data: bytes, base: int, width: int = 16):
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        h = " ".join("%02x" % b for b in chunk)
        a = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print("  %06x  %-47s  %s" % (base + off, h, a))


def walk_blocks(data: bytes, base: int, depth: int = 0, out=None):
    """Yield (offset, id, type, payload) walking the TLV stream; stop on anomaly."""
    rel = 0
    blocks = []
    while rel + 2 <= len(data):
        bid = data[rel]
        btype = data[rel + 1]
        if bid == 0 and btype == 0:
            # Observed terminator: a zero doublet ends the block list.
            blocks.append((base + rel, 0, 0, b"", "TERMINATOR"))
            rel += 2
            break
        payload_off = rel + 2
        if btype in TYPE_LEN:
            ln = TYPE_LEN[btype]
            if ln is None:
                if rel + 6 > len(data):
                    blocks.append((base + rel, bid, btype, None, "truncated var header"))
                    break
                ln = struct.unpack_from("<I", data, rel + 2)[0]
                if ln < 4 or rel + 2 + ln > len(data):
                    blocks.append((base + rel, bid, btype, None,
                                   "bad var length %d at rel %d" % (ln, rel)))
                    break
                payload = data[rel + 6:rel + 2 + ln]
                blocks.append((base + rel, bid, btype, payload, ""))
                rel += 2 + ln
                continue
            if rel + 2 + ln > len(data):
                blocks.append((base + rel, bid, btype, None, "truncated fixed"))
                break
            payload = data[rel + 2:rel + 2 + ln]
            blocks.append((base + rel, bid, btype, payload, ""))
            rel += 2 + ln
        else:
            blocks.append((base + rel, bid, btype, None, "unknown type %#04x" % btype))
            break
    return blocks, rel


def describe(blocks, data, base, depth=0):
    pad = "  " * depth
    for off, bid, btype, payload, err in blocks:
        if err:
            print("%s@%06x id=%#04x type=%#04x  !! %s" % (pad, off, bid, btype, err))
            continue
        rel = off - base
        if btype == 0xC0:  # string container
            try:
                s = payload.decode("latin-1")
            except Exception:
                s = repr(payload)
            print("%s@%06x id=%#04x type=STR  %r" % (pad, off, bid, s))
        elif btype in (0x80, 0x82, 0x88, 0x8A, 0x90, 0x98, 0xA0):
            print("%s@%06x id=%#04x type=%#04x len=%d (container)"
                  % (pad, off, bid, btype, len(payload)))
            if depth < 3:
                sub, _ = walk_blocks(payload, off + 6)
                describe(sub, payload, off + 6, depth + 1)
        else:
            val = int.from_bytes(payload, "little") if payload else 0
            print("%s@%06x id=%#04x type=%#04x len=%d val=%#x"
                  % (pad, off, bid, btype, len(payload), val))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--chunk-id", default=None, help="hex, e.g. 0x100")
    ap.add_argument("--type", default=None, help="hex chunk type marker, e.g. 0x15")
    ap.add_argument("--limit", type=int, default=4)
    ap.add_argument("--hex", action="store_true")
    a = ap.parse_args()
    doc = pubcore.parse_contents(a.file)
    sel = []
    if a.chunk_id:
        c = doc.by_id(int(a.chunk_id, 16))
        sel = [c] if c else []
    elif a.type:
        sel = doc.of_type(int(a.type, 16))
    else:
        sel = doc.chunks
    print("%s ver=%02x chunks=%d" % (a.file, doc.version_magic, len(doc.chunks)))
    print("streams:")
    for s in doc.streams:
        print("  " + s)
    for c in sel[:a.limit]:
        print("\n== chunk id=%#06x parent=%#06x type=%#06x (%s) off=%#08x size=%d"
              % (c.id, c.parent, c.type_marker, c.type_name, c.offset, c.size))
        if a.hex:
            hexdump(c.data, c.offset)
        else:
            blocks, consumed = walk_blocks(c.data, c.offset)
            describe(blocks, c.data, c.offset)
            print("  -- TLV consumed %d of %d payload bytes (%.1f%%), %d bytes trailing"
                  % (consumed, len(c.data), 100.0 * consumed / max(1, len(c.data)),
                     len(c.data) - consumed))
            if consumed < len(c.data):
                hexdump(c.data[consumed:consumed + 64], c.offset + consumed)


if __name__ == "__main__":
    main()
