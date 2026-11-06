"""Version-difference survey across Pub 95 / 97 / 97-deluxe / 98 corpora.

Writes a JSON blob to %TEMP%/p97_versiondiff.json and prints selected reports.

Usage: python tools/p97_versiondiff.py [report]
       report in {all,hdr,chunks,pairs,tlv,streams,disc}
"""
from __future__ import annotations
import sys, os, glob, json, struct, collections, tempfile, traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPORA = [
    ("p95", "p95/x"),
    ("p97", "p97/x"),
    ("p97deluxe", "p97deluxe/x"),
    ("p98", "p98/x"),
]

# payload width table from the container contract
ZERO = {0x78, 0x05, 0x08, 0x0A}
TWO = {0x10, 0x12, 0x18, 0x1A, 0x07}
FOUR = {0x20, 0x22, 0x58, 0x68, 0x70, 0xB8}
EIGHT = {0x28}
SIXTEEN = {0x38}
TWENTYFOUR = {0x48}
VAR = {0xC0, 0x80, 0x82, 0x88, 0x8A, 0x90, 0x98, 0xA0}


def tlv_pairs(data: bytes, limit: int = 4096):
    """Best-effort TLV scan: yields (id, type, offset) pairs found anywhere."""
    out = []
    i = 0
    n = min(len(data), limit)
    while i + 2 <= n:
        tid, ttype = data[i], data[i + 1]
        if ttype in ZERO:
            w = 0
        elif ttype in TWO:
            w = 2
        elif ttype in FOUR:
            w = 4
        elif ttype in EIGHT:
            w = 8
        elif ttype in SIXTEEN:
            w = 16
        elif ttype in TWENTYFOUR:
            w = 24
        elif ttype in VAR:
            if i + 6 > n:
                break
            w = 4 + struct.unpack_from("<I", data, i + 2)[0]
        else:
            i += 1
            continue
        if i + 2 + w > n:
            break
        out.append((tid, ttype))
        i += 2 + w
    return out


def survey():
    res = {}
    for ver, rel in CORPORA:
        root = os.path.join(ROOT, rel)
        files = sorted(glob.glob(os.path.join(root, "**", "*.PUB"), recursive=True)) + \
                sorted(glob.glob(os.path.join(root, "**", "*.pub"), recursive=True))
        seen = set()
        uni = []
        for f in files:
            if f.lower() in seen:
                continue
            seen.add(f.lower())
            uni.append(f)
        recs = []
        for f in uni:
            relpath = os.path.relpath(f, ROOT).replace("\\", "/")
            try:
                doc = pubcore.parse_contents(f)
            except Exception as e:
                recs.append({"path": relpath, "error": "%s: %s" % (type(e).__name__, e)})
                continue
            recs.append({
                "path": relpath,
                "base": os.path.basename(f).upper(),
                "ver": doc.version_magic,
                "len": len(doc.contents),
                "hdr": doc.header.hex(),
                "streams": doc.streams,
                "trailer": doc.trailer_offset,
                "n": len(doc.chunks),
                "chunks": [[c.id, c.parent, c.type_marker, c.size, c.offset] for c in doc.chunks],
                "tlv": sorted({p for c in doc.chunks for p in tlv_pairs(c.data)}),
                "tlv_by_type": _tlv_by_type(doc.chunks),
            })
        res[ver] = recs
    return res


def _tlv_by_type(chunks):
    m = collections.defaultdict(set)
    for c in chunks:
        key = "%04X" % c.type_marker
        for p in tlv_pairs(c.data):
            m[key].add(p)
    return {k: sorted(v) for k, v in m.items()}


