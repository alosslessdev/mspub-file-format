"""Throwaway analyzer v2: directory semantics + inventory, all corpora."""
from __future__ import annotations
import sys, os, glob, collections, json
sys.path.insert(0, os.path.dirname(__file__))
import pubcore

CORPORA = ["p95/x", "p97/x", "p97deluxe/x", "p98/x"]


def files(root):
    out = []
    for dirpath, _dn, fn in os.walk(root):
        for f in fn:
            if f.lower().endswith(".pub"):
                out.append(os.path.join(dirpath, f))
    return sorted(out)


def analyze(root):
    R = collections.defaultdict(int)
    types = {}
    seq = collections.Counter()
    seq_mod8 = collections.Counter()
    modal = collections.defaultdict(collections.Counter)   # type -> a
    fails = []
    depth_hist = collections.Counter()
    root_types = collections.Counter()
    parent_sentinel = collections.Counter()
    id_min = 10**9; id_max = -1
    firstoff_delta = collections.Counter()
    trailing = collections.Counter()
    term_form = collections.Counter()
    order_sorted_by_off = 0
    order_sorted_by_id = 0
    preorder = 0
    nfiles = 0
    id_gap_files = []
    for path in files(root):
        try:
            doc = pubcore.parse_contents(path)
        except Exception as e:
            fails.append((path, str(e))); continue
        nfiles += 1
        R["version_%02x" % doc.version_magic] += 1
        ch = doc.chunks
        R["chunks"] += len(ch)
        R["files"] += 1
        d = doc.contents
        # terminator record after count
        end = doc.trailer_offset + 2 + 10 * doc.directory_count
        if end + 10 <= len(d):
            import struct
            term = struct.unpack_from("<HHHI", d, end)
            term_form["id0" if term[1] == 0 else "id_nonzero"] += 1
            if term[1] == 0:
                term_form["a=0x%04x" % term[0]] += 1
                term_form["parent0_off0" if (term[2] == 0 and term[3] == 0) else "parent/off nonzero"] += 1
        else:
            term_form["no terminator"] += 1
        # first chunk offset formula
        if ch:
            delta = ch[0].offset - (end + 12)
            firstoff_delta[delta] += 1
        # chunk types
        for c in ch:
            t = types.setdefault(c.type_marker, {"files": set(), "n": 0, "min": None, "max": None, "name": c.type_name})
            t["files"].add(path); t["n"] += 1
            t["min"] = c.size if t["min"] is None else min(t["min"], c.size)
            t["max"] = c.size if t["max"] is None else max(t["max"], c.size)
            seq[c.seq_skip] += 1
            seq_mod8[c.seq_skip % 8] += 1
            modal[c.type_marker][c.seq_skip] += 1
        # seqSkip tests
        n = len(ch)
        offs = [c.offset for c in ch]
        R["seq_total"] += n
        R["seq_eq_index"] += sum(1 for i, c in enumerate(ch) if c.seq_skip == i)
        R["seq_eq_zero"] += sum(1 for c in ch if c.seq_skip == 0)
        R["seq_eq_off"] += sum(1 for c in ch if c.seq_skip == c.offset)
        R["seq_eq_size"] += sum(1 for c in ch if c.seq_skip == c.size)
        for i, c in enumerate(ch):
            nxt = offs[i + 1] if i + 1 < n else len(d)
            if c.seq_skip == nxt - c.offset: R["seq_eq_next_gap"] += 1
            if i and c.seq_skip == c.offset - offs[i - 1]: R["seq_eq_prev_gap"] += 1
        s = [c.seq_skip for c in ch]
        if all(s[i] < s[i + 1] for i in range(n - 1)): R["seq_monotone_inc"] += 1
        elif all(s[i] <= s[i + 1] for i in range(n - 1)): R["seq_monotone_nondec"] += 1
        else: R["seq_not_monotone"] += 1
        R["seq_distinct_lt_count"] += 1 if len(set(s)) < n else 0
        # ids
        ids = [c.id for c in ch]
        if len(set(ids)) != len(ids): R["id_dup_files"] += 1
        if ids:
            id_min = min(id_min, min(ids)); id_max = max(id_max, max(ids))
        if sorted(ids) != list(range(len(ids))): R["id_not_dense"] += 1
        if len(set(ids)) == len(ids) and ids and max(ids) + 1 != len(ids):
            id_gap_files.append((os.path.basename(path), min(ids), max(ids), len(ids)))
        if ids == sorted(ids): order_sorted_by_id += 1
        if offs == sorted(offs): order_sorted_by_off += 1
        # pre-order: parent appears before child and children contiguous
        seen = set(); ok = True
        for c in ch:
            if c.parent in {r for r in ids} and c.parent not in seen: ok = False
            seen.add(c.id)
        preorder += 1 if ok else 0
        # forest
        idset = set(ids)
        byid = {c.id: c for c in ch}
        roots = [c for c in ch if c.parent not in idset]
        for r in roots:
            root_types[r.type_marker] += 1
            if r.parent != 254: parent_sentinel["parent=0x%04x" % r.parent] += 1
        if len(roots) != 1: R["multi_root_files"] += 1
        # depth + cycles
        for c in ch:
            dep = 0; cur = c; guard = 0; seen2 = set()
            while cur.parent in byid and guard < 512:
                if cur.id in seen2: R["cycles"] += 1; break
                seen2.add(cur.id)
                cur = byid[cur.parent]; dep += 1; guard += 1
            depth_hist[dep] += 1
            R["max_depth"] = max(R["max_depth"], dep)
        # last chunk extent
        if ch:
            trailing[len(d) - (offs[-1] + ch[-1].size)] += 1
    out = {
        "files": nfiles, "fails": fails[:10], "n_fail": len(fails),
        "counters": {k: v for k, v in R.items() if not k.startswith("max_depth")},
        "max_depth": R["max_depth"],
        "types": {hex(m): {"files": len(t["files"]), "n": t["n"], "min": t["min"], "max": t["max"], "name": t["name"]} for m, t in sorted(types.items())},
        "seq_top": seq.most_common(30),
        "seq_distinct": len(seq),
        "seq_mod8": dict(seq_mod8),
        "modal": {hex(t): c.most_common(3) for t, c in sorted(modal.items())},
        "root_types": {hex(k): v for k, v in root_types.items()},
        "parent_sentinel": dict(parent_sentinel),
        "depth_hist": dict(sorted(depth_hist.items())),
        "firstoff_delta": dict(firstoff_delta),
        "trailing": dict(trailing),
        "term_form": dict(term_form),
        "order_sorted_by_off": order_sorted_by_off, "order_sorted_by_id": order_sorted_by_id,
        "preorder": preorder, "id_min": id_min, "id_max": id_max,
        "id_gap_examples": id_gap_files[:5],
    }
    return out


if __name__ == "__main__":
    allres = {}
    for c in CORPORA:
        if os.path.isdir(c):
            allres[c] = analyze(c)
    json.dump(allres, open("tools/_inv2.json", "w"), indent=1, default=str)
    for c, r in allres.items():
        print("=" * 70); print(c)
        print("files", r["files"], "fails", r["n_fail"], r["fails"])
        print("counters", r["counters"])
        print("max_depth", r["max_depth"], "depth_hist", r["depth_hist"])
        print("roots", r["root_types"], "non254", r["parent_sentinel"])
        print("firstoff_delta", r["firstoff_delta"], "trailing", r["trailing"])
        print("term_form", r["term_form"])
        print("order by off", r["order_sorted_by_off"], "by id", r["order_sorted_by_id"], "preorder", r["preorder"])
        print("id range", r["id_min"], r["id_max"], "gap_examples", r["id_gap_examples"])
        print("seq distinct", r["seq_distinct"], "mod8", r["seq_mod8"])
        print("seq top", r["seq_top"])
