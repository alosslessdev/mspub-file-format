"""Locate the TLV list start offset inside chunk payloads, empirically.

Chunk payloads begin with a u16 type marker. Some chunk types are a pure TLV
list right after it; others carry a binary prologue first. Instead of guessing,
this tool tries every start offset and reports, per chunk type, which offset
makes a TLV list terminate exactly at the end of the payload for (almost) all
chunks in the corpus.

Usage: python tlvfind.py <corpus> [--types 0x15,0x05]
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import pubdump


def score(chunk_data: bytes, start: int, base: int):
    """Return ('exact'|'trailing'|'fail', consumed)."""
    blocks, consumed = pubdump.walk_blocks(chunk_data[start:], base + start)
    if not blocks:
        return "fail", 0
    if blocks[-1][4] != "TERMINATOR":
        return "fail", consumed
    if start + consumed == len(chunk_data):
        return "exact", consumed
    return "trailing", consumed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--types", default=None, help="comma separated hex markers")
    ap.add_argument("--max-start", type=int, default=48)
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.corpus, "**", "*.PUB"), recursive=True))
    per_type = collections.defaultdict(list)
    for f in files:
        try:
            doc = pubcore.parse_contents(f)
        except Exception:
            continue
        for c in doc.chunks:
            per_type[c.type_marker].append(c)
    wanted = [int(x, 16) for x in a.types.split(",")] if a.types else sorted(
        per_type, key=lambda k: -len(per_type[k]))
    for tm in wanted:
        chunks = per_type.get(tm, [])
        if not chunks:
            continue
        best = []
        for start in range(0, min(a.max_start, 64)):
            cnt = collections.Counter()
            for c in chunks:
                if len(c.data) <= start:
                    continue
                k, _ = score(c.data, start, c.offset)
                cnt[k] += 1
            if cnt["exact"]:
                best.append((cnt["exact"], start, dict(cnt)))
        best.sort(reverse=True)
        print("\nchunk type %#06x  n=%d  (top exact-terminating start offsets)"
              % (tm, len(chunks)))
        if not best:
            print("   no start offset produces an exact TLV termination")
            continue
        for exact, start, cnt in best[:4]:
            print("   start=+%d  exact=%d/%d  %s" % (start, exact, len(chunks), cnt))


if __name__ == "__main__":
    main()
