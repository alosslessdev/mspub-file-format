"""Find candidate small-domain (enum) byte/word fields per chunk type.

Usage: python tools/p98_fieldscan.py <corpus-dir> [more...] [--max N]

For every chunk marker, and every chunk-relative offset from 0 to the minimum
chunk size - 1, computes the value histogram of the byte and reports offsets
whose domain size is <= --max (default 24) over at least 20 chunks.
"""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore  # noqa: E402


def iter_pubs(root):
    for dirpath, _d, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith('.pub'):
                yield os.path.join(dirpath, fn)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith('--')]
    maxd = 24
    for a in argv[1:]:
        if a.startswith('--max'):
            maxd = int(a.split('=')[1])
    hists = collections.defaultdict(collections.Counter)  # (marker, off) -> Counter
    sizes = collections.defaultdict(collections.Counter)
    for root in args:
        for path in iter_pubs(root):
            try:
                doc = pubcore.parse_contents(path)
            except Exception:  # noqa: BLE001
                continue
            for ch in doc.chunks:
                sizes[ch.type_marker][len(ch.data)] += 1
                for off, b in enumerate(ch.data):
                    hists[(ch.type_marker, off)][b] += 1
    for marker in sorted(sizes):
        sz = sizes[marker]
        print(f"\n=== marker 0x{marker:04x}: {sum(sz.values())} chunks, sizes {sorted(sz.items())[:6]}")
        for off in range(0, 0x60):
            c = hists.get((marker, off))
            if not c or sum(c.values()) < 20:
                continue
            n = sum(c.values())
            if len(c) <= maxd:
                top = ", ".join(f"{v:02x}:{k}" for v, k in sorted(c.items()) if k >= max(1, n // 200))
                print(f"  +0x{off:02x} n={n} distinct={len(c)}  {top}")


if __name__ == '__main__':
    main(sys.argv)
