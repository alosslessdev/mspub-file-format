"""Directory `flags` word: structural-bit correlation experiment (Publisher 95).

For every bit of the 16-bit `flags` word at directory record +8, compute a 2x2
contingency table against a set of structural predicates, and report:

  * phi coefficient (signed correlation) over all records,
  * whether the bit is constant, 1:1 with the feature, or unrelated.

Usage:
    python tools/p95_flags.py                # summary tables for p95/x
    python tools/p95_flags.py --per-marker   # per-marker flag values
"""
from __future__ import annotations

import argparse
import collections
import glob
import math
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

PAGE = 0x14
DOCUMENT = 0x15
STORY = 0x16
GROUP = 0x0F
TEXT_RUNS = (0x1A, 0x1C)          # the two counted-string children of 0x16
SHAPES = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0F}


def documents(root="p95/x"):
    out = []
    for pat in ("**/*.PUB", "**/*.JSP"):
        out.extend(glob.glob(os.path.join(root, pat), recursive=True))
    return sorted(set(out))


class Rec:
    __slots__ = ("id", "parent", "off", "flags", "marker", "size", "depth",
                 "children", "parent_marker", "feat")

    def __init__(self, rid, parent, off, flags, marker, size):
        self.id, self.parent, self.off, self.flags = rid, parent, off, flags
        self.marker, self.size = marker, size
        self.depth = -1
        self.children = []


def load(path):
    d = pubcore.read_stream(path, "Contents")
    D = struct.unpack_from("<I", d, 0x16)[0]
    n, hwm = struct.unpack_from("<HH", d, D)
    recs = []
    for i in range(n):
        rid, par, off, fl = struct.unpack_from("<HHIH", d, D + 4 + 10 * i)
        recs.append((rid, par, off, fl))
    offs = sorted(r[2] for r in recs)
    nxt = {o: (offs[i + 1] if i + 1 < len(offs) else len(d)) for i, o in enumerate(offs)}
    out = []
    for rid, par, off, fl in recs:
        mk = struct.unpack_from("<H", d, off)[0]
        out.append(Rec(rid, par, off, fl, mk, nxt[off] - off))
    return d, hwm, out


def features(recs):
    """Return {name: {rec_id: bool}} structural predicates."""
    by_id = {r.id: r for r in recs}
    kids = collections.defaultdict(list)
    for r in recs:
        kids[r.parent].append(r)
    for p, cs in kids.items():
        cs.sort(key=lambda r: r.off)

    # depth by parent hop
    def depth(r, seen=()):
        if r.depth >= 0:
            return r.depth
        if r.parent not in by_id:
            r.depth = 0
            return 0
        r.depth = depth(by_id[r.parent]) + 1
        return r.depth
    for r in recs:
        depth(r)
    for r in recs:
        r.children = [c.id for c in kids.get(r.id, ())]
        p = by_id.get(r.parent)
        r.parent_marker = p.marker if p else None

    # has a text-run descendant (the 0x16 story container is the only owner)
    def desc_types(r):
        acc, stack = set(), [r]
        seen = set()
        while stack:
            cur = stack.pop()
            if cur.id in seen:
                continue
            seen.add(cur.id)
            acc.add(cur.marker)
            stack.extend(by_id[c] for c in cur.children if c in by_id)
        return acc

    feats = collections.defaultdict(dict)
    for r in recs:
        sibs = kids.get(r.parent, [])
        pos = sibs.index(r) if r in sibs else -1
        dt = desc_types(r)
        feats["has_children"][r.id] = bool(r.children)
        feats["is_leaf"][r.id] = not r.children
        feats["one_child"][r.id] = len(r.children) == 1
        feats["is_first_sibling"][r.id] = pos == 0
        feats["is_last_sibling"][r.id] = pos == len(sibs) - 1
        feats["only_child"][r.id] = len(sibs) == 1
        feats["depth1"][r.id] = r.depth == 1
        feats["is_page"][r.id] = r.marker == PAGE
        feats["is_document"][r.id] = r.marker == DOCUMENT
        feats["is_group"][r.id] = r.marker == GROUP
        feats["is_shape"][r.id] = r.marker in SHAPES
        feats["owns_text_runs"][r.id] = bool(dt & set(TEXT_RUNS))
        feats["under_story"][r.id] = r.parent_marker == STORY
        feats["under_page"][r.id] = r.parent_marker == PAGE
        feats["parent_is_shape"][r.id] = r.parent_marker in SHAPES
        feats["even_off"][r.id] = r.off % 2 == 0
        feats["md4_zero"][r.id] = r.off % 4 == 0
    return feats


