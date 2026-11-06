"""Structural validator: checks every documented invariant against a corpus.

Each check corresponds to a rule stated in spec/. A non-zero violation count means
either the spec is wrong or the corpus contains a variant the spec does not cover —
both are release blockers.

Usage: python validate.py p95/x p97/x p97deluxe/x p98/x
"""
from __future__ import annotations

import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import pubread

CHECKS = [
    "cfb_parse", "contents_magic", "declared_length", "format_version_300",
    "directory_offsets_ascending", "directory_ids_unique", "directory_parents_resolve",
    "chunk_extents_cover_stream", "single_document_chunk", "document_size_rule",
    "page_size_equation", "page_children_exist", "page_child_count_pair",
    "shape_bbox_ordered", "shape_bbox_magnitude", "image_data_length_prefix", "image_data_wmf",
    "record_0x22_is_18", "quill_list_terminates",
]


def check_file(path: str, stats: collections.Counter, failures: list):
    def fail(check, detail):
        stats[check] += 1
        if len(failures) < 40:
            failures.append((check, path, detail))

    try:
        doc = pubcore.parse_contents(path)
    except Exception as e:
        fail("cfb_parse", str(e))
        return
    d = doc.contents
    if len(d) < 0x22:
        fail("contents_magic", "short stream")
        return
    magic = struct.unpack_from("<H", d, 0)[0]
    if magic not in (0xACE8, 0xACE7):
        fail("contents_magic", "magic=%#06x" % magic)
    declared = struct.unpack_from("<I", d, 8)[0]
    if declared != len(d):
        fail("declared_length", "%d != %d" % (declared, len(d)))
    fmt = struct.unpack_from("<H", d, 4)[0]
    if fmt != 300:
        fail("format_version_300", "format=%d" % fmt)

    offsets = [c.offset for c in doc.chunks]
    if offsets != sorted(offsets):
        fail("directory_offsets_ascending", "not sorted")
    ids = [c.id for c in doc.chunks]
    if len(set(ids)) != len(ids):
        fail("directory_ids_unique", "duplicate ids")
    idset = set(ids)
    for c in doc.chunks:
        if c.parent not in idset and c.parent not in (0x00FE, 0x00FF):
            fail("directory_parents_resolve", "id=%#06x parent=%#06x" % (c.id, c.parent))
            break
    last = doc.chunks[-1]
    if last.offset + last.size != len(d):
        fail("chunk_extents_cover_stream", "last ends at %d of %d" % (last.offset + last.size, len(d)))

    docs = doc.of_type(0x15)
    if len(docs) != 1:
        fail("single_document_chunk", "%d document chunks" % len(docs))
        return
    dc = docs[0]
    # Page slots are type 0x14 and (Publisher 98) 0x41.
    npages = len(doc.of_type(0x14)) + len(doc.of_type(0x41))
    # Publisher 95 base; Publisher 97 appends 30 bytes, Publisher 98 appends 72.
    delta = dc.size - (0x74 + 2 * (npages - 1))
    if delta not in (0, 30, 72):
        fail("document_size_rule", "pages=%d size=%d delta=%d" % (npages, dc.size, delta))
    stats["doc_delta_%d" % delta] += 1
    width = struct.unpack_from("<I", dc.data, 0x14)[0]
    height = struct.unpack_from("<I", dc.data, 0x18)[0]

    for c in doc.of_type(0x14):
        if len(c.data) < 0x24:
            fail("page_size_equation", "id=%#06x size=%d" % (c.id, c.size))
            continue
        # Publisher 98 shifted the record by +4: descriptor 0x1E, counts at +0x1E/+0x20,
        # ids at +0x28. Publisher 95/97: descriptor 0x1A, counts at +0x1A/+0x1C, ids at +0x24.
        p98 = c.data[2] == 0x1E
        cnt_off, arr_off = (0x1E, 0x28) if p98 else (0x1A, 0x24)
        n = struct.unpack_from("<H", c.data, cnt_off)[0]
        n2 = struct.unpack_from("<H", c.data, cnt_off + 2)[0]
        base = arr_off
        if c.size != base + 2 * n:
            fail("page_size_equation", "id=%#06x size=%d n=%d base=%#x" % (c.id, c.size, n, base))
        if n != n2:
            fail("page_child_count_pair", "id=%#06x %d != %d" % (c.id, n, n2))
        for cid in struct.unpack_from("<%dH" % n, c.data, arr_off):
            if cid not in idset:
                fail("page_children_exist", "page=%#06x child=%#06x" % (c.id, cid))
                break

    for c in doc.chunks:
        if c.type_marker in (0x00, 0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x16):
            if len(c.data) < 0x16:
                continue
            x0, y0, x1, y1 = struct.unpack_from("<iiii", c.data, 6)
            # Objects may legitimately lie outside the page (pasteboard).
            if x0 > x1 or y0 > y1:
                fail("shape_bbox_ordered", "id=%#06x box=(%d,%d,%d,%d)" % (c.id, x0, y0, x1, y1))
                break
            if max(abs(x0), abs(y0), abs(x1), abs(y1)) > 400 * pubread.EMU_PER_INCH:
                fail("shape_bbox_magnitude", "id=%#06x box=(%d,%d,%d,%d)" % (c.id, x0, y0, x1, y1))
                break
        elif c.type_marker == 0x21:
            if len(c.data) < 8:
                fail("image_data_length_prefix", "id=%#06x short" % c.id)
                continue
            n = struct.unpack_from("<I", c.data, 4)[0]
            if n != c.size - 8:
                fail("image_data_length_prefix", "id=%#06x %d != %d" % (c.id, n, c.size - 8))
            if c.data[8:12] != b"\x01\x00\x09\x00":
                fail("image_data_wmf", "id=%#06x sig=%s" % (c.id, c.data[8:12].hex()))
        elif c.type_marker == 0x22:
            if c.size != 18:
                fail("record_0x22_is_18", "id=%#06x size=%d" % (c.id, c.size))
    try:
        blob = pubcore.read_stream(path, "Quill/QuillSub/CONTENTS")
    except Exception:
        blob = None
    if blob:
        off = 0x18
        seen = set()
        ok = True
        while off != 0xFFFFFFFF:
            if off + 8 > len(blob) or off in seen:
                ok = False
                break
            seen.add(off)
            off = struct.unpack_from("<I", blob, off + 4)[0]
        if not ok:
            fail("quill_list_terminates", "walk failed at %#x" % off)
    stats["files"] += 1


def main():
    corpora = sys.argv[1:] or ["p95/x"]
    total = collections.Counter()
    failures = []
    for corpus in corpora:
        files = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
        stats = collections.Counter()
        for f in files:
            check_file(f, stats, failures)
        print("\n%s: %d files" % (corpus, len(files)))
        for check in CHECKS:
            if stats.get(check):
                print("   FAIL %-32s %d" % (check, stats[check]))
        else:
            print("   (all checks with violations listed above)")
        total.update(stats)
    print("\n=== violations ===")
    any_fail = False
    for check in CHECKS:
        if total.get(check):
            any_fail = True
            print("   %-32s %d" % (check, total[check]))
    if not any_fail:
        print("   none")
    else:
        print("\nfirst failures:")
        for check, path, detail in failures[:20]:
            print("   %-30s %s  %s" % (check, path, detail))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
