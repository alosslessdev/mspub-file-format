"""Analysis of Contents chunk markers 0x0002 and 0x0003 (throwaway slice tool).

Usage:
    python tools/p97_shape0203.py census
    python tools/p97_shape0203.py fields      [corpus ...]
    python tools/p97_shape0203.py tags        [corpus ...]
    python tools/p97_shape0203.py tlv         [corpus ...]
    python tools/p97_shape0203.py tail        [corpus ...]
    python tools/p97_shape0203.py geom        [corpus ...]

Corpora default to p97/x and p95/x.
"""
from __future__ import annotations

import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import pubdump

BASE = 126  # fixed-record size of both markers


def files(corpus):
    return sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))


def records(corpus):
    """Yield (path, chunk, doc) for 0x02 and 0x03 chunks."""
    for f in files(corpus):
        try:
            doc = pubcore.parse_contents(f)
        except Exception:
            continue
        for c in doc.chunks:
            if c.type_marker in (2, 3):
                yield f, c, doc


def doc_size(doc):
    for c in doc.chunks:
        if c.type_marker == 0x15:
            return (struct.unpack_from("<I", c.data, 0x14)[0],
                    struct.unpack_from("<I", c.data, 0x18)[0])
    return (None, None)


def cmd_census(corpora):
    for corpus in corpora:
        sizes = collections.Counter()
        n = 0
        for f, c, doc in records(corpus):
            sizes[(c.type_marker, len(c.data))] += 1
            n += 1
        print("== %s: %d chunks" % (corpus, n))
        for k in sorted(sizes):
            print("   marker %#06x size %4d  n=%d" % (k[0], k[1], sizes[k]))


def cmd_tags(corpora):
    for corpus in corpora:
        cnt = collections.Counter()
        fset = collections.defaultdict(set)
        for f, c, doc in records(corpus):
            tag = struct.unpack_from("<H", c.data, 2)[0]
            cnt[(c.type_marker, tag)] += 1
            fset[tag].add(os.path.basename(f))
        print("== %s" % corpus)
        for k in sorted(cnt):
            print("   marker %#06x tag %#06x  chunks=%4d files=%3d" %
                  (k[0], k[1], cnt[k], len(fset[k[1]])))
        for tag in sorted(fset):
            if len(fset[tag]) <= 20:
                print("   rare tag %#06x files: %s" %
                      (tag, ", ".join(sorted(fset[tag]))))


def cmd_fields(corpora):
    for corpus in corpora:
        recs = [(f, c, doc) for f, c, doc in records(corpus)]
        print("== %s  n=%d" % (corpus, len(recs)))
        print(" off  | u8 distinct/values                     | u16 distinct  min..max        | u32 const?")
        for off in range(0, BASE):
            b8 = collections.Counter(c.data[off] for f, c, doc in recs)
            if len(b8) == 1:
                s8 = "const %#04x" % next(iter(b8))
            else:
                s8 = "%2d %s" % (len(b8), ",".join("%02x" % v for v in sorted(b8)[:8]))
            if off + 2 <= BASE:
                b16 = collections.Counter(struct.unpack_from("<H", c.data, off)[0]
                                          for f, c, doc in recs)
                s16 = "%3d  %6d..%-6d" % (len(b16), min(b16), max(b16))
            else:
                s16 = " " * 20
            if off + 4 <= BASE:
                b32 = collections.Counter(struct.unpack_from("<I", c.data, off)[0]
                                          for f, c, doc in recs)
                s32 = ("CONST %#x" % next(iter(b32))) if len(b32) == 1 else "%d vals" % len(b32)
            else:
                s32 = ""
            print(" %#04x | %-40s | %-29s | %s" % (off, s8, s16, s32))


