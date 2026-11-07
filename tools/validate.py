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
import olefile

import pubcore
import pubread

# Writer-side fixed record length byte at +0x03. Publisher 98 grew the IMAGE record
# by 24 bytes (116 -> 140), so the marker has a version-dependent value set.
RECORD_LEN_B = {0x00: {92}, 0x01: {96}, 0x02: {116, 140}, 0x03: {116}, 0x04: {59},
                0x05: {62}, 0x06: {53}, 0x07: {41}, 0x16: {16, 18}}
RECORD_BASE = {0x00: 102, 0x01: 106, 0x02: 126, 0x03: 126, 0x04: 59, 0x05: 62,
               0x06: 53, 0x07: 41, 0x16: 16}

# Publisher 95/97 writer length byte. A shape record still carrying one of these B
# values predates the Publisher 98 +8 shift and therefore has the 95/97 field at
# +0x23 (spec 06 §6.7.1). Publisher 98 always writes +8 (0x5C->0x64 ... 0x29->0x31).
RECORD_LEN_B_9597 = {0x00: 92, 0x01: 96, 0x02: 116, 0x03: 116, 0x04: 59,
                     0x05: 62, 0x06: 53, 0x07: 41}

# Descriptor of the Publisher 98 shape-list record 0x0008 (spec 06 §6.4.2).
SHAPE8_B = 0x76
SHAPE8_BASE = 0x80


def colour_ref_ok(ref: int) -> bool:
    """True when `ref` decodes under MSPUB.EXE's colour-reference switch.

    MSPUB.EXE 95 FUN_00418364 @ 0x00418364 switches on `ref >> 29`:
    0 -> palette[ref & 0xFFFF], 1 -> literal RGB, 2/4 -> derived colours,
    anything else -> -1 (no colour). The palette has 0x38 entries (spec 09 §9.2),
    so a palette-class reference must carry an index below 0x38.
    """
    top = (ref >> 29) & 0x7
    if top == 0:
        return (ref & 0xFFFF) < 0x38
    if top == 1:
        return True
    if top in (2, 4):
        return True
    return False


CHECKS = [
    "cfb_parse", "contents_magic", "declared_length", "format_version_300",
    "directory_offsets_ascending", "directory_ids_unique", "directory_parents_resolve",
    "chunk_extents_cover_stream", "single_document_chunk", "document_size_rule",
    "document_id_base", "document_flags_domain", "document_coord_system",
    "document_tab_interval",
    "page_size_equation", "page_children_exist", "page_child_count_pair",
    "shape_bbox_ordered", "shape_bbox_magnitude", "image_data_length_prefix", "image_data_wmf",
    "record_length_byte", "record_min_size", "record_0x22_is_18", "quill_list_terminates", "object_link_resolves",
    "group_size_equation", "group_count_pair", "group_bbox_ordered",
    "shape_colour_ref", "shape_colour_pair", "shape_text_colour", "shape8_tail",
    "rec_0x3a_container", "rec_0x3b_empty", "rec_0x3f_label",
    "rec_0x4e_element_size", "rec_0x52_container", "borderart_0x1f_container",
    "image_record_base",
    "header_document_id", "header_post_header_offset", "header_page_id_resolves",
    "directory_id_hwm_is_max_id", "directory_flags_writer_bits",
    "freelist_0x1f_chain", "freelist_0x3a_chain", "rec_0x3a_arena",
]


