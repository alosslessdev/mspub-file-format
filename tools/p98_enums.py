"""Corpus histograms for single-byte enum fields inside shape chunks.

Usage:
  python tools/p98_enums.py <corpus-dir> [more dirs...]

For every chunk it records, per chunk type marker, the distribution of the
bytes at a set of fixed chunk-relative offsets (the offsets libmspub uses):
  0x22 u32 fill colour ref, 0x2A u8 fill type, 0x2C u8 line width,
  0x31 u8 shape specifier, 0x33 u8 flip flags, 0x35 u8 vertical align,
  0x41 u8 line flags (marker 0x04).

Output: per (marker, offset) a sorted "value:count" histogram.
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore  # noqa: E402

OFFSETS = [0x22, 0x2A, 0x2C, 0x31, 0x33, 0x35, 0x41]


def iter_pubs(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.pub'):
                yield os.path.join(dirpath, fn)


def main(argv):
    roots = argv[1:]
    hist = collections.defaultdict(collections.Counter)
    nfiles = 0
    nchunks = 0
    fails = []
    for root in roots:
        for path in iter_pubs(root):
            try:
                doc = pubcore.parse_contents(path)
            except Exception as exc:  # noqa: BLE001
                fails.append((path, repr(exc)))
                continue
            nfiles += 1
            for ch in doc.chunks:
                nchunks += 1
                data = ch.data
                for off in OFFSETS:
                    if off < len(data):
                        hist[(ch.type_marker, off)][data[off]] += 1
    print(f"files={nfiles} chunks={nchunks} failures={len(fails)}")
    for path, err in fails[:10]:
        print("FAIL", path, err)
    for (marker, off) in sorted(hist, key=lambda k: (k[0], k[1])):
        c = hist[(marker, off)]
        top = ", ".join(f"{v:02x}:{n}" for v, n in sorted(c.items()))
        print(f"marker 0x{marker:04x} +0x{off:02x}  ({sum(c.values())} chunks, {len(c)} distinct)  {top}")


if __name__ == '__main__':
    main(sys.argv)
