"""Publisher 95/97 shape record, chunk type marker 0x06 — field census + validator.

Reproduces every number in notes/p97/slices/shape_06.md.

Usage:
    python tools/p97_shape06.py [corpus ...]      # default p97/x p95/x
    python tools/p97_shape06.py --quiet p97/x     # structural check only

Structural checks (exit 1 on the first violation):
  * every 0x06 chunk is 53 bytes in the 95/97 family
  * bytes +2..+3 == 39 35 (u16 0x3539), i.e. +3 == record length
  * the geometry quad has (x1 > x0) and (y1 > y0) whenever it is not all zero
"""
from __future__ import annotations

import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore  # noqa: E402

TAG = b"\x39\x35"
LEN_97 = 53
EMU_PER_IN = 914400


def corpus_files(corpora):
    out = []
    for c in corpora:
        for pat in ("*.PUB", "*.pub"):
            out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))


def load(corpora):
    recs = []
    for f in corpus_files(corpora):
        try:
            doc = pubcore.parse_contents(f)
        except Exception:
            continue
        parent_types = {c.id: c.type_marker for c in doc.chunks}
        for c in doc.chunks:
            if c.type_marker == 0x06:
                recs.append((f, doc, c, parent_types.get(c.parent)))
    return recs


def check(recs, strict=True):
    bad = []
    for f, doc, c, pt in recs:
        if len(c.data) != LEN_97:
            bad.append((f, c.id, "size %d != %d" % (len(c.data), LEN_97)))
            continue
        if c.data[2:4] != TAG:
            bad.append((f, c.id, "tag %s != %s" % (c.data[2:4].hex(), TAG.hex())))
            continue
        q = struct.unpack_from("<iiii", c.data, 6)
        if q != (0, 0, 0, 0) and not (q[2] > q[0] and q[3] > q[1]):
            bad.append((f, c.id, "degenerate quad %s" % (q,)))
    return bad


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    quiet = "--quiet" in argv
    corpora = args or ["p97/x", "p95/x"]
    recs = load(corpora)
    print("corpora=%s files=%d 0x06 chunks=%d" % (corpora, len({r[0] for r in recs}), len(recs)))
    bad = check(recs)
    print("structural violations: %d" % len(bad))
    for b in bad[:10]:
        print("   ", b)
    if quiet:
        return 1 if bad else 0
    if bad:
        return 1

    print("\nsizes:", collections.Counter(len(r[2].data) for r in recs).most_common())
    print("tag  :", collections.Counter(r[2].data[2:4].hex() for r in recs).most_common())
    pn = {0x0F: "GROUP", 0x14: "PAGE"}
    print("parent:", collections.Counter(pn.get(r[3], r[3]) for r in recs).most_common())

    print("\n-- per-byte domains (53-byte record) --")
    for o in range(53):
        c = collections.Counter(r[2].data[o] for r in recs)
        print("  +%02x n=%3d %s%s" % (o, len(c), ", ".join("%02x:%d" % kv for kv in c.most_common(8)),
                                      " ..." if len(c) > 8 else ""))

    print("\n-- width-2/4 candidates --")
    for off, w in ((0x04, 2), (0x22, 2), (0x25, 2), (0x18, 4), (0x1C, 4), (0x2D, 4), (0x31, 4)):
        fmt = "<H" if w == 2 else "<I"
        c = collections.Counter(struct.unpack_from(fmt, r[2].data, off)[0] for r in recs)
        print("  %s@%#04x : %3d distinct  %s" % (
            "u%d" % (w * 8), off, len(c),
            ", ".join("%d:%d" % kv for kv in c.most_common(10))))

    print("\n-- geometry --")
    nz = zero = inpage = ordered = 0
    outside = collections.Counter()
    for f, doc, c, pt in recs:
        dc = next((x for x in doc.chunks if x.type_marker == 0x15), None)
        if not dc or len(dc.data) < 0x1C:
            continue
        W, H = struct.unpack_from("<II", dc.data, 0x14)
        q = struct.unpack_from("<iiii", c.data, 6)
        if q == (0, 0, 0, 0):
            zero += 1
            continue
        nz += 1
        ordered += (q[2] > q[0] and q[3] > q[1])
        ok = q[0] >= 0 and q[1] >= 0 and q[2] <= W and q[3] <= H
        inpage += ok
        if not ok:
            outside["x0<0"] += q[0] < 0
            outside["y0<0"] += q[1] < 0
            outside["x1>W"] += q[2] > W
            outside["y1>H"] += q[3] > H
    print("  zero quad %d ; nonzero %d ; x1>x0 and y1>y0 %d (%.1f%%) ; fully inside page %d (%.1f%%)" % (
        zero, nz, ordered, 100.0 * ordered / max(nz, 1), inpage, 100.0 * inpage / max(nz, 1)))
    print("  outside breakdown:", dict(outside))

    print("\n-- rotation (+0x04, u16) --")
    rot = collections.Counter(struct.unpack_from("<H", r[2].data, 4)[0] for r in recs)
    print("  distinct=%d nonzero=%d max=%d  top: %s" % (
        len(rot), sum(v for k, v in rot.items() if k), max(rot),
        ", ".join("%d:%d" % kv for kv in rot.most_common(10))))

    print("\n-- colour descriptor +0x18..+0x1B / +0x1C..+0x1F --")
    for base in (0x18, 0x1C):
        fam = collections.defaultdict(collections.Counter)
        for r in recs:
            b = r[2].data
            fam[b[base + 3]][(b[base], b[base + 1], b[base + 2])] += 1
        print("  slot %#04x modes: %s" % (base, {hex(m): sum(v.values()) for m, v in sorted(fam.items())}))
        for m in sorted(fam):
            if m == 0x20:
                print("     mode 0x20 RGB triples:", [bytes(t).hex() for t, _ in fam[m].most_common(6)])

    print("\n-- fill type +0x20 vs colour +0x18 --")
    tab = collections.defaultdict(lambda: [0, 0])
    for r in recs:
        b = r[2].data
        ft = b[0x20]
        tab[ft][0] += 1
        tab[ft][1] += struct.unpack_from("<I", b, 0x18)[0] != 0
    for ft in sorted(tab):
        n, col = tab[ft]
        print("  +0x20=%#04x n=%3d  colour!=0 in %d (%.0f%%)" % (ft, n, col, 100.0 * col / n))
    z = [r for r in recs if r[2].data[0x20] == 0]
    print("  records with +0x20==0 and u32@+0x22 != 0: %d/%d" % (
        sum(1 for r in z if struct.unpack_from("<I", r[2].data, 0x22)[0] != 0), len(z)))
    print("  +0x2A constant: %s" % collections.Counter(r[2].data[0x2A] for r in recs).most_common(3))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