def freelist_chain(slots, head, term):
    """spec/11 §11.3.1: the words of an offset table that are not byte offsets are the
    links of one free list.  A slot is live when its value is >= n+1 (a byte offset,
    always >= the table size), free when it is a slot index; the list starts at the head
    and ends at `term` (0xFFFF / 0xFFFFFFFF).  Return (ok, free_indices)."""
    n = len(slots) - 1
    free = set(i for i, v in enumerate(slots) if i < n and (v < n + 1 or v == term))
    seen = []
    cur = head
    while cur != term:
        if cur > n or cur in seen:
            return False, free
        seen.append(cur)
        cur = slots[cur]
    return set(seen) == free, free


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
    # spec/04 §4.7/§4.9/§4.10: the fixed id base, the flag-word bit domain, the
    # default tab interval in twips, and the coordinate-system enumeration.
    if len(dc.data) < 0x3E:
        fail("document_id_base", "id=%#06x size=%d short" % (dc.id, dc.size))
    else:
        if struct.unpack_from("<H", dc.data, 0x0E)[0] != 1:
            fail("document_id_base", "u16@+0x0E=%d" % struct.unpack_from("<H", dc.data, 0x0E)[0])
        flags = struct.unpack_from("<H", dc.data, 0x0A)[0]
        if flags & ~0x161E:
            fail("document_flags_domain", "flags=%#06x" % flags)
        coord = struct.unpack_from("<H", dc.data, 0x12)[0]
        if coord not in (0, 1, 3, 4, 5, 6, 7, 8):
            fail("document_coord_system", "coordSystem=%d" % coord)
        tab = struct.unpack_from("<H", dc.data, 0x3C)[0]
        if tab not in (360, 432, 720, 1296):
            fail("document_tab_interval", "u16@+0x3C=%d" % tab)
    width = struct.unpack_from("<I", dc.data, 0x14)[0]
    height = struct.unpack_from("<I", dc.data, 0x18)[0]

    # Contents header cross-references (spec 02 §2.4 / §2.4.1).
    hdr_doc_id = struct.unpack_from("<H", d, 0x0E)[0]
    if hdr_doc_id != dc.id:
        fail("header_document_id", "%#06x != %#06x" % (hdr_doc_id, dc.id))
    post_header = struct.unpack_from("<I", d, 0x1A)[0]
    if post_header != 0x22:
        fail("header_post_header_offset", "%d != 34" % post_header)
    view_page = struct.unpack_from("<H", d, 0x10)[0]
    page_ids = {c.id for c in doc.of_type(0x14)} | {c.id for c in doc.of_type(0x41)}
    if view_page != 0 and view_page not in page_ids:
        fail("header_page_id_resolves", "%#06x is not a PAGE id" % view_page)
    # Directory header: the writer computes D+2 as max(id) (spec 03 §3.5).
    dir_off = doc.trailer_offset
    if ids:
        hwm = struct.unpack_from("<H", d, dir_off + 2)[0]
        if hwm != max(ids):
            fail("directory_id_hwm_is_max_id", "%#06x != %#06x" % (hwm, max(ids)))
    # Flags bits the writer normalises (spec 03 §3.6.2): bit 6 set, bits 11/15 clear.
    for c in doc.chunks:
        if c.flags & 0x8840 != 0x0040:
            fail("directory_flags_writer_bits", "id=%#06x flags=%#06x" % (c.id, c.flags))
            break

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
        if c.type_marker in (0x00, 0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08):
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
        elif 0x00 <= c.type_marker <= 0x07 or c.type_marker == 0x16:
            # B at +0x03 is the writer-side fixed record length (it does not grow with the
            # optional counted tail): 92/96/116/116 for 0x00..0x03, 59/62/53/41/16 for the rest.
            expected_b = RECORD_LEN_B.get(c.type_marker)
            base = RECORD_BASE.get(c.type_marker, 0)
            if expected_b and c.data[3] not in expected_b:
                fail("record_length_byte", "id=%#06x type=%#06x B=%d expected=%s"
                     % (c.id, c.type_marker, c.data[3], sorted(expected_b)))
            if c.size < base:
                fail("record_min_size", "id=%#06x type=%#06x size=%d base=%d"
                     % (c.id, c.type_marker, c.size, base))
            # Every 95/97 shape record carries a colour reference at +0x23 (spec 06 §6.7).
            if c.type_marker <= 0x07 and c.data[3] == RECORD_LEN_B_9597[c.type_marker]:
                if len(c.data) < 0x27:
                    fail("shape_colour_ref", "id=%#06x type=%#06x short" % (c.id, c.type_marker))
                else:
                    ref = struct.unpack_from("<I", c.data, 0x23)[0]
                    if not colour_ref_ok(ref):
                        fail("shape_colour_ref", "id=%#06x type=%#06x ref=%#010x"
                             % (c.id, c.type_marker, ref))
                # The two colour references at +0x18/+0x1C (spec 06 §6.7.7): +0x18 is 0 or a
                # reference, +0x1C is 0, 1 ("none") or a reference. 21925/21925 records.
                if len(c.data) >= 0x20:
                    ref_a = struct.unpack_from("<I", c.data, 0x18)[0]
                    ref_b = struct.unpack_from("<I", c.data, 0x1C)[0]
                    if ref_a != 0 and not colour_ref_ok(ref_a):
                        fail("shape_colour_pair", "id=%#06x type=%#06x +0x18=%#010x"
                             % (c.id, c.type_marker, ref_a))
                    if ref_b not in (0, 1) and not colour_ref_ok(ref_b):
                        fail("shape_colour_pair", "id=%#06x type=%#06x +0x1C=%#010x"
                             % (c.id, c.type_marker, ref_b))
                # The text colour of an image/polygon record lives at +0x70 and may be -1.
                if c.type_marker in (0x02, 0x03) and len(c.data) >= 0x74:
                    ref = struct.unpack_from("<I", c.data, 0x70)[0]
                    if ref != 0xFFFFFFFF and not colour_ref_ok(ref):
                        fail("shape_text_colour", "id=%#06x type=%#06x ref=%#010x"
                             % (c.id, c.type_marker, ref))
        elif c.type_marker == 0x08:
            # Publisher 98 shape-list record: base 0x80, counted tail of u16 chunk ids
            # (spec 06 §6.4.2). The count is stored twice and the element size word is 2.
            if c.data[3] != SHAPE8_B:
                fail("record_length_byte", "id=%#06x type=%#06x B=%d expected=%d"
                     % (c.id, c.type_marker, c.data[3], SHAPE8_B))
            if c.size < SHAPE8_BASE + 6:
                fail("shape8_tail", "id=%#06x short size=%d" % (c.id, c.size))
                continue
            n = struct.unpack_from("<H", c.data, 0x76)[0]
            n2 = struct.unpack_from("<H", c.data, 0x78)[0]
            elem = struct.unpack_from("<H", c.data, 0x7A)[0]
            if c.size != SHAPE8_BASE + elem * n:
                fail("shape8_tail", "id=%#06x size=%d n=%d elem=%d" % (c.id, c.size, n, elem))
            if n != n2:
                fail("shape8_tail", "id=%#06x count %d != %d" % (c.id, n, n2))
            if elem != 2:
                fail("shape8_tail", "id=%#06x elem=%d expected=2" % (c.id, elem))
        elif c.type_marker == 0x22:
            if c.size != 18:
                fail("record_length_byte", "record_min_size", "record_0x22_is_18", "id=%#06x size=%d" % (c.id, c.size))
    # GROUP 0x000F: counted child list; +8 shift in Publisher 98 (descriptor 0x20).
    for c in doc.of_type(0x0F):
        if len(c.data) < 0x24:
            fail("group_size_equation", "id=%#06x short" % c.id)
            continue
        p98 = c.data[2] == 0x20
        cnt_off, arr_off = (0x20, 0x2A) if p98 else (0x18, 0x22)
        n = struct.unpack_from("<H", c.data, cnt_off)[0]
        n2 = struct.unpack_from("<H", c.data, cnt_off + 2)[0]
        if c.size != arr_off + 2 * n:
            fail("group_size_equation", "id=%#06x size=%d n=%d base=%#x"
                 % (c.id, c.size, n, arr_off))
        if n != n2:
            fail("group_count_pair", "id=%#06x %d != %d" % (c.id, n, n2))
        if len(c.data) >= 0x16:
            x0, y0, x1, y1 = struct.unpack_from("<iiii", c.data, 6)
            if x0 > x1 or y0 > y1:
                fail("group_bbox_ordered", "id=%#06x box=(%d,%d,%d,%d)" % (c.id, x0, y0, x1, y1))

    # ---- spec/11 §11.12: Publisher 97-era records (0x003A/0x003B/0x003F) ----------
    # 0x003A is a u32 offset-table container in both the empty and the populated form:
    # count duplicated at +0x04/+0x08, end == size-0x16, last slot == end.
    for c in doc.of_type(0x3A):
        d = c.data
        if len(d) < 0x1A:
            fail("rec_0x3a_container", "id=%#06x size=%d short" % (c.id, c.size))
            continue
        n = struct.unpack_from("<I", d, 4)[0]
        n2 = struct.unpack_from("<I", d, 8)[0]
        end = struct.unpack_from("<I", d, 0x0C)[0]
        if (n != n2 or end != c.size - 0x16 or c.size < 0x16 + 4 * (n + 1)
                or struct.unpack_from("<H", d, 0x10)[0] != 1):
            fail("rec_0x3a_container", "id=%#06x size=%d n=%d" % (c.id, c.size, n))
        elif struct.unpack_from("<I", d, 0x16 + 4 * n)[0] != end:
            fail("rec_0x3a_container", "id=%#06x last slot != end" % c.id)

    for c in doc.of_type(0x3B):
        if (c.size != 26 or struct.unpack_from("<I", c.data, 4)[0] != 0
                or struct.unpack_from("<I", c.data, 0x0C)[0] != 4
                or struct.unpack_from("<I", c.data, 0x16)[0] != 4):
            fail("rec_0x3b_empty", "id=%#06x size=%d" % (c.id, c.size))

    for c in doc.of_type(0x3F):
        if c.size != 180 or struct.unpack_from("<I", c.data, 8)[0] != 1:
            fail("rec_0x3f_label", "id=%#06x size=%d" % (c.id, c.size))

    # ---- spec/11 §11.11.2: 0x004E/0x004F/0x0050 share a header whose +0x0E word is
    # the element size, so size == 0x14 + elementSize*n.
    for tm, elem in ((0x4E, 45), (0x4F, 11), (0x50, 5)):
        for c in doc.of_type(tm):
            if c.size < 0x14:
                fail("rec_0x4e_element_size", "id=%#06x size=%d short" % (c.id, c.size))
                continue
            n, n2, e = struct.unpack_from("<HHH", c.data, 0x0A)
            if n != n2 or e != elem or c.size != 0x14 + elem * n:
                fail("rec_0x4e_element_size", "id=%#06x n=%d e=%d size=%d"
                     % (c.id, n, e, c.size))

    # ---- spec/11 §11.11.1: 0x0052, 40 + 34*n with a 30-byte record size word and a
    # 0x7FFFFFFF terminator after the sorted key array.
    for c in doc.of_type(0x52):
        d = c.data
        if len(d) < 0x28:
            fail("rec_0x52_container", "id=%#06x size=%d short" % (c.id, c.size))
            continue
        n, n2 = struct.unpack_from("<HH", d, 0x12)
        elem = struct.unpack_from("<H", d, 0x16)[0]
        if n != n2 or elem != 0x1E or c.size != 40 + 34 * n:
            fail("rec_0x52_container", "id=%#06x n=%d elem=%d size=%d"
                 % (c.id, n, elem, c.size))
        elif struct.unpack_from("<I", d, 0x24 + 4 * n)[0] != 0x7FFFFFFF:
            fail("rec_0x52_container", "id=%#06x missing sentinel" % c.id)

    # ---- spec/11 §11.6: 0x001F is an offset-table container in two widths; the form is
    # detected by exact fit (the (A,B) stamp is 0x0404 in every instance) and the last
    # slot always equals the end offset.
    for c in doc.of_type(0x1F):
        d = c.data
        L = c.size
        w16 = (L >= 0x0E
               and struct.unpack_from("<H", d, 6)[0] == struct.unpack_from("<H", d, 4)[0]
               and struct.unpack_from("<H", d, 8)[0] == L - 0x0E)
        w32 = (L >= 0x10
               and struct.unpack_from("<I", d, 8)[0] == struct.unpack_from("<I", d, 4)[0]
               and struct.unpack_from("<I", d, 0x0C)[0] == L - 0x16)
        if w16 == w32:
            fail("borderart_0x1f_container", "id=%#06x size=%d form ambiguous" % (c.id, L))
            continue
        if w16:
            n = struct.unpack_from("<H", d, 4)[0]
            base, w, end = 0x0E, 2, L - 0x0E
        else:
            n = struct.unpack_from("<I", d, 4)[0]
            base, w, end = 0x16, 4, L - 0x16
        if base + w * (n + 1) > L:
            fail("borderart_0x1f_container", "id=%#06x n=%d overflows size=%d"
                 % (c.id, n, L))
            continue
        offs = struct.unpack_from("<%d%s" % (n + 1, "H" if w == 2 else "I"), d, base)
        if offs[-1] != end:
            fail("borderart_0x1f_container", "id=%#06x last slot %#x != end %#x"
                 % (c.id, offs[-1], end))

    # ---- spec/8 §8.7.1: the counted tail of 0x0002/0x0003 starts at the record's B
    # byte in both generations (95/97 B=116, 98 B=140), elements 8 bytes.
    for tm in (0x02, 0x03):
        for c in doc.of_type(tm):
            b = c.data[3]
            if b not in (116, 140) or c.size < b + 10:
                continue
            n, n2 = struct.unpack_from("<HH", c.data, b)
            if n != n2 or c.size != b + 10 + 8 * n:
                fail("image_record_base", "id=%#06x B=%d n=%d size=%d"
                     % (c.id, b, n, c.size))
            if (b == 140 and len(c.data) >= 0x8C
                    and (struct.unpack_from("<I", c.data, 0x78)[0] != 0xFFFFFFFF
                         or c.data[0x7C:0x8C] != b"\x00" * 16)):
                fail("image_record_base", "id=%#06x 98 tail landmarks" % c.id)

    # Embedded-object linkage: every 0x0022 ordinal must name an Objects/Object N storage.
    try:
        ole = olefile.OleFileIO(path)
        nums = set()
        for entry in ole.listdir():
            if len(entry) >= 2 and entry[0] == "Objects" and entry[1].startswith("Object "):
                try:
                    nums.add(int(entry[1][7:]))
                except ValueError:
                    pass
        for c in doc.of_type(0x22):
            if len(c.data) >= 0x0C:
                num = struct.unpack_from("<H", c.data, 0x0A)[0]
                if num not in nums:
                    fail("object_link_resolves", "id=%#06x ordinal=%d" % (c.id, num))
                    break
    except Exception as e:
        fail("object_link_resolves", "ole access: %s" % e)

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
            fail("quill_list_terminates", "object_link_resolves",
    "group_size_equation", "group_count_pair", "group_bbox_ordered", "walk failed at %#x" % off)
    stats["files"] += 1


def main():
    corpora = sys.argv[1:] or ["p95/x"]
    total = collections.Counter()
    failures = []
    for corpus in corpora:
        files = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
        files += sorted(f for f in glob.glob(os.path.join(corpus, "**", "*.JSP"), recursive=True)
                        if open(f, "rb").read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
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
