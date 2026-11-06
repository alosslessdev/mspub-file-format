#!/usr/bin/env python3
"""Colour-reference analysis for the Publisher 95/97/98 (2k-family) chunk format.

Sub-commands
  shapescan   <corpus...>   shape chunks: u32 at +0x22 (fill colour) and +0x2A (fill type),
                            plus u32 at +0x32 (line colour) / +0x36? ; per-high-byte histogram
  palettes    <corpus...>   PALETTE (0x47) chunks: full byte dump + the eight u32 at +0xA0
  scan        <corpus...>   per-byte high-byte signature scan: modal absolute offsets of
                            4-byte little-endian words whose top byte is a known colour tag
  u32hist     <corpus...>   high-byte histogram of the colour words found at the modal offsets

Evidence output is always "file:absolute_offset".
"""
import sys, os, glob, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

TAGS = (0x00, 0x20, 0x80, 0x90, 0xC0, 0xE0)


def files_of(args):
    out = []
    for a in args:
        if os.path.isdir(a):
            out.extend(sorted(glob.glob(os.path.join(a, "**", "*.PUB"), recursive=True)))
        else:
            out.append(a)
    # de-dupe case-insensitively (Windows globs are case-insensitive already, but --args may repeat)
    seen = set()
    uniq = []
    for f in out:
        k = os.path.normcase(os.path.abspath(f))
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    return uniq


def u32(data, off):
    if off + 4 > len(data):
        return None
    return struct.unpack_from("<I", data, off)[0]


def loader(args):
    for f in files_of(args):
        try:
            yield f, pubcore.parse_contents(f)
        except Exception as e:
            print("SKIP", f, e)


FILL_TYPE_OFF = 0x2A
FILL_COLOR_OFF = 0x22


def cmd_shapescan(args):
    """Shape chunks 0x00..0x08: histogram of the high byte of the fill colour word."""
    hb = collections.Counter()
    per_type = collections.defaultdict(collections.Counter)
    filltypes = collections.Counter()
    out = []
    for f, d in loader(args):
        for c in d.chunks:
            if c.type_marker > 0x08:
                continue
            v = u32(c.data, FILL_COLOR_OFF)
            t = c.data[FILL_TYPE_OFF] if len(c.data) > FILL_TYPE_OFF else None
            if v is None:
                continue
            filltypes[t] += 1
            h = (v >> 24) & 0xFF
            key = h if h in TAGS else "other(%02x)" % h
            hb[key] += 1
            per_type[c.type_marker][key] += 1
            out.append((f, c, v, t))
    print("== fill type at +0x%02x :" % FILL_TYPE_OFF, dict(filltypes))
    print("== high byte of u32 at +0x%02x :" % FILL_COLOR_OFF, dict(hb))
    for k in sorted(per_type):
        print("   marker %02x : %s" % (k, dict(per_type[k])))
    print("== non-zero colour words (filltype==2, i.e. solid fill):")
    n = 0
    for f, c, v, t in out:
        if t == 2 and v not in (0, 0x00000000):
            print("   %s:%d chunk id=%d marker=%02x fill=%08x (%s)" %
                  (f, c.offset + FILL_COLOR_OFF, c.id, c.type_marker, v,
                   interpret(v)))
            n += 1
    print("   total solid fills with colour word: %d" % n)


def interpret(v):
    h = (v >> 24) & 0xFF
    if h in (0x00, 0x80):
        return "palette index 0x%02x" % (v & 0xFF)
    if h in (0x20, 0x90):
        return "rgb(%d,%d,%d)" % (v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF)
    if h in (0xC0, 0xE0):
        return "user-palette index 0x%02x" % (v & 0xFF)
    return "UNKNOWN tag"


def cmd_palettes(args):
    for f, d in loader(args):
        for c in d.chunks:
            if c.type_marker != 0x47:
                continue
            print("== %s:%d  size=%d" % (f, c.offset, c.size))
            for i in range(0, len(c.data), 16):
                print("   +%03x  %s" % (i, c.data[i:i + 16].hex(" ")))
            print("   -- u32 at +0xA0 (8 entries, libmspub order):")
            for k in range(8):
                v = u32(c.data, 0xA0 + 4 * k)
                if v is None:
                    break
                print("      +%03x = %08x  %s" % (0xA0 + 4 * k, v, interpret(v)))


def cmd_scan(args, restrict=None):
    cnt = collections.Counter()
    tot = 0
    for f, d in loader(args):
        for c in d.chunks:
            if restrict is not None and c.type_marker != restrict:
                continue
            tot += 1
            data = c.data
            for o in range(max(0, len(data) - 3)):
                if data[o + 3] in (0x20, 0x80, 0x90, 0xC0, 0xE0):
                    cnt[o] += 1
    print("chunks scanned:", tot)
    for o, n in sorted(cnt.items()):
        if n >= 2:
            print("  offset +%02x : %d" % (o, n))


def cmd_u32hist(args, off, restrict=None):
    hb = collections.Counter()
    for f, d in loader(args):
        for c in d.chunks:
            if restrict is not None and c.type_marker != restrict:
                continue
            v = u32(c.data, off)
            if v is None:
                continue
            h = (v >> 24) & 0xFF
            hb[h if h in TAGS else "other"] += 1
    print("u32 at +%02x high-byte histogram:" % off, dict(hb))


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "shapescan":
        cmd_shapescan(args)
    elif cmd == "palettes":
        cmd_palettes(args)
    elif cmd == "scan":
        restrict = None
        if "--type" in args:
            i = args.index("--type")
            restrict = int(args[i + 1], 0)
            args = args[:i] + args[i + 2:]
        cmd_scan(args, restrict)
    elif cmd == "u32hist":
        cmd_u32hist(args, int(args[0], 0), None if len(args) < 2 else int(args[1], 0))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
