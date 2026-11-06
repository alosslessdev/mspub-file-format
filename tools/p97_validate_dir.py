"""Validate the Publisher 95/97/98 chunk-directory model over a corpus.

Usage:
    python tools/p97_validate_dir.py <corpus-dir> [<corpus-dir> ...]

Each file's `Contents` stream is re-parsed from raw bytes (not trusting
pubcore's derived fields) and the following invariants are checked:

  D1  magic 0xACE8, version magic 0x22
  D2  directory count fits: trailer + 2 + 10*count + 10 <= len(Contents)
  D3  a 10-byte sentinel record follows the count records:
      id == 0, parentId == 0, chunkOffset == 0
  D4  first chunk offset == trailer + 2 + 10*count + 12
  D5  record chunkOffset values are strictly increasing and in range
  D6  every chunk starts with a u16 type marker readable at its offset
  D7  chunk sizes (next offset - own offset) are > 0 and the last chunk
      ends exactly at len(Contents)
  D8  chunk ids are unique within the file
  D9  exactly one root record (parentId not present in the id set) and it
      is the DOCUMENT chunk (type 0x15)
  D10 every non-root parentId resolves to a chunk id in the same file
  D11 parent links form a forest: no cycles, max depth <= 8
  D12 the DOCUMENT record's tag word == max(chunk ids); every other
      chunk's tag word >= 0x1000 and is a multiple of 8

Exit code 0 if every file in every corpus passes, 1 otherwise.
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore  # noqa: E402

ROOT_SENTINELS = (254, 255)
MAX_DEPTH = 8


def pub_files(root):
    out = []
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            if n.lower().endswith(".pub"):
                out.append(os.path.join(dirpath, n))
    return sorted(out)


def check_file(path):
    """Return (list of (check_id, detail), stats)."""
    errs = []
    raw = pubcore.read_stream(path, "Contents")
    if raw is None:
        return [("D0", "no Contents stream")], {}

    def fail(cid, msg):
        errs.append((cid, msg))

    if len(raw) < 0x22 or struct.unpack_from("<H", raw, 0)[0] != 0xACE8:
        return [("D1", "bad magic")], {}
    if raw[2] != 0x22:
        fail("D1", "version magic %#04x != 0x22" % raw[2])

    trailer = struct.unpack_from("<I", raw, 0x16)[0]
    count = struct.unpack_from("<H", raw, trailer)[0]
    end = trailer + 2 + 10 * count
    if end + 10 > len(raw):
        return [("D2", "directory overruns stream")], {"count": count}

    recs = [struct.unpack_from("<HHHI", raw, trailer + 2 + 10 * i) for i in range(count)]

    # D3 sentinel
    s_tag, s_id, s_par, s_off = struct.unpack_from("<HHHI", raw, end)
    if (s_id, s_par, s_off) != (0, 0, 0):
        fail("D3", "sentinel = id %d parent %d off %#x" % (s_id, s_par, s_off))

    offs = [r[3] for r in recs]
    # D4 first offset
    if offs and offs[0] != end + 12:
        fail("D4", "first chunk at %#x, expected %#x" % (offs[0], end + 12))
    # D5 increasing
    for i in range(len(offs) - 1):
        if offs[i] >= offs[i + 1]:
            fail("D5", "offset %#x not before %#x at record %d" % (offs[i], offs[i + 1], i))
            break
    if offs and not (0x22 <= offs[0] and offs[-1] < len(raw)):
        fail("D5", "offset out of stream range")

    # D6/D7 chunks
    order = sorted(range(len(recs)), key=lambda i: offs[i])
    sizes = {}
    for k, i in enumerate(order):
        start = offs[i]
        stop = offs[order[k + 1]] if k + 1 < len(order) else len(raw)
        sizes[i] = stop - start
        if sizes[i] <= 0:
            fail("D7", "chunk %d has size %d" % (i, sizes[i]))
        if start + 2 > len(raw):
            fail("D6", "chunk %d offset past EOF" % i)
    if order and offs[order[-1]] + sizes[order[-1]] != len(raw):
        fail("D7", "last chunk ends at %#x, stream is %#x"
             % (offs[order[-1]] + sizes[order[-1]], len(raw)))

    # D8 ids unique
    ids = [r[1] for r in recs]
    if len(set(ids)) != len(ids):
        fail("D8", "duplicate chunk ids")

    # D9/D10/D11 forest
    idset = set(ids)
    byid = {}
    for i, r in enumerate(recs):
        byid.setdefault(r[1], i)
    roots = [i for i, r in enumerate(recs) if r[2] not in idset]
    if len(roots) != 1:
        fail("D9", "%d root records" % len(roots))
    else:
        ri = roots[0]
        marker = struct.unpack_from("<H", raw, offs[ri])[0]
        if marker != 0x15:
            fail("D9", "root record has type %#06x, expected 0x0015" % marker)
        if recs[ri][2] not in ROOT_SENTINELS:
            fail("D9", "root parentId %d not a sentinel" % recs[ri][2])
    for i, r in enumerate(recs):
        if r[2] not in idset and i not in roots:
            fail("D10", "record %d parent %d unresolved" % (i, r[2]))
            break
    depth_max = 0
    for i, r in enumerate(recs):
        depth = 0
        cur = i
        seen = set()
        while recs[cur][2] in idset:
            if cur in seen:
                fail("D11", "cycle through id %d" % recs[cur][1])
                depth = -1
                break
            seen.add(cur)
            cur = byid[recs[cur][2]]
            depth += 1
            if depth > 64:
                fail("D11", "chain too long at id %d" % recs[i][1])
                depth = -1
                break
        depth_max = max(depth_max, depth)
    if depth_max > MAX_DEPTH:
        fail("D11", "max depth %d > %d" % (depth_max, MAX_DEPTH))

    # D12 tag words
    doc_idx = roots[0] if len(roots) == 1 else None
    mx = max(ids) if ids else 0
    for i, r in enumerate(recs):
        tag = r[0]
        if i == doc_idx:
            if tag != mx:
                fail("D12", "DOCUMENT tag %d != max id %d" % (tag, mx))
        elif tag < 0x1000 or tag % 8:
            fail("D12", "chunk id %d tag %#06x violates tag shape" % (r[1], tag))

    return errs, {"count": count, "depth": depth_max,
                  "tags": len({r[0] for r in recs})}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rc = 0
    for root in argv[1:]:
        paths = pub_files(root)
        print("== %s: %d files" % (root, len(paths)))
        if not paths:
            print("   FAIL: no .PUB files found")
            rc = 1
            continue
        pfail = 0
        per_check = {}
        depths = []
        for p in paths:
            try:
                errs, stats = check_file(p)
            except Exception as e:  # noqa: BLE001
                errs, stats = [("D0", "exception: %s" % e)], {}
            if errs:
                pfail += 1
                if pfail <= 3:
                    for cid, msg in errs[:4]:
                        print("   FAIL %s: %s %s" % (os.path.basename(p), cid, msg))
            for cid, _msg in errs:
                per_check[cid] = per_check.get(cid, 0) + 1
            if "depth" in stats:
                depths.append(stats["depth"])
        print("   pass %d / fail %d" % (len(paths) - pfail, pfail))
        print("   failing checks: %s" % (per_check or "none"))
        if depths:
            print("   max depth seen %d, mean %.2f"
                  % (max(depths), sum(depths) / len(depths)))
        if pfail:
            rc = 1
    print("RESULT: %s" % ("PASS" if rc == 0 else "FAIL"))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