def load():
    p = os.path.join(tempfile.gettempdir(), "p97_versiondiff.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    data = survey()
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return data


def report_hdr(data):
    for ver, recs in data.items():
        ok = [r for r in recs if "error" not in r]
        print("== %s  (%d files, %d parsed) ==" % (ver, len(recs), len(ok)))
        print("   distinct version_magic:", sorted({r["ver"] for r in ok}))
        nbyte = 0x22
        for i in range(nbyte):
            vals = collections.Counter()
            for r in ok:
                vals[int(r["hdr"][2 * i:2 * i + 2], 16)] += 1
            if i < 0x22 - 1:
                pass
            desc = " ".join("%02x:%d" % (v, c) for v, c in sorted(vals.items()))
            print("   %02x  n=%2d  %s" % (i, len(vals), desc))
        print()


def report_chunks(data):
    per = {}
    for ver, recs in data.items():
        cnt = collections.Counter()
        nfiles = collections.Counter()
        for r in recs:
            if "error" in r:
                continue
            seen = set()
            for cid, parent, tm, size, off in r["chunks"]:
                cnt[tm] += 1
                seen.add(tm)
            for tm in seen:
                nfiles[tm] += 1
        per[ver] = (cnt, nfiles)
    alltypes = sorted({t for cnt, _ in per.values() for t in cnt})
    print("marker  " + "  ".join("%-22s" % v for v in per))
    for t in alltypes:
        row = []
        for ver in per:
            cnt, nf = per[ver]
            row.append("%d/%df" % (cnt[t], nf[t]))
        print("0x%04X  %s" % (t, "  ".join("%-22s" % x for x in row)))


def report_streams(data):
    for ver, recs in data.items():
        top = collections.Counter()
        allnames = collections.Counter()
        for r in recs:
            if "error" in r:
                continue
            tops = set()
            for s in r["streams"]:
                kind, name, size = s.split("\t")
                if kind != "stream":
                    continue
                allnames[name] += 1
                tops.add(name.split("/")[0])
            for t in tops:
                top[t] += 1
        print("== %s ==" % ver)
        print("  top-level:", ", ".join("%s(%d)" % (k, v) for k, v in top.most_common()))
        print("  all stream paths:", ", ".join("%s(%d)" % (k, v) for k, v in allnames.most_common(30)))
        print()


def report_pairs(data):
    p95 = {r["base"]: r for r in data["p95"] if "error" not in r}
    p97 = {r["base"]: r for r in data["p97"] if "error" not in r}
    common = sorted(set(p95) & set(p97))
    print("%d common basenames" % len(common))
    for b in common:
        a, c = p95[b], p97[b]
        ca = collections.defaultdict(list)
        cc = collections.defaultdict(list)
        for cid, parent, tm, size, off in a["chunks"]:
            ca[tm].append(size)
        for cid, parent, tm, size, off in c["chunks"]:
            cc[tm].append(size)
        diffs = []
        for tm in sorted(set(ca) | set(cc)):
            sa, sc = ca.get(tm, []), cc.get(tm, [])
            if len(sa) != len(sc) or sa != sc:
                diffs.append((tm, sa, sc))
        if diffs:
            print(b, "| n95=%d n97=%d" % (a["n"], c["n"]))
            for tm, sa, sc in diffs:
                print("   0x%04X %s -> %s" % (tm, sa, sc))


def report_tlv(data):
    for ver, recs in data.items():
        byt = collections.defaultdict(set)
        for r in recs:
            if "error" in r:
                continue
            for k, v in r["tlv_by_type"].items():
                byt[k].update(tuple(x) for x in v)
        print("== %s ==" % ver)
        for k in sorted(byt):
            print("   0x%s: %s" % (k, " ".join("%02x/%02x" % (a, b) for a, b in sorted(byt[k]))))


def report_disc(data):
    print("stub")


if __name__ == "__main__":
    rep = sys.argv[1] if len(sys.argv) > 1 else "all"
    data = load()
    if rep in ("hdr", "all"):
        report_hdr(data)
    if rep in ("chunks", "all"):
        report_chunks(data)
    if rep in ("streams", "all"):
        report_streams(data)