def cmd_tlv(corpora):
    for corpus in corpora:
        per = collections.defaultdict(list)
        for f, c, doc in records(corpus):
            per[c.type_marker].append(c)
        print("== %s" % corpus)
        for tm in sorted(per):
            cs = per[tm]
            print("  marker %#06x n=%d" % (tm, len(cs)))
            best = []
            for start in range(0, 64):
                ex = tr = fl = 0
                for c in cs:
                    if len(c.data) <= start:
                        continue
                    b, consumed = pubdump.walk_blocks(c.data[start:], 0)
                    if not b or b[-1][4] != "TERMINATOR":
                        fl += 1
                    elif start + consumed == len(c.data):
                        ex += 1
                    else:
                        tr += 1
                if ex:
                    best.append((ex, start, tr, fl))
            if not best:
                print("     no start offset terminates exactly (0 exact over 0..63)")
            for ex, start, tr, fl in sorted(best, reverse=True)[:3]:
                print("     start=+%d exact=%d trailing=%d fail=%d" % (start, ex, tr, fl))


def cmd_tail(corpora):
    for corpus in corpora:
        print("== %s" % corpus)
        rows = []
        for f, c, doc in records(corpus):
            if c.type_marker != 3 or len(c.data) <= BASE:
                continue
            n = (len(c.data) - BASE) // 8
            c74 = struct.unpack_from("<H", c.data, 0x74)[0]
            c76 = struct.unpack_from("<H", c.data, 0x76)[0]
            u16_16 = struct.unpack_from("<H", c.data, 0x16)[0]
            rows.append((f, c, n, c74, c76, u16_16))
        print("   %d chunks with a tail" % len(rows))
        for f, c, n, c74, c76, u16_16 in rows:
            print("   %s id=%#06x size=%4d N=(size-126)/8=%3d hdr+0x74=%3d +0x76=%3d u16@0x16=%d" %
                  (os.path.basename(f), c.id, len(c.data), n, c74, c76, u16_16))
        # column ranges over all entries
        colA = collections.Counter()
        colB = collections.Counter()
        colC = []
        for f, c, n, c74, c76, u16_16 in rows:
            t = c.data[BASE:]
            for i in range(0, len(t) - 7, 8):
                a, b, cc = struct.unpack_from("<HHI", t, i)
                colA[a] += 1
                colB[b] += 1
                colC.append(cc)
        if colA:
            print("   entries total=%d" % len(colC))
            print("   colA (u16@+0): distinct=%d min=%d max=%d" %
                  (len(colA), min(colA), max(colA)))
            print("   colB (u16@+2): distinct=%d min=%d max=%d values=%s" %
                  (len(colB), min(colB), max(colB),
                   sorted(colB)[:12]))
            print("   colC (u32@+4): min=%d max=%d" % (min(colC), max(colC)))


def cmd_geom(corpora):
    for corpus in corpora:
        print("== %s" % corpus)
        tot = collections.Counter()
        ok = collections.Counter()
        bypar = collections.Counter()
        okpar = collections.Counter()
        negx = 0
        for f, c, doc in records(corpus):
            W, H = doc_size(doc)
            if W is None:
                continue
            xs, ys, xe, ye = struct.unpack_from("<iiii", c.data, 6)
            zero = (xs, ys, xe, ye) == (0, 0, 0, 0)
            tot[c.type_marker] += 1
            if not zero and xs < 0:
                negx += 1
            good = (not zero and 0 <= xs and 0 <= ys and xe >= xs and ye >= ys
                    and xe <= W and ye <= H)
            if good:
                ok[c.type_marker] += 1
            p = doc.by_id(c.parent)
            pt = p.type_marker if p else -1
            bypar[(c.type_marker, pt)] += 1
            if good:
                okpar[(c.type_marker, pt)] += 1
        for tm in sorted(tot):
            print("   marker %#06x n=%d quad-in-page=%d (%.1f%%)" %
                  (tm, tot[tm], ok[tm], 100.0 * ok[tm] / tot[tm]))
        print("   negative xs (non-zero quads): %d" % negx)
        for k in sorted(bypar):
            print("     parent %#06x: %d/%d (%.1f%%)" %
                  (k[1], okpar[k], bypar[k], 100.0 * okpar[k] / bypar[k]))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    corpora = sys.argv[2:] or ["p97/x", "p95/x"]
    {"census": cmd_census, "fields": cmd_fields, "tags": cmd_tags,
     "tlv": cmd_tlv, "tail": cmd_tail, "geom": cmd_geom}[cmd](corpora)


if __name__ == "__main__":
    main()
