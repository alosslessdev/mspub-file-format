"""Structural validator for Publisher 95 documents.

Every rule here is a claim made in spec/01..spec/05. The tool reports, per file and in
aggregate:

  * structural violations (must be 0 for a valid corpus),
  * the percentage of chunk payload bytes covered by a documented field rule
    ("unexplained" = the rest).

Coverage is deliberately conservative: a chunk type whose byte layout is not documented in
the spec is reported as fully unexplained rather than assumed.

Usage:
    python p95_validate.py                 # validate p95/x with the default root
    python p95_validate.py --corpus p95/x
    python p95_validate.py --corpus p95/x --verbose
    python p95_validate.py --file p95/x/MSPUB.PUB --dump-unexplained
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

KNOWN_MARKERS = {
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007, 0x000F,
    0x0014, 0x0015, 0x0016, 0x001A, 0x001C, 0x001E, 0x001F, 0x0021, 0x0022,
    0x0023, 0x0026, 0x0027, 0x0028, 0x0029, 0x002A, 0x002B, 0x002C, 0x002D,
    0x002E, 0x0031, 0x0032, 0x0034, 0x0035, 0x0037, 0x0038, 0x0039,
}

# Per-type constant byte pair at chunk +2/+3 (chapter 04/05 and the record table).
# Only the values that are constant over the whole corpus are listed; the pair is
# checked as (low byte constant, high byte free) where the corpus shows variation.
DESCRIPTOR_LOW = {           # byte at +3, constant per type over the corpus
    0x0000: 0x5C, 0x0001: 0x60, 0x0002: 0x74, 0x0003: 0x74, 0x0004: 0x3B,
    0x0005: 0x3E, 0x0006: 0x35, 0x0007: 0x29, 0x000F: 0x18, 0x0014: 0x1A,
    0x0015: 0x6A, 0x0016: 0x10, 0x001A: 0x04, 0x001C: 0x04, 0x001E: 0x04,
    0x001F: 0x04, 0x0021: 0x08, 0x0022: 0x08, 0x0023: 0x04, 0x0026: 0x04,
    0x0027: 0x16, 0x0028: 0x10, 0x0029: 0x2C, 0x002A: 0x04, 0x002B: 0x04,
    0x002C: 0x18, 0x002D: 0x04, 0x002E: 0x04, 0x0031: 0x08, 0x0032: 0x04,
    0x0034: 0x24, 0x0035: 0xC8, 0x0037: 0x04, 0x0038: 0x04, 0x0039: 0x30,
}

# Types whose record has one size in the whole corpus and whose entire byte range is
# documented as a fixed record (offset tables in spec/04, spec/05 and the record table).
FIXED_RECORD = {
    0x0004, 0x0005, 0x0006, 0x0007, 0x0016, 0x0022, 0x0027,
    0x002E, 0x0035, 0x0038, 0x0039,
}

# base + count*element_size rules, proven over the whole corpus (zero exceptions):
#   size == base + element * u16@count_off
BASE_COUNT = {
    0x0000: (102, 0x5C, 2),
    0x0001: (106, 0x60, 14),
    0x0002: (126, 0x74, 8),
    0x0003: (126, 0x74, 8),
    0x000F: (0x22, 0x18, 2),
    0x0014: (0x24, 0x1A, 2),
    0x001C: (26, 0x04, 8),
    0x0028: (26, 0x10, 5),
    0x002C: (34, 0x18, 6),
    0x002D: (26, 0x04, 8),
    0x0031: (30, 0x08, 8),
    0x0034: (46, 0x24, 14),
    0x0037: (14, 0x04, 6),
}

# Types that declare their own payload length at +0x08 (= size - 14) after a 14-byte
# header. Proven with zero exceptions over the whole corpus.
PAYLOAD_LEN = {0x001E, 0x001F, 0x0023, 0x0026, 0x002A, 0x002B, 0x0032}

# Types whose record size encodes the element count with no count field:
#   size == base + element * k
IMPLIED_COUNT = {
    0x001A: (26, 14),
}

TRAILER_STAMPS = {0x1540, 0x1548, 0x1640, 0x1648}
DESCRIPTOR_SET = {0x1440, 0x1448, 0x14C0, 0x1540, 0x1548, 0x1640, 0x1648,
                  0x1660, 0x16C0, 0x16C8, 0x16E0, 0x1740, 0x1748}


class Violations:
    def __init__(self):
        self.items = []

    def add(self, f, check, detail):
        self.items.append((os.path.basename(f), check, detail))

    def __len__(self):
        return len(self.items)


def _covered_ranges(c: "pubcore.Chunk") -> list:
    """Return the byte ranges of the chunk payload that a documented rule covers.

    Ranges are chunk-relative. Anything not covered counts as unexplained.
    """
    d = c.data
    n = len(d)
    tm = c.type_marker
    rng = [(0, min(4, n))]          # type marker + descriptor pair: chapters 02..05

    if tm == 0x0014:                                  # PAGE, chapter 05
        if n >= 0x24:
            rng.append((0x04, 0x24))
            cnt = struct.unpack_from("<H", d, 0x1A)[0]
            rng.append((0x24, min(n, 0x24 + 2 * cnt)))
    elif tm == 0x0015:                                # DOCUMENT, chapter 04
        rng.append((0x04, min(n, 0x74)))
        if n >= 0x74:
            rng.append((0x74, n))                     # page id array, all of the tail
    elif tm == 0x0021:                                # IMAGE_DATA: u32 length + opaque blob
        rng.append((0, n))
    elif tm == 0x0022:                                # 18-byte fixed record
        rng.append((0, n))
    elif tm in FIXED_RECORD:
        rng.append((0, n))
    elif tm in PAYLOAD_LEN:
        if n >= 14 and struct.unpack_from("<H", d, 8)[0] == n - 14:
            rng.append((4, n))
    elif tm == 0x0029:
        if n >= 54 and struct.unpack_from("<H", d, 0x30)[0] == n - 54:
            rng.append((4, n))
    elif tm in IMPLIED_COUNT:
        base, elem = IMPLIED_COUNT[tm]
        if n >= base and (n - base) % elem == 0:
            rng.append((4, n))
    elif tm in BASE_COUNT:
        base, cnt_off, elem = BASE_COUNT[tm]
        if n >= cnt_off + 2:
            cnt = struct.unpack_from("<H", d, cnt_off)[0]
            if n == base + elem * cnt:
                rng.append((4, n))
    return rng


# Byte ranges whose semantics are named in the spec (stronger than framing coverage).
NAMED = {
    0x0015: lambda n, d: [(0, n)],
    0x0014: lambda n, d: [(0, min(n, 0x24 + 2 * struct.unpack_from("<H", d, 0x1A)[0]))],
    0x0016: lambda n, d: [(0, n)],
    0x0021: lambda n, d: [(0, n)],
    0x0022: lambda n, d: [(0, n)],
    0x0000: lambda n, d: [(0, 0x16)],          # marker/descriptor/rotation/bbox
    0x0002: lambda n, d: [(0, 0x16)],
    0x0003: lambda n, d: [(0, 0x16)],
    0x0004: lambda n, d: [(0, 0x16)],
    0x0005: lambda n, d: [(0, 0x16)],
    0x0006: lambda n, d: [(0, 0x16)],
    0x0007: lambda n, d: [(0, 0x16)],
    0x0001: lambda n, d: [(0, 0x16)],
    0x000F: lambda n, d: [(0, min(n, 0x22 + 2 * struct.unpack_from("<H", d, 0x18)[0]))],
}


def named_coverage(c: "pubcore.Chunk"):
    n = len(c.data)
    fn = NAMED.get(c.type_marker)
    if fn is None:
        return 0, n
    mask = bytearray(n)
    for a, b in fn(n, c.data):
        for i in range(max(0, a), min(n, b)):
            mask[i] = 1
    return sum(mask), n


def coverage(c: "pubcore.Chunk"):
    n = len(c.data)
    mask = bytearray(n)
    for a, b in _covered_ranges(c):
        for i in range(max(0, a), min(n, b)):
            mask[i] = 1
    return sum(mask), n


def validate_file(path: str, v: Violations):
    stats = {"files": 0, "explained": 0, "payload": 0, "named": 0}
    doc = pubcore.parse_contents(path)
    d = doc.contents
    stats["files"] = 1

    # ---- container / header (chapter 02) --------------------------------
    if struct.unpack_from("<H", d, 0)[0] != 0xACE8:
        v.add(path, "header.magic", "not 0xACE8")
    if struct.unpack_from("<H", d, 4)[0] != 300:
        v.add(path, "header.format_version", struct.unpack_from("<H", d, 4)[0])
    if struct.unpack_from("<H", d, 0x0C)[0] != 125:
        v.add(path, "header.header_tag", struct.unpack_from("<H", d, 0x0C)[0])
    if struct.unpack_from("<I", d, 8)[0] != len(d):
        v.add(path, "header.declared_length",
              "%d != %d" % (struct.unpack_from("<I", d, 8)[0], len(d)))
    if struct.unpack_from("<I", d, 0x1A)[0] != 34:
        v.add(path, "header.const_34", struct.unpack_from("<I", d, 0x1A)[0])
    if struct.unpack_from("<I", d, 0x12)[0] != 574:
        v.add(path, "header.const_574", struct.unpack_from("<I", d, 0x12)[0])

    by_id = {c.id: c for c in doc.chunks}
    docc = by_id.get(struct.unpack_from("<H", d, 0x0E)[0])
    if docc is None or docc.type_marker != 0x15:
        v.add(path, "header.document_chunk_id", "does not resolve to a 0x15 chunk")
        return stats
    page4 = by_id.get(struct.unpack_from("<H", d, 0x10)[0])
    if page4 is None or page4.type_marker != 0x14:
        v.add(path, "header.page_4_id", "does not resolve to a 0x14 chunk")

    # ---- directory (chapter 03) ----------------------------------------
    tr = struct.unpack_from("<I", d, 0x16)[0]
    if not (0x22 <= tr < len(d) - 4):
        v.add(path, "dir.offset", tr)
        return stats
    count = struct.unpack_from("<H", d, tr)[0]
    if tr + 2 + 10 * count + 12 > len(d):
        v.add(path, "dir.extent", "count %d overruns stream" % count)
        return stats
    recs = []
    for i in range(count):
        X, cid, par, off = struct.unpack_from("<HHHI", d, tr + 2 + 10 * i)
        recs.append((X, cid, par, off))
    ids = [r[1] for r in recs]
    if len(set(ids)) != len(ids):
        v.add(path, "dir.duplicate_id", "count %d" % count)
    idset = set(ids)
    for i, (X, cid, par, off) in enumerate(recs):
        if par != 0x00FE and par not in idset:
            v.add(path, "dir.parent_resolves", "record %d parent %d" % (i, par))
        if not (tr + 2 + 10 * count + 12 <= off < len(d)):
            v.add(path, "dir.chunk_offset_range", "record %d offset %d" % (i, off))
    if recs[0][2] != 0x00FE:
        v.add(path, "dir.root_is_record0", recs[0][2])
    for i in range(len(recs) - 1):
        if not (recs[i][3] < recs[i + 1][3]):
            v.add(path, "dir.offset_order", "records %d/%d" % (i, i + 1))
    if recs[0][0] != max(ids):
        v.add(path, "dir.record0_descriptor", "%d != max %d" % (recs[0][0], max(ids)))
    for i, (X, _cid, _par, _off) in enumerate(recs[1:], start=1):
        if X not in DESCRIPTOR_SET:
            v.add(path, "dir.descriptor_set", "record %d value %#06x" % (i, X))
    gap = tr + 2 + 10 * count
    first_chunk = recs[0][3] if False else min(ids and [r[3] for r in recs])
    if first_chunk != gap + 12:
        v.add(path, "dir.trailer", "gap %d bytes, expected 12" % (first_chunk - gap))
    else:
        stamp = struct.unpack_from("<H", d, gap)[0]
        if stamp not in TRAILER_STAMPS:
            v.add(path, "dir.trailer_stamp", "%#06x" % stamp)
        if any(d[gap + 2:gap + 12]):
            v.add(path, "dir.trailer_zero", d[gap + 2:gap + 12].hex())

    # ---- chunk adjacency and framing -----------------------------------
    offs = sorted(r[3] for r in recs)
    extents = {o: (offs[i + 1] if i + 1 < len(offs) else len(d)) for i, o in enumerate(offs)}
    type_of = {}
    for c in doc.chunks:
        type_of[c.id] = c.type_marker
        if c.type_marker not in KNOWN_MARKERS:
            v.add(path, "chunk.marker_known", "id %d marker %#06x" % (c.id, c.type_marker))
            continue
        if c.size < 4:
            v.add(path, "chunk.min_size", "id %d size %d" % (c.id, c.size))
            continue
        want = DESCRIPTOR_LOW.get(c.type_marker)
        if want is not None and c.data[3] != want:
            v.add(path, "chunk.descriptor_low",
                  "id %d marker %#06x byte3 %#04x != %#04x" % (c.id, c.type_marker, c.data[3], want))
        if (extents.get(c.offset, 0) - c.offset) != c.size:
            v.add(path, "chunk.extent", "id %d" % c.id)

    # ---- DOCUMENT (chapter 04) -----------------------------------------
    ddata = docc.data
    if ddata[0:2] != b"\x15\x00":
        v.add(path, "document.marker", ddata[0:2].hex())
    if struct.unpack_from("<H", ddata, 0x02)[0] != 0x6A78:
        v.add(path, "document.descriptor", struct.unpack_from("<H", ddata, 0x02)[0])
    n_pages = sum(1 for c in doc.chunks if c.type_marker == 0x14)
    if docc.size != 0x74 + 2 * (n_pages - 1):
        v.add(path, "document.size", "%d != 0x74+2*(%d-1)" % (docc.size, n_pages))
    expect = {0x04: 0x29, 0x06: 0x28, 0x08: 0x14, 0x68: 0x39}
    for off, tm in expect.items():
        ref = by_id.get(struct.unpack_from("<H", ddata, off)[0])
        if ref is None or ref.type_marker != tm:
            v.add(path, "document.pointer", "+%#04x should be a %#06x chunk" % (off, tm))
    slots = {0x46: 0x23, 0x48: 0x31, 0x4A: 0x1E, 0x4C: 0x1F, 0x4E: 0x16,
             0x50: 0x2A, 0x52: 0x2B, 0x54: 0x26, 0x56: 0x31, 0x58: 0x31,
             0x5A: 0x34, 0x5C: 0x35, 0x5E: 0x37, 0x60: 0x38}
    for off, tm in slots.items():
        val = struct.unpack_from("<H", ddata, off)[0]
        if val == 0:
            continue
        ref = by_id.get(val)
        if ref is None or ref.type_marker != tm:
            v.add(path, "document.global_slot", "+%#04x -> %d, want type %#06x" % (off, val, tm))
    if struct.unpack_from("<H", ddata, 0x6A)[0] != n_pages - 1:
        v.add(path, "document.last_page_index", struct.unpack_from("<H", ddata, 0x6A)[0])
    if struct.unpack_from("<H", ddata, 0x6C)[0] != n_pages - 1:
        v.add(path, "document.last_page_index2", struct.unpack_from("<H", ddata, 0x6C)[0])
    if struct.unpack_from("<H", ddata, 0x6E)[0] != 2:
        v.add(path, "document.const_6e", struct.unpack_from("<H", ddata, 0x6E)[0])
    for off in (0x62, 0x66, 0x70, 0x72):
        if struct.unpack_from("<H", ddata, off)[0] != 0:
            v.add(path, "document.reserved_zero", "+%#04x" % off)
    w = struct.unpack_from("<I", ddata, 0x14)[0]
    h = struct.unpack_from("<I", ddata, 0x18)[0]
    if w == 0 or h == 0:
        v.add(path, "document.page_size", "%dx%d" % (w, h))
    page_ids = [struct.unpack_from("<H", ddata, 0x08)[0]]
    for i in range((docc.size - 0x74) // 2):
        page_ids.append(struct.unpack_from("<H", ddata, 0x74 + 2 * i)[0])
    if len(set(page_ids)) != len(page_ids):
        v.add(path, "document.page_ids_unique", str(page_ids))
    for pid in page_ids:
        ref = by_id.get(pid)
        if ref is None or ref.type_marker != 0x14:
            v.add(path, "document.page_id", str(pid))
    if page_ids != [c.id for c in doc.of_type(0x14)]:
        v.add(path, "document.page_order", "differs from directory order")
    # +0x10 is the 4th page of that order
    if len(page_ids) >= 4 and struct.unpack_from("<H", d, 0x10)[0] != page_ids[3]:
        v.add(path, "header.page_4_id_order", str(struct.unpack_from("<H", d, 0x10)[0]))

    # ---- PAGE (chapter 05) ---------------------------------------------
    for p in doc.of_type(0x14):
        pd = p.data
        if pd[0:4] != b"\x14\x00\x1a\x1a":
            v.add(path, "page.descriptor", pd[0:4].hex())
            continue
        n = struct.unpack_from("<H", pd, 0x1A)[0]
        if p.size != 0x24 + 2 * n:
            v.add(path, "page.size", "id %d size %d n %d" % (p.id, p.size, n))
        if struct.unpack_from("<H", pd, 0x1C)[0] != n:
            v.add(path, "page.count_dup", "id %d" % p.id)
        if struct.unpack_from("<H", pd, 0x1E)[0] != 2:
            v.add(path, "page.element_size", "id %d" % p.id)
        if struct.unpack_from("<H", pd, 0x20)[0] or struct.unpack_from("<H", pd, 0x22)[0]:
            v.add(path, "page.reserved_zero", "id %d" % p.id)
        if struct.unpack_from("<H", pd, 0x18)[0] not in (0, 1, 2, 4):
            v.add(path, "page.kind", "id %d" % p.id)
        s = struct.unpack_from("<H", pd, 0x04)[0]
        if s:
            ref = by_id.get(s)
            if ref is None or ref.type_marker != 0x2C:
                v.add(path, "page.settings_id", "id %d -> %d" % (p.id, s))
        kids = [struct.unpack_from("<H", pd, 0x24 + 2 * i)[0] for i in range(n)]
        if len(set(kids)) != len(kids):
            v.add(path, "page.child_duplicate", "id %d" % p.id)
        for k in kids:
            ref = by_id.get(k)
            if ref is None:
                v.add(path, "page.child_resolves", "id %d -> %d" % (p.id, k))
            elif ref.type_marker in (0x14, 0x15, 0x2C):
                v.add(path, "page.child_type", "id %d -> %#06x" % (p.id, ref.type_marker))

    # ---- IMAGE_DATA -----------------------------------------------------
    for im in doc.of_type(0x21):
        if im.size < 8:
            v.add(path, "image.min_size", str(im.id))
            continue
        declared = struct.unpack_from("<I", im.data, 4)[0]
        if declared != im.size - 8:
            v.add(path, "image.declared_length", "id %d %d != %d" % (im.id, declared, im.size - 8))

    # ---- coverage --------------------------------------------------------
    for c in doc.chunks:
        got, total = coverage(c)
        stats["explained"] += got
        stats["payload"] += total
        ngot, ntot = named_coverage(c)
        stats["named"] += ngot

    # ---- extra record checks -------------------------------------------
    for c in doc.of_type(0x22):
        if c.size != 18 or c.data[8:10] != b"MO":
            v.add(path, "record_0x22", "id %d size %d sig %s" % (c.id, c.size, c.data[8:10].hex()))
    for c in doc.of_type(0x21):
        if len(c.data) >= 12 and c.data[8:12] != b"\x01\x00\x09\x00":
            v.add(path, "image_data.signature", "id %d %s" % (c.id, c.data[8:12].hex()))
    for c in doc.of_type(0x16):
        refs = [struct.unpack_from("<H", c.data, o)[0] for o in (0x08, 0x0A, 0x0C, 0x0E)]
        want = [0x1A, 0x1C, 0x2E, 0x2D]
        for r, w in zip(refs, want):
            ref = by_id.get(r)
            if ref is None or ref.type_marker != w:
                v.add(path, "chunk16.slot_order", "id %d -> %d want %#06x" % (c.id, r, w))

    # ---- nested documents (Objects/Object N/Contents) -------------------
    try:
        import olefile
        ole = olefile.OleFileIO(path)
        for entry in ole.listdir():
            name = "/".join(entry)
            if name.endswith("/Contents") or name == "Contents":
                if not name.startswith("Objects/"):
                    continue
                blob = ole.openstream(entry).read()
                if len(blob) >= 0x20:
                    if struct.unpack_from("<H", blob, 0)[0] != 0xACE8:
                        v.add(path, "nested.magic", name)
                    ntr = struct.unpack_from("<I", blob, 0x16)[0]
                    if not (0x22 <= ntr < len(blob) - 4):
                        v.add(path, "nested.directory", "%s offset %d" % (name, ntr))
                    else:
                        n = struct.unpack_from("<H", blob, ntr)[0]
                        if ntr + 2 + 10 * n + 12 > len(blob):
                            v.add(path, "nested.directory_extent", name)
        ole.close()
    except Exception as e:
        v.add(path, "nested.inspect", "%s: %s" % (type(e).__name__, e))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=None)
    ap.add_argument("--file", default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--dump-unexplained", action="store_true")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    if a.file:
        files = [a.file]
    else:
        corpus = a.corpus or os.path.join(root, "p95", "x")
        files = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
    if not files:
        print("no .PUB files found")
        return 2

    v = Violations()
    agg = collections.Counter()
    per_type = collections.Counter()
    for f in files:
        try:
            st = validate_file(f, v)
        except Exception as e:
            v.add(f, "parse.crash", "%s: %s" % (type(e).__name__, e))
            continue
        agg["files"] += 1
        agg["explained"] += st["explained"]
        agg["payload"] += st["payload"]
        agg["named"] += st["named"]

    by_check = collections.Counter((c for _, c, _ in v.items))
    print("files                : %d" % agg["files"])
    print("structural violations: %d" % len(v))
    if v:
        for check, n in by_check.most_common():
            print("   %-32s %d" % (check, n))
        if a.verbose or a.file:
            for f, check, detail in v.items[:40]:
                print("   %-24s %-30s %s" % (f, check, detail))
    if agg["payload"]:
        pct = 100.0 * (1 - agg["explained"] / agg["payload"])
        print("chunk payload bytes  : %d" % agg["payload"])
        print("documented coverage  : %.1f%%" % (100.0 * agg["explained"] / agg["payload"]))
        print("unexplained          : %.1f%%  (%d bytes)"
              % (pct, agg["payload"] - agg["explained"]))
        print("named-field coverage : %.1f%%  (bytes inside a field whose meaning the spec states)"
              % (100.0 * agg["named"] / agg["payload"]))
    return 0 if len(v) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