def phi(a, b, c, d):
    n = a + b + c + d
    if n == 0:
        return 0.0
    den = (a + b) * (c + d) * (a + c) * (b + d)
    if den == 0:
        return 0.0
    return (a * d - b * c) / math.sqrt(den)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="p95/x")
    ap.add_argument("--per-marker", action="store_true")
    args = ap.parse_args()

    files = documents(args.root)
    allrecs = []
    hwm_ok = 0
    zero_ok = 0
    bitcount = collections.Counter()
    for f in files:
        d, hwm, recs = load(f)
        if hwm == max(r.id for r in recs):
            hwm_ok += 1
        D = struct.unpack_from("<I", d, 0x16)[0]
        n = len(recs)
        if d[D + 4 + 10 * n:D + 4 + 10 * n + 10] == b"\0" * 10:
            zero_ok += 1
        fs = features(recs)
        for r in recs:
            r.feat = {k: v[r.id] for k, v in fs.items()}
            allrecs.append(r)
        for r in recs:
            for bit in range(16):
                if r.flags >> bit & 1:
                    bitcount[bit] += 1

    nrec = len(allrecs)
    print("files %d, directory records %d (incl. %d .JSP documents)"
          % (len(files), nrec, sum(1 for f in files if f.lower().endswith(".jsp"))))
    print("idHwm == max(id): %d/%d   ten zero bytes after records: %d/%d"
          % (hwm_ok, len(files), zero_ok, len(files)))
    print("\nbit set frequency (over %d records):" % nrec)
    for bit in range(16):
        print("  bit %2d 0x%04x  %6d  %5.1f%%"
              % (bit, 1 << bit, bitcount[bit], 100.0 * bitcount[bit] / nrec))

    fnames = sorted(allrecs[0].feat)
    print("\n2x2 contingency: rows = feature, cols = bit.  cells a=both b=feat only "
          "c=bit only d=neither; phi")
    header = "%-18s" % "feature" + "".join("%6d" % b for b in range(16))
    print(header)
    print("-" * len(header))
    for fn in fnames:
        row = "%-18s" % fn
        for bit in range(16):
            a = b = c = dd = 0
            for r in allrecs:
                bitv = r.flags >> bit & 1
                fv = r.feat[fn]
                if fv and bitv:
                    a += 1
                elif fv:
                    b += 1
                elif bitv:
                    c += 1
                else:
                    dd += 1
            p = phi(a, b, c, dd)
            row += "%6.2f" % p
        print(row)

    variable = [b for b in range(16) if 0 < bitcount[b] < nrec]
    print("\nexact relations (bit <=> feature on every record), variable bits only:")
    found = False
    for fn in fnames:
        for bit in variable:
            a = sum(1 for r in allrecs if r.feat[fn] and r.flags >> bit & 1)
            b = sum(1 for r in allrecs if r.feat[fn] and not r.flags >> bit & 1)
            c = sum(1 for r in allrecs if not r.feat[fn] and r.flags >> bit & 1)
            if b == 0 and c == 0:
                print("  bit %2d %-18s EXACT  n=%d" % (bit, fn, a))
                found = True
            elif b == 0 or c == 0:
                tag = "feature=>bit" if b == 0 else "bit=>feature"
                print("  bit %2d %-7s %-18s a=%d b=%d c=%d" % (bit, tag, fn, a, b, c))
                found = True
    if not found:
        print("  none")

    print("\nrequested 2x2 tables (a = feat&bit, b = feat&!bit, c = !feat&bit, d = neither):")
    for fn in ("has_children", "is_last_sibling", "owns_text_runs", "is_page"):
        print("  %s" % fn)
        for bit in variable:
            a = sum(1 for r in allrecs if r.feat[fn] and r.flags >> bit & 1)
            b = sum(1 for r in allrecs if r.feat[fn] and not r.flags >> bit & 1)
            c = sum(1 for r in allrecs if not r.feat[fn] and r.flags >> bit & 1)
            dd = nrec - a - b - c
            print("    bit %2d  a=%-6d b=%-6d c=%-6d d=%-6d  phi=%+.2f  P(bit|feat)=%5.1f%%  P(bit|!feat)=%5.1f%%"
                  % (bit, a, b, c, dd, phi(a, b, c, dd),
                     100.0 * a / max(1, a + b), 100.0 * c / max(1, c + dd)))

    if args.per_marker:
        print("\nflags values per marker:")
        tab = collections.defaultdict(collections.Counter)
        for r in allrecs:
            tab[r.marker][r.flags] += 1
        for mk in sorted(tab):
            vals = ", ".join("%04X x%d" % (v, n) for v, n in
                             sorted(tab[mk].items(), key=lambda kv: -kv[1]))
            print("  0x%04X  %s" % (mk, vals))
    return 0


if __name__ == "__main__":
    sys.exit(main())
