"""TLV-block inventory scan for the Publisher 95/97/98 chunk model.

For every chunk of every corpus document this tool

 1. walks the payload as a `{u8 id, u8 type, payload}` TLV list (libmspub
    type->length table, see pubdump.TYPE_LEN) starting at every offset 0..64,
 2. keeps a start offset only when the walk terminates on a `00 00` doublet AND
    consumes exactly to the end of the chunk,
 3. inventories every block of every accepted walk,
 4. additionally runs an exhaustive dynamic-programming check over *every* start
    offset (0..len-2) so that "no start works" is a proof, not a sampling gap,
 5. records every abort caused by an unknown `type` byte, with a sample offset.

Outputs a machine-sortable TSV (default notes/p98/tlv_observed.tsv) plus a
human summary on stdout.

TSV columns: chunk_type  start_offset  id  type  len  n  extra

`extra` starts with `kind=`; four row kinds exist:

  kind=block         id/type/len of one TLV block, aggregated over every accepted
                     walk at that start offset.  extra also carries
                     ex=<exact>/<chunks>, tailmed, realmed, verdict, nv, top.
  kind=block-var     same, but len is variable: the `len` column reads `var` and
                     extra carries lens=<observed payload lengths>.
  kind=abort         a walk that stopped on an unknown type byte.  id/len are `-`,
                     type is the offending byte, extra carries sample=<file>@<abs>.
  kind=type-summary  one row per chunk type: best start offset and all ratios.
  kind=no-exact-walk the chunk type has no exact-terminating walk at any start
                     in 0..64 (and, per `dp_sub=`, no substantive parse at any
                     start at all).

Usage:
    python tools/p98_tlvscan.py                     # all four corpora
    python tools/p98_tlvscan.py --corpora p95/x,p98/x
    python tools/p98_tlvscan.py --out /tmp/x.tsv --quiet
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import statistics
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import pubdump

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CORPORA = ["p95/x", "p97/ext2", "p97deluxe/x", "p98/x"]
DEFAULT_OUT = os.path.join(ROOT, "notes", "p98", "tlv_observed.tsv")
MAX_START = 64
TYPE_LEN = pubdump.TYPE_LEN
VAR_TYPES = {t for t, n in TYPE_LEN.items() if n is None}


# --------------------------------------------------------------------------- #
# walking
# --------------------------------------------------------------------------- #
def walk_exact(data: bytes, start: int):
    """Return the block list if a TLV walk from `start` ends exactly at len(data)."""
    blocks, consumed = pubdump.walk_blocks(data[start:], start)
    if not blocks:
        return None
    if blocks[-1][4] != "TERMINATOR":
        return None
    if start + consumed != len(data):
        return None
    return blocks


def dp_scan(data: bytes):
    """Exhaustive check: ok[s] = a TLV walk from s ends exactly at len(data).

    Mirrors pubdump.walk_blocks semantics (terminator first, fixed widths,
    variable = u32 payload length >= 4).  `real[s]` is the number of non
    terminator blocks on that walk.  O(len) per chunk.
    """
    L = len(data)
    ok = [False] * (L + 1)
    real = [0] * (L + 1)
    for s in range(L - 2, -1, -1):
        if data[s] == 0 and data[s + 1] == 0:
            ok[s] = s + 2 == L
            real[s] = 0
            continue
        t = data[s + 1]
        if t not in TYPE_LEN:
            continue
        w = TYPE_LEN[t]
        if w is None:
            if s + 6 > L:
                continue
            n = struct.unpack_from("<I", data, s + 2)[0]
            if n < 4:
                continue
            nxt = s + 2 + n
        else:
            nxt = s + 2 + w
        if nxt >= L or not ok[nxt]:
            continue
        ok[s] = True
        real[s] = real[nxt] + 1
    return ok, real


# --------------------------------------------------------------------------- #
# corpus
# --------------------------------------------------------------------------- #
def corpus_files(corpus: str):
    return sorted(f for f in glob.glob(os.path.join(corpus, "**", "*"), recursive=True)
                  if f.lower().endswith(".pub") and os.path.isfile(f))


def load(corpora):
    docs, failed = [], []
    for corpus in corpora:
        for f in corpus_files(corpus):
            try:
                docs.append((f, pubcore.parse_contents(f)))
            except Exception as exc:  # unreadable / not a Publisher document
                failed.append((f, repr(exc)))
    return docs, failed


# --------------------------------------------------------------------------- #
# scan
# --------------------------------------------------------------------------- #
def scan(docs, max_start=MAX_START):
    """Return (block_rows, abort_rows, summary_rows, report)."""
    # (chunk_type, start) -> counters
    stat = collections.defaultdict(lambda: {
        "tot": 0, "ex": 0, "ex2": 0, "ex3": 0,
        "tail": [], "real": [], "blocks": collections.Counter(),
        "values": collections.defaultdict(collections.Counter),
        "bsample": {},
    })
    chunk_n = collections.Counter()          # chunk_type -> chunk count
    dp_any = collections.Counter()           # chunk_type -> chunks with any exact start
    dp_sub = collections.Counter()           # chunk_type -> chunks with a substantive start
    dp_sub_events = collections.Counter()    # chunk_type -> #(chunk,start) substantive
    abort = collections.defaultdict(lambda: {"n": 0, "starts": set(), "sample": None})
    tot_chunks = 0
    tot_bytes = 0

    for path, doc in docs:
        for c in doc.chunks:
            data = c.data
            tm = c.type_marker
            L = len(data)
            tot_chunks += 1
            tot_bytes += L
            chunk_n[tm] += 1
            base = c.offset

            # --- exhaustive existence test over every start offset ----------
            ok, real = dp_scan(data)
            starts_ok = [s for s in range(L) if ok[s]]
            if starts_ok:
                dp_any[tm] += 1
            sub = [s for s in starts_ok if real[s] >= 2 and L - s >= 16]
            if sub:
                dp_sub[tm] += 1
                dp_sub_events[tm] += len(sub)

            # --- 0..max_start sweep ----------------------------------------
            for start in range(max_start + 1):
                if L <= start:
                    break
                blocks = walk_exact(data, start)
                st = stat[(tm, start)]
                st["tot"] += 1
                if blocks is None:
                    # record the unknown type we died on (if any)
                    b, _ = pubdump.walk_blocks(data[start:], start)
                    if b and b[-1][4].startswith("unknown"):
                        t = b[-1][2]
                        a = abort[(tm, t)]
                        a["n"] += 1
                        a["starts"].add(start)
                        if a["sample"] is None:
                            a["sample"] = (path, base + start)
                    continue
                st["ex"] += 1
                rblk = [x for x in blocks if x[4] == ""]
                if len(blocks) >= 2:
                    st["ex2"] += 1
                if len(blocks) >= 3:
                    st["ex3"] += 1
                st["tail"].append(L - start)
                st["real"].append(len(rblk))
                for boff, bid, btype, payload, err in blocks:
                    if err:
                        continue
                    if btype in VAR_TYPES:
                        key = (bid, btype, "var")
                        if payload is not None:
                            st["values"][key][len(payload)] += 1
                    else:
                        plen = len(payload) if payload is not None else -1
                        key = (bid, btype, plen)
                    st["blocks"][key] += 1
                    if key not in st["bsample"]:
                        st["bsample"][key] = (path, base + boff)
                    if payload is not None and len(payload) in (1, 2, 4):
                        st["values"][key][int.from_bytes(payload, "little")] += 1

    return stat, abort, chunk_n, dp_any, dp_sub, dp_sub_events, tot_chunks, tot_bytes


# --------------------------------------------------------------------------- #
# rows
# --------------------------------------------------------------------------- #
def _top(counter, k=5):
    return ";".join("%d:%d" % (v, n) for v, n in counter.most_common(k)) or "-"


def build_rows(stat, abort, chunk_n, dp_any, dp_sub, dp_sub_events):
    rows = []  # (chunk_type, sort_start, id, type, len, n, extra)

    # per chunk type: best start offset (most exact, then most ex3, then lowest)
    best = {}
    for tm in chunk_n:
        cands = [(v["ex"], v["ex3"], -s, s) for (t2, s), v in stat.items() if t2 == tm]
        best[tm] = max(cands)[3] if cands else None

    for (tm, start), st in sorted(stat.items()):
        if st["ex"] == 0:
            continue
        tail_med = statistics.median(st["tail"]) if st["tail"] else 0
        real_med = statistics.median(st["real"]) if st["real"] else 0
        substantive = (real_med >= 2 and tail_med >= 16)
        verdict = "substantive" if substantive else "tail-artifact"
        for (bid, btype, plen), n in sorted(
                st["blocks"].items(),
                key=lambda kv: (str(kv[0][2]), kv[0][0], kv[0][1])):
            vals = st["values"].get((bid, btype, plen))
            extra = ["kind=block-var" if plen == "var" else "kind=block"]
            extra.append("ex=%d/%d" % (st["ex"], st["tot"]))
            extra.append("ex2=%d" % st["ex2"])
            extra.append("ex3=%d" % st["ex3"])
            extra.append("tailmed=%g" % tail_med)
            extra.append("realmed=%g" % real_med)
            extra.append("verdict=%s" % verdict)
            if plen == "var":
                extra.append("lens=%s" % ",".join(str(x) for x in sorted(vals or {})))
            extra.append("nv=%d" % (len(vals) if vals else 0))
            extra.append("top=%s" % _top(vals) if vals else "top=-")
            smp = st["bsample"].get((bid, btype, plen))
            if smp:
                extra.append("sample=%s@0x%x" % (os.path.relpath(smp[0], ROOT), smp[1]))
            rows.append(("0x%04x" % tm, "%d" % start, "0x%02x" % bid, "0x%02x" % btype,
                         "var" if plen == "var" else "%d" % plen, "%d" % n,
                         " ".join(extra)))

    for (tm, t), a in sorted(abort.items()):
        sample = a["sample"]
        extra = ("kind=abort why=unknown-type nstarts=%d ctype=%s sample=%s@0x%x"
                 % (len(a["starts"]), "0x%04x" % tm,
                    os.path.relpath(sample[0], ROOT), sample[1]))
        rows.append(("0x%04x" % tm, "-", "-", "0x%02x" % t, "-", "%d" % a["n"], extra))

    for tm in sorted(chunk_n):
        b = best.get(tm)
        st = stat.get((tm, b), None) if b is not None else None
        if st is None or st["ex"] == 0:
            rows.append(("0x%04x" % tm, "-", "-", "-", "-", "%d" % chunk_n[tm],
                         "kind=no-exact-walk chunks=%d dp_any=%d dp_sub=%d"
                         % (chunk_n[tm], dp_any[tm], dp_sub[tm])))
            continue
        med_tail = statistics.median(st["tail"]) if st["tail"] else 0
        med_real = statistics.median(st["real"]) if st["real"] else 0
        verdict = "not-a-tlv-list" if dp_sub[tm] == 0 else "mixed"
        rows.append(("0x%04x" % tm, "%d" % b, "-", "-", "-", "%d" % chunk_n[tm],
                     ("kind=type-summary chunks=%d exact=%d ex2=%d ex3=%d tailmed=%g "
                      "realmed=%g dp_any=%d dp_sub=%d dp_subevents=%d verdict=%s")
                     % (chunk_n[tm], st["ex"], st["ex2"], st["ex3"],
                        med_tail, med_real, dp_any[tm], dp_sub[tm],
                        dp_sub_events[tm], verdict)))
    return rows


def write_tsv(rows, out_path):
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write("chunk_type\tstart_offset\tid\ttype\tlen\tn\textra\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def print_report(stat, abort, chunk_n, dp_any, dp_sub, dp_sub_events, docs, failed,
                 tot_chunks, tot_bytes):
    print("documents parsed: %d  failed: %d  chunks: %d  chunk bytes: %d"
          % (len(docs), len(failed), tot_chunks, tot_bytes))
    for f, e in failed[:10]:
        print("  FAILED", f, e)
    print()
    print("%-8s %6s %5s %7s %6s %6s %6s %7s %6s %s"
          % ("chunk", "n", "start", "exact", "ex2", "ex3", "dp_any", "dp_sub", "ev", "verdict"))
    for tm in sorted(chunk_n):
        cands = [(v["ex"], v["ex3"], -s, s) for (t2, s), v in stat.items()
                 if t2 == tm and v["ex"] > 0]
        if not cands:
            print("%-8s %6d %5s %7s %6s %6s %6d %6d %6d %s"
                  % ("0x%04x" % tm, chunk_n[tm], "-", "0", "0", "0",
                     dp_any[tm], dp_sub[tm], dp_sub_events[tm], "no-exact-walk"))
            continue
        ex, ex3, _, s = max(cands)
        st = stat[(tm, s)]
        verdict = "not-a-tlv-list" if dp_sub[tm] == 0 else "mixed"
        print("%-8s %6d %5d %4d/%-4d %6d %6d %7d %6d %6d %s"
              % ("0x%04x" % tm, chunk_n[tm], s, ex, st["tot"], st["ex2"], st["ex3"],
                 dp_any[tm], dp_sub[tm], dp_sub_events[tm], verdict))

    print()
    utypes = collections.defaultdict(lambda: {"n": 0, "tms": set(), "sample": None})
    for (tm, t), a in abort.items():
        u = utypes[t]
        u["n"] += a["n"]
        u["tms"].add(tm)
        if u["sample"] is None:
            u["sample"] = a["sample"]
    print("unknown-type aborts: %d events, %d distinct type values, %d (chunk_type,type) pairs"
          % (sum(a["n"] for a in abort.values()), len(utypes), len(abort)))
    for t in sorted(utypes):
        u = utypes[t]
        print("  type 0x%02x  events=%-7d chunk_types=%-3d sample=%s@0x%x"
              % (t, u["n"], len(u["tms"]),
                 os.path.relpath(u["sample"][0], ROOT), u["sample"][1]))


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", default=",".join(DEFAULT_CORPORA))
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--max-start", type=int, default=MAX_START)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    corpora = [os.path.join(ROOT, c.strip()) for c in a.corpora.split(",") if c.strip()]
    docs, failed = load(corpora)
    if not docs:
        print("no documents parsed", file=sys.stderr)
        return 1
    stat, abort, chunk_n, dp_any, dp_sub, dp_sub_events, tot_chunks, tot_bytes = scan(
        docs, a.max_start)
    rows = build_rows(stat, abort, chunk_n, dp_any, dp_sub, dp_sub_events)
    write_tsv(rows, a.out)
    if not a.quiet:
        print_report(stat, abort, chunk_n, dp_any, dp_sub, dp_sub_events,
                     docs, failed, tot_chunks, tot_bytes)
        print()
    print("wrote %s (%d rows)" % (a.out, len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
