"""Harvest LOGO (0x31) and companion (0x32) chunks from every corpus.

Usage:
  python tools/p98_logo.py dump  [out.json]      # full record dump
  python tools/p98_logo.py stats                 # per-offset differential
  python tools/p98_logo.py graph                 # parent-graph census
  python tools/p98_logo.py sizes
"""
from __future__ import annotations

import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPORA = [
    ("p95", os.path.join(ROOT, "p95", "x")),
    ("p97", os.path.join(ROOT, "p97", "ext2")),
    ("p97deluxe", os.path.join(ROOT, "p97deluxe", "x")),
    ("p98", os.path.join(ROOT, "p98", "x")),
]


def pub_files(top):
    out = []
    for dirpath, _dirs, files in os.walk(top):
        for f in files:
            if f.lower().endswith(".pub"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def harvest(want=(0x31, 0x32)):
    recs = []
    for corpus, top in CORPORA:
        if not os.path.isdir(top):
            continue
        for path in pub_files(top):
            try:
                doc = pubcore.parse_contents(path)
            except Exception as exc:  # noqa: BLE001
                print("SKIP %s: %s" % (path, exc), file=sys.stderr)
                continue
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            for c in doc.chunks:
                if c.type_marker not in want:
                    continue
                recs.append({
                    "corpus": corpus,
                    "file": rel,
                    "chunk_index": c.index,
                    "id": c.id,
                    "parent": c.parent,
                    "seq_skip": c.seq_skip,
                    "offset": c.offset,
                    "size": c.size,
                    "type": c.type_marker,
                    "hex": c.data.hex(),
                })
    return recs


def load(path="out/logo.json"):
    with open(os.path.join(ROOT, path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def cmd_dump(argv):
    recs = harvest()
    out = argv[0] if argv else "out/logo.json"
    full = os.path.join(ROOT, out)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        json.dump(recs, fh)
    cnt = collections.Counter((r["corpus"], r["type"]) for r in recs)
    for k in sorted(cnt):
        print(k, cnt[k])
    print("total", len(recs), "->", out)


def cmd_sizes(argv):
    recs = harvest() if not os.path.exists(os.path.join(ROOT, "out/logo.json")) else load()
    per = collections.defaultdict(collections.Counter)
    for r in recs:
        per[(r["corpus"], r["type"])][r["size"]] += 1
    for k in sorted(per):
        print(k, dict(sorted(per[k].items())))


def cmd_stats(argv):
    recs = load(argv[0]) if argv else load()
    for typ in (0x31, 0x32):
        sub = [r for r in recs if r["type"] == typ]
        if not sub:
            continue
        print("=" * 70)
        print("type 0x%02x  n=%d  sizes=%s" % (
            typ, len(sub), dict(sorted(collections.Counter(r["size"] for r in sub).items()))))
        maxlen = max(len(r["hex"]) // 2 for r in sub)
        print("maxlen", maxlen)
        rows = []
        for off in range(maxlen):
            vals = collections.Counter()
            miss = 0
            for r in sub:
                b = bytes.fromhex(r["hex"])
                if off < len(b):
                    vals[b[off]] += 1
                else:
                    miss += 1
            rows.append((off, len(vals), sorted(vals), miss))
        for off, dv, vals, miss in rows:
            if dv == 1 and not miss:
                print("+%02x  const 0x%02x  (n=%d)" % (off, vals[0], len(sub)))
            elif dv <= 6:
                print("+%02x  u8  d=%d  %s%s" % (
                    off, dv, " ".join("%02x:%d" % (v, _c(sub, off, v)) for v in vals),
                    ("  short:%d" % miss) if miss else ""))
            else:
                print("+%02x  u8  d=%d  (wide)%s" % (off, dv, ("  short:%d" % miss) if miss else ""))


def _c(sub, off, val):
    n = 0
    for r in sub:
        b = bytes.fromhex(r["hex"])
        if off < len(b) and b[off] == val:
            n += 1
    return n


def cmd_graph(argv):
    recs = harvest() if not os.path.exists(os.path.join(ROOT, "out/logo.json")) else load()
    # per-file graph
    files = collections.defaultdict(list)
    for r in recs:
        files[r["file"]].append(r)
    childcnt = collections.Counter()
    kinds = collections.Counter()
    tot31 = tot32 = 0
    for f, rs in sorted(files.items()):
        l31 = [r for r in rs if r["type"] == 0x31]
        l32 = [r for r in rs if r["type"] == 0x32]
        tot31 += len(l31)
        tot32 += len(l32)
        for a in l31:
            kids = [b for b in l32 if b["parent"] == a["id"]]
            childcnt[len(kids)] += 1
        kinds[(len(l31), len(l32))] += 1
    print("31 total", tot31, "32 total", tot32)
    print("children-per-31", dict(sorted(childcnt.items())))
    print("(n31,n32) per file histogram:", dict(sorted(kinds.items())))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dump"
    rest = sys.argv[2:]
    {"dump": cmd_dump, "sizes": cmd_sizes, "stats": cmd_stats, "graph": cmd_graph}[cmd](rest)
