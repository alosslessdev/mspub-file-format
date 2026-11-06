"""Byte-level differential field mapper for Publisher chunk payloads.

For every chunk type, align all chunk payloads from a corpus at relative
offset 0 and report, per byte offset:
  * distinct value count across the corpus
  * whether the value is constant
  * the observed value set (truncated)
  * how many files contributed

This is the primary instrument for discovering implicit (undocumented) field
layouts: a field that is constant across 128 templates is a fixed tag, a field
with 2-6 distinct values is an enum, a field that increases with file size or
page count is a count/offset.

Usage:
    python pubstats.py <corpus-dir> [--type 0x15] [--max-size 512]
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


def collect(corpus: str, marker: int, max_size: int):
    rows = []
    files = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
    files = [f for f in files if "MSPUB" not in os.path.basename(f).upper() or True]
    for f in files:
        try:
            doc = pubcore.parse_contents(f)
        except Exception:
            continue
        for ch in doc.of_type(marker):
            rows.append((f, ch))
    return rows


def report(rows, max_size, show=8):
    if not rows:
        print("no chunks")
        return
    limit = min(max_size, max(len(c.data) for _, c in rows))
    print("chunk type %#06x  files=%d  payload sizes min=%d max=%d" % (
        rows[0][1].type_marker, len(rows),
        min(len(c.data) for _, c in rows), max(len(c.data) for _, c in rows)))
    print(" off  ndist  kind        sample values")
    for off in range(limit):
        vals = collections.Counter()
        for _, c in rows:
            if off < len(c.data):
                vals[c.data[off]] += 1
        if not vals:
            continue
        nd = len(vals)
        if nd == 1:
            kind = "const %#04x" % next(iter(vals))
            sample = ""
        elif nd <= 8:
            kind = "enum"
            sample = " ".join("%02x" % v for v, _ in vals.most_common(8))
        else:
            kind = "varies(%d)" % nd
            sample = " ".join("%02x" % v for v, _ in vals.most_common(show))
        print("%4x  %5d  %-11s %s" % (off, nd, kind, sample))
    # u32/u16 aligned views for the first 64 bytes
    print("\n u32 view at even offsets (distinct counts):")
    for off in range(0, min(limit, 96) - 3, 4):
        vals = collections.Counter()
        for _, c in rows:
            if off + 4 <= len(c.data):
                vals[struct.unpack_from("<I", c.data, off)[0]] += 1
        top = ", ".join("%d/0x%x(%d)" % (v, v, n) for v, n in vals.most_common(4))
        print("  +%02x nd=%-3d %s" % (off, len(vals), top))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--type", default=None, help="hex chunk type marker, e.g. 0x15")
    ap.add_argument("--max-size", type=int, default=256)
    a = ap.parse_args()
    if a.type:
        rows = collect(a.corpus, int(a.type, 16), a.max_size)
        report(rows, a.max_size)
        return
    # inventory
    counts = collections.Counter()
    files = sorted(glob.glob(os.path.join(a.corpus, "**", "*.PUB"), recursive=True))
    for f in files:
        try:
            doc = pubcore.parse_contents(f)
        except Exception:
            continue
        for ch in doc.chunks:
            counts[ch.type_marker] += 1
    for m, n in sorted(counts.items()):
        print("%#06x %-16s %d" % (m, pubcore.CHUNK_TYPES.get(m, "?"), n))


if __name__ == "__main__":
    main()
