#!/usr/bin/env python3
"""MSPUB.M14 container reader (Publisher 95/97/98 "M14" file).

M14 is NOT a PE. It is a WinHelp 4.0 help file ("HCR"/"HCW" internal file
system): a 16-byte header followed by a sequence of named slots, plus a
B+tree-ish directory at header+0x04 that maps name -> slot offset.

Layout (all u32 little-endian):

    0x00 u16 0x5F3F      magic  ("?_", same value as a WinHelp .HLP)
    0x02 u16 0x0003      version
    0x04 u32 dir_off     offset of the internal-file directory
    0x08 u32 alt_off     offset of a second (older / secondary) directory node
    0x0C u32 file_len    total length of the file, == os.path.getsize()
    0x10 ...             first slot ("|MVCHARTAB" in both shipped files)

Slot header (every named slot, at its listed offset):

    +0x00 u32 slot_len   distance to the next slot (files tile the file)
    +0x04 u32 data_len   < slot_len-9 when the payload is compressed
    +0x08 ...            payload (an 8-byte record/compression prefix follows
                         for most slots; a WinHelp B+tree node carries the
                         u16 magic 0x293B at payload+1)

Usage:
    python tools/p98_m14.py p98/x/MSPUB.M14            # header + tiling report
    python tools/p98_m14.py p98/x/MSPUB.M14 --list     # every slot
    python tools/p98_m14.py p98/x/MSPUB.M14 --string X # find a slot by name
"""

import os
import re
import struct
import sys

MAGIC = 0x5F3F
# Internal ("|SYSTEM", "|bm0", ...) or baggage ("ARROW1.WMF", "BACKBTN.BMP") name.
_NAME_RE = re.compile(rb"^(?:\|[A-Za-z0-9_]+|[A-Z0-9_\-]{2,16}\.[A-Z0-9]{2,4})$")


def parse(path):
    d = open(path, "rb").read()
    magic, ver, dir_off, alt_off, file_len = struct.unpack_from("<HHIII", d, 0)
    if magic != MAGIC:
        raise ValueError("not an M14/WinHelp container: magic %04x" % magic)
    out = {
        "path": path,
        "size": len(d),
        "magic": magic,
        "version": ver,
        "dir_off": dir_off,
        "alt_off": alt_off,
        "file_len": file_len,
        "entries": directory(d, dir_off),
    }
    return out, d


def directory(d, dir_off):
    """Walk a directory node: repeated `name NUL u32 offset`, resyncing over
    the small per-page markers that interrupt the entry list.  An entry is
    kept only when its slot header validates (8 <= slot_len, slot fits)."""
    ents = {}
    p = dir_off
    n = len(d)
    while p < n - 6:
        q = p
        while q < n and 32 < d[q] < 127:
            q += 1
        if q < n and d[q] == 0 and 2 <= q - p <= 20 and _NAME_RE.match(d[p:q]):
            name = d[p:q].decode("ascii")
            off = struct.unpack_from("<I", d, q + 1)[0]
            if 0x10 <= off <= n - 8:
                slot_len = struct.unpack_from("<I", d, off)[0]
                if 9 <= slot_len <= n - off and name not in ents:
                    ents[name] = off
                    p = q + 5
                    continue
        p += 1
    return ents


def slots(ents):
    """(name, off, slot_len, data_len, end) sorted by offset."""
    d = _DATA
    res = []
    for name, off in sorted(ents.items(), key=lambda kv: kv[1]):
        slot_len, data_len = struct.unpack_from("<II", d, off)
        res.append((name, off, slot_len, data_len, off + slot_len))
    return res


def report(path, verbose=False):
    global _DATA
    info, d = parse(path)
    _DATA = d
    n = info["size"]
    print("%s  %d bytes (0x%x)" % (path, n, n))
    print("  magic 0x%04x version %d dir_off 0x%06x alt_off 0x%06x file_len 0x%06x (%s)"
          % (info["magic"], info["version"], info["dir_off"], info["alt_off"],
             info["file_len"], "OK" if info["file_len"] == n else "MISMATCH"))
    sl = slots(info["entries"])
    uniq = []
    for s in sl:
        if not uniq or s[1] != uniq[-1][1]:
            uniq.append(s)
    print("  %d named slots (%d distinct offsets)" % (len(sl), len(uniq)))
    prev_end = 0x10
    gaps = []
    tiles = 0
    for name, off, slot_len, data_len, end in uniq:
        if off != prev_end:
            gaps.append((prev_end, off - prev_end, "before " + name))
        else:
            tiles += 1
        prev_end = end
    if n > prev_end:
        gaps.append((prev_end, n - prev_end, "tail"))
    print("  chained tiles: %d/%d   chain ends at 0x%06x of 0x%06x"
          % (tiles, len(uniq) - 1, prev_end, n))
    print("  regions not covered by the slot chain:")
    for off, ln, why in gaps:
        print("      0x%06x + 0x%06x  %-16s %s" % (off, ln, why, _what(d, off, ln)))
    if verbose:
        print("%-16s %8s %8s %8s  %s" % ("name", "offset", "slot_len", "data_len", "payload[0:8]"))
        for name, off, slot_len, data_len, end in sl:
            print("%-16s %08x %8x %8x  %s"
                  % (name, off, slot_len, data_len, d[off + 8:off + 16].hex(" ")))
    return info


def _what(d, off, ln):
    if off == 0:
        return "16-byte container header"
    head = d[off:off + 8]
    if len(head) >= 6 and head[2:4] == b"\x3b\x29":
        return "unlisted B+tree node (u16 0x293B at +2)"
    if head[:2] in (b"BM",):
        return "bitmap"
    return head.hex(" ")


def find(path, needle):
    info, d = parse(path)
    global _DATA
    _DATA = d
    hits = [s for s in slots(info["entries"]) if needle.lower() in s[0].lower()]
    for name, off, slot_len, data_len in hits:
        print("%-16s off 0x%06x slot 0x%x data 0x%x  %s"
              % (name, off, slot_len, data_len, d[off + 8:off + 24].hex(" ")))
    return hits


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    path = argv[1]
    if "--list" in argv:
        report(path, verbose=True)
    elif "--string" in argv:
        find(path, argv[argv.index("--string") + 1])
    else:
        report(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
