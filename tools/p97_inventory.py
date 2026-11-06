"""Throwaway analyzer: chunk-type inventory + directory semantics over corpora."""
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
    res = {
        "files": 0, "ok": 0, "fail": [],
        "versions": collections.Counter(),
        "types": {},          # marker -> dict(files=set, count, sizes)
        "seqskip_vals": collections.Counter(),
        "seqskip_eq_index": 0, "seqskip_eq_zero": 0, "seqskip_total": 0,
        "seqskip_eq_gap": 0, "seqskip_eq_prev_gap": 0,
        "seqskip_monotone_inc": 0, "seqskip_monotone_nondec": 0, "seqskip_other": 0,
        "seqskip_examples": collections.Counter(),
        "id_min": None, "id_max": None, "id_counts": collections.Counter(),
        "id_dup_files": [], "id_noncontig_files": 0, "id_sorted_eq_rank": 0,
        "parent_viol_files": [], "parent_missing_parent_files": [],
        "root_chunks": collections.Counter(),
        "max_depth": 0, "depth_hist": collections.Counter(),
        "multi_root_files": [], "no_doc_files": [],
        "dir_count_mismatch": [],
        "order_mismatch": 0,
        "overlaps": [],
        "first_chunk_not_at_0x22": [],
        "hdr_len_eq_stream": 0, "hdr_len_ne_stream": [],
        "chunk_sizes": collections.Counter(),
        "hdr_0x1a": collections.Counter(),
    }
    for path in files(root):
        try:
            doc = pubcore.parse_contents(path)
        except Exception as e:
            res["fail"].append((path, str(e)))
            continue
        res["files"] += 1
        res["ok"] += 1
        res["versions"][doc.version_magic] += 1
        res["hdr_0x1a"][int.from_bytes(doc.header[0x1A:0x1E], "little")] += 1
        hl = int.from_bytes(doc.header[8:0xC], "little")
        if hl == len(doc.contents):
            res["hdr_len_eq_stream"] += 1
        else:
            res["hdr_len_ne_stream"].append((path, hl, len(doc.contents)))
        if doc.directory_count != len(doc.chunks):
            res["dir_count_mismatch"].append((path, doc.directory_count, len(doc.chunks)))
        if doc.chunks and doc.chunks[0].offset != 0x22:
            res["first_chunk_not_at_0x22"].append((path, hex(doc.chunks[0].offset)))
        # types
        for c in doc.chunks:
            t = res["types"].setdefault(c.type_marker, {"files": set(), "count": 0, "min": None, "max": None, "name": c.type_name})
            t["files"].add(path)
            t["count"] += 1
            if t["min"] is None or c.size < t["min"]:
                t["min"] = c.size
            if t["max"] is None or c.size > t["max"]:
                t["max"] = c.size
            res["chunk_sizes"][c.type_marker] += c.size
        # seqSkip
        chunks = doc.chunks
        idx_of = {id(c): i for i, c in enumerate(chunks)}
        settled = [c for c in doc.chunks]
        seqs = [c.seq_skip for c in doc.chunks]
        res["seqskip_vals"].update(seqs)
        res["seqskip_total"] += len(seqs)
        n = len(chunks)
        offs = [c.offset for c in chunks]
        eq_idx = sum(1 for i, c in enumerate(chunks) if c.seq_skip == i)
        eq_zero = sum(1 for c in chunks if c.seq_skip == 0)
        eq_gap = 0
        eq_prev = 0
        for i, c in enumerate(chunks):
            nxt = offs[i + 1] if i + 1 < n else len(doc.contents)
            if c.seq_skip == nxt - c.offset:
                eq_gap += 1
            if i > 0 and c.seq_skip == c.offset - offs[i - 1]:
                eq_prev += 1
        res["seqskip_eq_index"] += eq_idx
        res["seqskip_eq_zero"] += eq_zero
        res["seqskip_eq_gap"] += eq_gap
        res["seqskip_eq_prev_gap"] += eq_prev
        if all(seqs[i] < seqs[i + 1] for i in range(n - 1)):
            res["seqskip_monotone_inc"] += 1
        elif all(seqs[i] <= seqs[i + 1] for i in range(n - 1)):
            res["seqskip_monotone_nondec"] += 1
        else:
            res["seqskip_other"] += 1
            res["seqskip_examples"][path] += 1
        # ids
        ids = [c.id for c in chunks]
        if len(set(ids)) != len(ids):
            res["id_dup_files"].append(path)
        if ids:
            res["id_min"] = min(ids) if res["id_min"] is None else min(res["id_min"], min(ids))
            res["id_max"] = max(ids) if res["id_max"] is None else max(res["id_max"], max(ids))
        res["id_counts"].update(ids)
        if sorted(ids) != list(range(len(ids))):
            res["id_noncontig_files"] += 1
        if ids == sorted(ids):
            res["id_sorted_eq_rank"] += 1
        # order: records sorted by offset?
        if offs != sorted(offs):
            res["order_mismatch"] += 1
        # overlaps / zero sizes
        for i in range(len(offs) - 1):
            if offs[i] >= offs[i + 1]:
                res["overlaps"].append(path)
                break
        # parents
        id_set = set(ids)
        bad = 0
        for c in chunks:
            if c.parent not in id_set:
                bad += 1
        if bad:
            res["parent_missing_parent_files"].append((path, bad))
        roots = [c for c in chunks if c.parent not in id_set]
        for r in roots:
            res["root_chunks"][r.type_marker] += 1
        if len(roots) > 1:
            res["multi_root_files"].append((path, len(roots)))
        if not any(c.type_marker == 0x15 for c in chunks):
            res["no_doc_files"].append(path)
        # depth via parent chain
        byid = {c.id: c for c in chunks}
        if len(byid) == len(chunks):
            depths = {}
            for c in chunks:
                d = 0
                cur = c
                seen = set()
                while cur.parent in byid and id(cur) not in seen:
                    if cur.id in seen:
                        bad = 1
                        break
                    seen.add(cur.id)
                    cur = byid[cur.parent]
                    d += 1
                    if d > 200:
                        bad = 1
                        break
                depths[c.id] = d
            md = max(depths.values()) if depths else 0
            res["max_depth"] = max(res["max_depth"], md)
            for v in depths.values():
                res["depth_hist"][v] += 1
    # serialize sets
    out = {}
    for k, v in res.items():
        if k == "types":
            out[k] = {hex(m): {"files": len(d["files"]), "count": d["count"], "min": d["min"], "max": d["max"], "name": d["name"]} for m, d in sorted(v.items())}
        elif isinstance(v, collections.Counter):
            out[k] = {str(a): b for a, b in v.items()}
        elif isinstance(v, list):
            out[k] = v[:20]
        else:
            out[k] = v
    return out


if __name__ == "__main__":
    allres = {}
    for c in CORPORA:
        if os.path.isdir(c):
            allres[c] = analyze(c)
    json.dump(allres, open("tools/_inventory.json", "w"), indent=1, default=str)
    for c, r in allres.items():
        print("==", c, "files", r["files"], "ok", r["ok"], "fail", len(r["fail"]))
        print("   versions", r["versions"])
        print("   types", len(r["types"]))
        print("   seqskip vals", r["seqskip_vals"])
