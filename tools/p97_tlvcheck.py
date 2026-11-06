"""Cross-check the Publisher block-length table against the 95/97/98 corpora.

The table below is `MSPUBParser::getBlockDataLength`
(ref/libmspub/src/lib/MSPUBParser.cpp:210).  It is the table of the shared
Publisher "Quill"/Contents block parser.  NOTE: this parser does not appear to
be reachable from the Publisher 95/97/98 chunk payloads -- see
notes/p97/slices/tlv_table.md.  The tool therefore doubles as a negative
control: if the table matched the 95/97 payloads, walking a chunk from the
correct prologue would terminate exactly at the end of the payload far more
often than by chance.

Block framing: {u8 id, u8 type, payload}; the payload width is implied by
`type`.  Variable-length types carry a u32 little-endian length INCLUDING the
four length bytes (libmspub reads `length - 4` data bytes).

Usage:
    python p97_tlvcheck.py p97/x p95/x
    python p97_tlvcheck.py p95/x --table --markers 0x22,0x14
    python p97_tlvcheck.py p97/x --max-prologue 64 --min-blocks 2
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import random
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

# type -> payload byte length; None = u32 length prefix (count includes the 4 bytes).
BLOCK_LEN = {
    0x00: 0,     # DUMMY
    0x05: 0,
    0x07: 2,
    0x08: 0,
    0x0A: 0,
    0x10: 2,
    0x12: 2,
    0x18: 2,
    0x1A: 2,
    0x20: 4,
    0x22: 4,
    0x28: 8,
    0x38: 16,
    0x48: 24,
    0x58: 4,
    0x68: 4,
    0x70: 4,
    0x78: 0,     # DUMMY (libmspub)
    0x80: None,
    0x82: None,
    0x88: None,  # GENERAL_CONTAINER
    0x8A: None,
    0x90: None,
    0x98: None,
    0xA0: None,
    0xC0: None,  # STRING_CONTAINER
    0xB8: 4,
}

VAR_LEN = {t for t, v in BLOCK_LEN.items() if v is None}
KNOWN = set(BLOCK_LEN)


class Walk:
    __slots__ = ("blocks", "consumed", "known", "var", "bad")

    def __init__(self, blocks, consumed, known, var, bad):
        self.blocks = blocks
        self.consumed = consumed   # bytes consumed from the walk start
        self.known = known         # blocks whose type is in BLOCK_LEN
        self.var = var             # variable-length blocks seen
        self.bad = bad             # True if a block ran past the payload end


def walk(payload: bytes, start: int, unknown_len0: bool = False) -> Walk:
    """Walk a TLV list from `start` to the end of `payload`.

    With `unknown_len0` an unknown type is treated as len 0 (libmspub's default
    branch) so the walk always makes progress.  Otherwise an unknown type ends
    the walk in the `bad` state -- that is the only useful test of whether the
    table explains a payload: with the lenient policy every even-length payload
    "terminates exactly", which is a tautology, not evidence.
    """
    rel = start
    n = len(payload)
    blocks = known = var = 0
    while rel + 2 <= n:
        btype = payload[rel + 1]
        blocks += 1
        if btype in KNOWN:
            known += 1
        elif not unknown_len0:
            return Walk(blocks, rel - start, known, var, True)
        ln = BLOCK_LEN.get(btype, 0)
        if ln is None:
            var += 1
            if rel + 6 > n:
                return Walk(blocks, rel - start, known, var, True)
            tot = struct.unpack_from("<I", payload, rel + 2)[0]
            if tot < 4 or rel + 2 + tot > n:
                return Walk(blocks, rel - start, known, var, True)
            rel += 2 + tot
        else:
            if rel + 2 + ln > n:
                return Walk(blocks, rel - start, known, var, True)
            rel += 2 + ln
    return Walk(blocks, rel - start, known, var, rel != n)


def check_chunk(payload: bytes, max_prologue: int, min_blocks: int,
                unknown_len0: bool = False):
    """Return (best_start, best_walk) or (None, None) if nothing terminates exactly."""
    best = None
    for start in range(min(max_prologue, len(payload)) + 1):
        w = walk(payload, start, unknown_len0)
        if w.bad or w.blocks < min_blocks:
            continue
        if start + w.consumed != len(payload):
            continue
        # prefer the shortest prologue (largest block count) that terminates
        score = (w.blocks, -start)
        if best is None or score > best[0]:
            best = (score, start, w)
    if best is None:
        return None, None
    return best[1], best[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpora", nargs="+")
    ap.add_argument("--max-prologue", type=int, default=64)
    ap.add_argument("--min-blocks", type=int, default=2)
    ap.add_argument("--markers", default=None,
                    help="comma separated chunk type markers (hex), default: all")
    ap.add_argument("--null-trials", type=int, default=2,
                    help="random-byte control per marker (0 disables)")
    ap.add_argument("--unknown-len0", action="store_true",
                    help="treat unknown block types as zero length (libmspub default)")
    ap.add_argument("--table", action="store_true", help="print the length table and exit")
    a = ap.parse_args()

    if a.table:
        for t in sorted(BLOCK_LEN):
            v = BLOCK_LEN[t]
            print("%#04x  %s" % (t, "var (u32 prefix)" if v is None else "%d bytes" % v))
        return 0

    wanted = ({int(x, 16) for x in a.markers.split(",")} if a.markers else None)
    per_type = collections.defaultdict(list)
    files = 0
    for corpus in a.corpora:
        paths = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
        paths += sorted(glob.glob(os.path.join(corpus, "**", "*.pub"), recursive=True))
        for path in paths:
            try:
                doc = pubcore.parse_contents(path)
            except Exception:
                continue
            files += 1
            for c in doc.chunks:
                if wanted is not None and c.type_marker not in wanted:
                    continue
                per_type[c.type_marker].append(c)

    print("corpora: %s" % ", ".join(a.corpora))
    print("files parsed: %d  chunk markers: %d  max prologue: %d  min blocks: %d  unknown->%s"
          % (files, len(per_type), a.max_prologue, a.min_blocks,
             "len0" if a.unknown_len0 else "fail"))
    print()
    print("%-8s %7s %8s %6s %9s %8s %6s %10s"
          % ("marker", "      n", "  exact", "  frac", " prologue", "blocks", " var", "  null"))
    rows = []
    rng = random.Random(0x97)
    for tm in sorted(per_type):
        chunks = per_type[tm]
        n = len(chunks)
        exact = 0
        best_p = collections.Counter()
        nblocks = var = 0
        for c in chunks:
            p, w = check_chunk(c.data, a.max_prologue, a.min_blocks, a.unknown_len0)
            if p is not None:
                exact += 1
                best_p[p] += 1
                nblocks += w.blocks
                var += w.var
        # null model: same payload lengths, uniformly random bytes
        null = 0.0
        if a.null_trials:
            sample = chunks if n <= 200 else rng.sample(chunks, 200)
            hit = tried = 0
            for c in sample:
                for _ in range(a.null_trials):
                    buf = bytes(rng.randrange(256) for _ in range(len(c.data)))
                    p, _w = check_chunk(buf, a.max_prologue, a.min_blocks, a.unknown_len0)
                    hit += p is not None
                    tried += 1
            null = 100.0 * hit / tried if tried else 0.0
        top_p = best_p.most_common(1)[0][0] if best_p else -1
        rows.append((tm, n, exact, exact / n, top_p, nblocks, var, null))
    rows.sort(key=lambda r: (-r[3], -r[1]))
    for tm, n, exact, frac, top_p, nblocks, var, null in rows:
        print("%#08x %7d %8d %5.1f%% %9s %8d %6d %9.1f%%"
              % (tm, n, exact, 100 * frac, ("+%d" % top_p) if top_p >= 0 else "-",
                 nblocks, var, null))
    print()
    tot = sum(r[1] for r in rows)
    tot_exact = sum(r[2] for r in rows)
    print("TOTAL chunks %d, exact-terminating %d (%.1f%%)"
          % (tot, tot_exact, 100.0 * tot_exact / tot if tot else 0.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
