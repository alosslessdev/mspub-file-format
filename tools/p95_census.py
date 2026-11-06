"""Publisher 95 corpus census: directory, parent graph, marker table, flags domain.

Emits the exact tables published in spec/03-directory.md so they can be regenerated.

Usage:
    python tools/p95_census.py                 # markdown tables for p95/x
    python tools/p95_census.py --corpus p95/x
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

NAMES = {
    0x0000: "SHAPE / text frame (has font size)",
    0x0001: "SHAPE1 (14-byte tail records)",
    0x0002: "IMAGE",
    0x0003: "SHAPE3 (polygon, vertex array)",
    0x0004: "LINE",
    0x0005: "RECT",
    0x0006: "SHAPE_OBJECT (OLE)",
    0x0007: "SHAPE7 (fixed 41)",
    0x000F: "GROUP / frame",
    0x0014: "PAGE",
    0x0015: "DOCUMENT",
    0x0016: "text-story container",
    0x001A: "story table #1 (26+14n)",
    0x001C: "story table #2 (26+8n)",
    0x001E: "FONT table",
    0x001F: "line/border style table",
    0x0021: "IMAGE_DATA",
    0x0022: "OLE reference (18 B)",
    0x0023: "fixed 4-slot table",
    0x0026: "paragraph-style names",
    0x0027: "linked clip-art reference",
    0x0028: "paper/print parameter block",
    0x0029: "PRINT SETUP (DEVMODE)",
    0x002A: "font-substitution table",
    0x002B: "document name list",
    0x002C: "page layout / column grid",
    0x002D: "story parameter mirror A",
    0x002E: "story parameter mirror B",
    0x0031: "design / object-set",
    0x0032: "string table (child of 0x31)",
    0x0034: "fixed 14-byte sub-table",
    0x0035: "DLL binding record",
    0x0036: "print-setup companion (112 B)",
    0x0037: "colour list (6-byte records)",
    0x0038: "colour list (10-byte records)",
    0x0039: "48-byte document record",
}


def documents(root):
    out = []
    for pat in ("**/*.PUB", "**/*.JSP"):
        out.extend(glob.glob(os.path.join(root, pat), recursive=True))
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="p95/x")
    args = ap.parse_args()

    files = documents(args.corpus)
    cnt = collections.Counter()
    nfiles = collections.Counter()
    per_min = {}
    per_max = {}
    sizes = collections.defaultdict(collections.Counter)
    parents = collections.defaultdict(collections.Counter)
    depth_rng = collections.defaultdict(lambda: [99, -1])
    flags = collections.defaultdict(collections.Counter)
    flag_all = collections.Counter()
    depth_hist = collections.Counter()
    total_bytes = collections.Counter()
    nrec = 0
    Ds = []
    counts = []
    for f in files:
        d = pubcore.read_stream(f, "Contents")
        D = struct.unpack_from("<I", d, 0x16)[0]
        n = struct.unpack_from("<H", d, D)[0]
        Ds.append(D)
        counts.append(n)
        doc = pubcore.parse_contents(f, d)
        by_id = {c.id: c for c in doc.chunks}
        kids = collections.Counter(c.parent for c in doc.chunks)

        def depth(c):
            k = 0
            while c.parent in by_id:
                c = by_id[c.parent]
                k += 1
                if k > 50:
                    break
            return k

        seen_here = collections.Counter()
        for c in doc.chunks:
            nrec += 1
            cnt[c.type_marker] += 1
            seen_here[c.type_marker] += 1
            sizes[c.type_marker][c.size] += 1
            total_bytes[c.type_marker] += c.size
            p = by_id.get(c.parent)
            parents[c.type_marker][p.type_marker if p else 0x00FE] += 1
            dep = depth(c)
            depth_hist[dep] += 1
            r = depth_rng[c.type_marker]
            r[0] = min(r[0], dep)
            r[1] = max(r[1], dep)
            flags[c.type_marker][c.flags] += 1
            flag_all[c.flags] += 1
        for mk, k in seen_here.items():
            nfiles[mk] += 1
            per_min[mk] = min(per_min.get(mk, 999), k)
            per_max[mk] = max(per_max.get(mk, 0), k)

    print("documents: %d   records: %d   markers: %d" % (len(files), nrec, len(cnt)))
    print("directory offset: %#x .. %#x   count: %d .. %d"
          % (min(Ds), max(Ds), min(counts), max(counts)))
    print("distinct flags values: %d" % len(flag_all))
    for v, k in flag_all.most_common():
        print("   %04X  %6d  %5.1f%%" % (v, k, 100.0 * k / nrec))
    print("\ndepth histogram: " + ", ".join("%d:%d" % kv for kv in sorted(depth_hist.items())))

    print("\n| marker | n | files | per-file | parents | bytes | size min/mode/max | distinct | depth | flags |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for mk in sorted(cnt):
        s = sizes[mk]
        mode = s.most_common(1)[0][0]
        par = ", ".join("%#06x×%d" % kv for kv in parents[mk].most_common(3))
        fl = ",".join("%04X" % v for v in sorted(flags[mk]))
        print("| `%#06x` %s | %d | %d | %d–%d | %s | %d | %d/%d/%d | %d | %d–%d | %s |"
              % (mk, NAMES.get(mk, "?"), cnt[mk], nfiles[mk], per_min[mk], per_max[mk], par,
                 total_bytes[mk], min(s), mode, max(s), len(s),
                 depth_rng[mk][0], depth_rng[mk][1], fl))
    return 0


if __name__ == "__main__":
    sys.exit(main())
