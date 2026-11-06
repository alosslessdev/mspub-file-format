"""Structural validation of the Publisher 98 Quill story stream (Quill/QuillSub/CONTENTS).

Every check below is a *measured identity* from spec/13-quill.md; this script re-derives
them over every Quill-bearing document in the corpus.  It never modifies anything.

Usage:  python tools/p97_quill_validate.py [file ...]
Exit code 0 = no violations.
"""
import glob
import struct
import sys

import olefile

QUILL = "Quill/QuillSub/CONTENTS"

DEFAULT_FILES = [
    "p98/x/MSPUB.PUB",
    "p98/x/ZMSPUB.PUB",
    "p98/x/CHEKLIST.JSP",
    "p98/x/CLRCHK.JSP",
    "p98/x/INFOSHET.JSP",
]

# ---------------------------------------------------------------- container


def read_quill(path):
    o = olefile.OleFileIO(path)
    try:
        if not o.exists(QUILL):
            return None
        return o.openstream(QUILL).read()
    finally:
        o.close()


def parse_directory(blob, errors):
    """Return [(name, id, name2, off, len)] in stream order."""
    sig, tag, subver, ver, nrec, f0e, dircap, logical = struct.unpack_from("<4s4sHHHHII", blob, 0)
    if sig != b"CHNK":
        errors.append("header signature %r != CHNK" % sig)
    if tag != b"INK ":
        errors.append("header tag %r != 'INK '" % tag)
    if subver >= 8:
        errors.append("sub-version %d >= 8" % subver)
    if ver < 1:
        errors.append("version %d < 1" % ver)
    if logical > len(blob):
        errors.append("logical size %#x > physical %#x" % (logical, len(blob)))
    if dircap >= len(blob):
        errors.append("directory capacity %#x >= stream size" % dircap)
    if nrec and len(blob) <= 0x3FF:
        errors.append("non-empty directory in a stream < 0x400 bytes")

    recs = []
    off = 0x18
    seen = set()
    while True:
        if off in seen:
            errors.append("directory page loop at %#x" % off)
            break
        seen.add(off)
        if off + 8 > len(blob):
            errors.append("page header past end at %#x" % off)
            break
        cap, cnt, nxt = struct.unpack_from("<HHI", blob, off)
        if cnt >= 0x8000:
            errors.append("negative page count at %#x" % off)
            break
        p = off + 8
        for _ in range(cnt):
            if p + 24 > len(blob):
                errors.append("record past end at %#x" % p)
                return recs
            size, name, rid, f8, f10, name2, roff, rlen = struct.unpack_from(
                "<H4sHHH4sII", blob, p)
            if size < 0x18 or p + size > len(blob):
                errors.append("bad record size %d at %#x" % (size, p))
                return recs
            if roff + rlen > len(blob):
                errors.append("chunk %r runs past end (%#x+%#x)" % (name, roff, rlen))
            recs.append((name, rid, name2, roff, rlen))
            p += size
        if len(recs) >= nrec:
            break
        if nxt == 0xFFFFFFFF:
            break
        off = nxt
    if len(recs) != nrec:
        errors.append("record count %d != header count %d" % (len(recs), nrec))
    return recs


# ---------------------------------------------------------------- descriptor streams

CODE_FIXED = {0: 2, 1: 2, 2: 4, 3: 4, 4: 6, 5: 10,
              0x1C: 2, 0x1D: 2, 0x1E: 2}   # code -> total record size
CODE_VAR = (0x10, 0x11)                  # {u16 tag; u32 len; payload[len-4]}, total 2+len
# The full 32-entry code -> size table is data in QS98.DLL at VA 0x404680C8 (stride 8),
# indexed by tag >> 11 and read by FUN_404076b1. Codes 0 (explicit zero), 1 (boolean
# true), 5 (two u32) and 0x1C-0x1E (merge markers) are real; 0x06-0x0F/0x12-0x1B are
# id-only like code 0 and Publisher 98 never emits them, so the walker below rejects
# them rather than accepting noise as a valid stream.


def parse_descriptors(data):
    """Walk a field-descriptor stream; return list of (field_id, code, size) or None."""
    p, out = 0, []
    while p < len(data):
        if p + 2 > len(data):
            return None
        tag = struct.unpack_from("<H", data, p)[0]
        code = tag >> 11
        if code in CODE_FIXED:
            n = CODE_FIXED[code]
        elif code in CODE_VAR:
            if p + 6 > len(data):
                return None
            n = 2 + struct.unpack_from("<I", data, p + 2)[0]
        else:
            return None
        if n < 2 or p + n > len(data):
            return None
        out.append((tag & 0x7FF, code, n))
        p += n
    return out


def walk_blobs(blob, start):
    """Chain {u32 size; size-4 bytes} to the end of the buffer; None if it does not fit."""
    pos, out = start, []
    while pos < len(blob):
        if pos + 4 > len(blob):
            return None
        size = struct.unpack_from("<I", blob, pos)[0]
        if size < 4 or pos + size > len(blob):
            return None
        out.append((pos, size))
        pos += size
    return out if pos == len(blob) else None


def pool_of(blob, count, ids):
    """Locate the right-aligned descriptor pool of an FDPP/FDPC chunk; None if absent.

    The writer fills the 512-byte page backwards, so the slack between the id array and
    the pool is unwritten and the pool has to be found by its end: the first candidate
    offset whose {u32 size; size-4} chain covers the chunk with exactly one blob per
    distinct id.
    """
    ndistinct = len(set(ids))
    aligned = (8 + 6 * count + 3) & ~3
    for cand in range(min(aligned, len(blob)), len(blob)):
        blobs = walk_blobs(blob, cand)
        if blobs is not None and len(blobs) == ndistinct:
            return blobs
    return None


def check_fdp(blob, name, errors, where):
    """FDPP / FDPC: header + pos[] + id[] + right-aligned descriptor pool."""
    count, ver, start = struct.unpack_from("<HHI", blob, 0)
    if ver != 1:
        errors.append("%s %s: version word %d != 1" % (where, name, ver))
    body = 8 + 6 * count
    if body > len(blob):
        errors.append("%s %s: table (%d records) exceeds chunk" % (where, name, count))
        return
    pos = struct.unpack_from("<%dI" % count, blob, 8) if count else ()
    ids = struct.unpack_from("<%dH" % count, blob, 8 + 4 * count) if count else ()
    if any(pos[i] > pos[i + 1] for i in range(count - 1)):
        errors.append("%s %s: positions not ascending" % (where, name))
    pool = pool_of(blob, count, ids)
    if pool is None:
        errors.append("%s %s: no descriptor pool with %d entries"
                      % (where, name, len(set(ids))))
        return
    for bp, size in pool:
        if parse_descriptors(blob[bp + 4:bp + size]) is None:
            errors.append("%s %s: unparsable descriptor blob at %#x" % (where, name, bp))
            break


def check_table20(blob, name, errors, where):
    """STSH / FONT: 20-byte prologue + u32 offsets (rel. to +0x14) + records."""
    if len(blob) < 20:
        errors.append("%s %s: shorter than prologue" % (where, name))
        return
    size, count, _flags, trail = struct.unpack_from("<IIII", blob, 0)
    if size != len(blob) - 20:
        errors.append("%s %s: prologue size %d != len-20 (%d)" % (where, name, size, len(blob) - 20))
    if 20 + 4 * count > len(blob):
        errors.append("%s %s: %d offsets exceed chunk" % (where, name, count))
        return
    offs = struct.unpack_from("<%dI" % count, blob, 20) if count else ()
    if count and offs[0] != 4 * count:
        errors.append("%s %s: first offset %d != 4*count" % (where, name, offs[0]))
    trail_sz = trail & 0x3FFF
    for i, o in enumerate(offs):
        p = 20 + o
        if p + 2 > len(blob):
            errors.append("%s %s: entry %d offset out of range" % (where, name, i))
            continue
        cch = struct.unpack_from("<H", blob, p)[0]
        if p + 2 + 2 * cch + trail_sz > len(blob):
            errors.append("%s %s: entry %d (cch=%d) runs past chunk" % (where, name, i, cch))
    if count:
        expect = 4 * count + sum(
            2 + 2 * struct.unpack_from("<H", blob, 20 + o)[0] + trail_sz for o in offs)
        if expect != size:
            errors.append("%s %s: size identity %d != %d" % (where, name, size, expect))


def check_strs(blob, errors, where):
    """STRS: 12-byte header + (count+1) u32 + count {u32 size; descriptor stream}."""
    if len(blob) < 12:
        errors.append("%s STRS: shorter than header" % where)
        return
    count, elem = struct.unpack_from("<II", blob, 0)
    if elem != 8:
        errors.append("%s STRS: element size %d != 8" % (where, elem))
    pos = 12 + 4 * (count + 1)
    if pos > len(blob):
        errors.append("%s STRS: offset table exceeds chunk" % where)
        return
    for _ in range(count):
        if pos + 4 > len(blob):
            errors.append("%s STRS: entry header past end" % where)
            return
        size = struct.unpack_from("<I", blob, pos)[0]
        if size < 4 or pos + size > len(blob):
            errors.append("%s STRS: entry size %d at %#x" % (where, size, pos))
            return
        if parse_descriptors(blob[pos + 4:pos + size]) is None:
            errors.append("%s STRS: unparsable entry at %#x" % (where, pos))
        pos += size
    if pos != len(blob):
        errors.append("%s STRS: %d trailing bytes" % (where, len(blob) - pos))


def check_element_array(blob, name, errors, where, elem_hint=None):
    """Family B: {u32 count; u32 elemSize; u8 f0,f1,f2,u8; u32 off[count+1]; elements}.

    Two payload forms exist and both are measured (spec 13.10). Contiguous (mode -1 in
    FUN_404223b4): count * elemSize bytes. Packed (any other mode, FUN_4042251d): count x
    {u32 len; len-4 bytes of descriptor stream} followed by the 6-byte trailer
    {tag 0x2200 = 0xFFFFFFFF}.
    """
    if len(blob) < 12:
        errors.append("%s %s: shorter than 12-byte header" % (where, name))
        return
    count, elem = struct.unpack_from("<II", blob, 0)
    if elem_hint is not None and elem != elem_hint:
        errors.append("%s %s: element size %d != %d" % (where, name, elem, elem_hint))
    hdr = 12 + 4 * (count + 1)
    if hdr > len(blob):
        errors.append("%s %s: %d offsets exceed chunk" % (where, name, count + 1))
        return
    offs = struct.unpack_from("<%dI" % (count + 1), blob, 12)
    if any(offs[i] > offs[i + 1] for i in range(count)):
        errors.append("%s %s: offsets not ascending" % (where, name))
    if hdr + count * elem == len(blob):
        return
    p, walk_ok = hdr, True
    for _ in range(count):
        if p + 4 > len(blob):
            walk_ok = False
            break
        n = struct.unpack_from("<I", blob, p)[0]
        if n < 4 or p + n > len(blob) or parse_descriptors(blob[p + 4:p + n]) is None:
            walk_ok = False
            break
        p += n
    if walk_ok and blob[p:] == b"\x0a\x00\x00\x00\x00\x22\xff\xff\xff\xff":
        return
    errors.append("%s %s: neither contiguous (%d) nor packed (%s, tail %d) form fits %d"
                  % (where, name, hdr + count * elem,
                     "ok" if walk_ok else "unparsable", len(blob) - p, len(blob)))


# ---- the QS98.DLL property-class tables (spec 13.17) --------------------------------
# id -> the on-disk codes the class declares; ('f',) = boolean, code 0 or 1.
# Derived from the table at VA 0x40463AD8 (page directory) / 0x40463ADC (id sets),
# 6-byte descriptors at pageBase + ((id & 0x1FF) >> shift) * 6.


def _codes(spec):
    out = {}
    for item in spec.split():
        fid, code = item.split(":")
        out[int(fid, 16)] = ("f",) if code == "f" else (int(code, 0),)
    return out


CLASS_1_CODES = _codes(          # text-run (character) properties, carrier FDPC
    "200:2 202:f 203:f 204:f 205:f 208:2 20c:4 20f:2 210:f 211:4 212:4 213:f "
    "214:f 215:f 216:f 217:f 218:4 21a:4 21b:4 21c:f 21d:3 21e:2 21f:3 220:3 "
    "222:4 223:4 224:0x11 229:3 22a:3 22b:3 22d:f 22e:4 22f:4 230:4 231:4")

CLASS_2_CODES = _codes(          # paragraph properties, carrier FDPP
    "200:2 202:4 203:3 204:2 205:4 206:4 208:2 20a:f 20c:4 20d:4 20e:4 212:4 "
    "213:4 214:4 215:4 216:4 217:f 218:f 219:3 21a:2 21b:f 21c:f 21d:f 21e:2 "
    "21f:4 220:2 221:4 222:4 223:4 224:4 225:2 22a:2 22c:2 22d:2 230:2 231:2 "
    "232:0x10 233:2 234:4 235:4 236:2 237:2 239:2")

CLASS_12_CODES = _codes(         # MCLD document-object record
    "200:4 201:4 202:4 203:4 204:4 205:4 206:4 207:4 208:4 209:4 20a:4 20b:3 "
    "20c:f 20d:4 20e:4 211:4 212:4 213:2 214:f 215:4 216:4 217:4 218:4 219:f 21a:f")

CLASS_18_CODES = _codes("200:f 201:4")       # MCLD object header

CLASS_12_STREAM = 130            # sum of the 25 encoded widths


def check_class_stream(buf, codes, errors, where, label):
    """Every tag in one descriptor stream must be a field of the class it is used as."""
    recs = parse_descriptors(buf)
    if recs is None:
        errors.append("%s %s: unparsable stream (%d bytes)" % (where, label, len(buf)))
        return None
    for fid, code, _n in recs:
        want = codes.get(fid)
        if want is None:
            errors.append("%s %s: id %#x not in the class" % (where, label, fid))
        elif want == ("f",):
            if code not in (0, 1):
                errors.append("%s %s: boolean id %#x written with code %d"
                              % (where, label, fid, code))
        elif code != want[0]:
            errors.append("%s %s: id %#x code %d != class type %d"
                          % (where, label, fid, code, want[0]))
    return recs


def check_mcld(blob, errors, where):
    """{u32 tag; u32 count; u32 ids[count];
        count x {u32 12; class-18 stream; u32 n; n x {u32 134; class-12 stream}}}"""
    if len(blob) < 8:
        errors.append("%s MCLD: shorter than header" % where)
        return
    tag, count = struct.unpack_from("<II", blob, 0)
    if 8 + 4 * count > len(blob):
        errors.append("%s MCLD: id list exceeds chunk" % where)
        return
    ids = list(struct.unpack_from("<%dI" % count, blob, 8)) if count else []
    if ids != sorted(set(ids)):
        errors.append("%s MCLD: object ids not strictly ascending" % where)
    p = 8 + 4 * count
    for oid in ids:
        if p + 4 > len(blob):
            errors.append("%s MCLD: object %d: header past end" % (where, oid))
            return
        size_a = struct.unpack_from("<I", blob, p)[0]
        if size_a != 12 or p + size_a > len(blob):
            errors.append("%s MCLD: object %d: header size %d != 12" % (where, oid, size_a))
            return
        check_class_stream(blob[p + 4:p + size_a], CLASS_18_CODES, errors, where,
                           "MCLD/%d/header" % oid)
        p += size_a
        if p + 4 > len(blob):
            errors.append("%s MCLD: object %d: block count past end" % (where, oid))
            return
        nblk = struct.unpack_from("<I", blob, p)[0]
        p += 4
        for k in range(nblk):
            if p + 4 > len(blob):
                errors.append("%s MCLD: object %d block %d: size past end" % (where, oid, k))
                return
            size_b = struct.unpack_from("<I", blob, p)[0]
            if size_b != CLASS_12_STREAM + 4:
                errors.append("%s MCLD: object %d block %d: size %d != %d"
                              % (where, oid, k, size_b, CLASS_12_STREAM + 4))
                return
            if p + size_b > len(blob):
                errors.append("%s MCLD: object %d block %d: %d bytes past end"
                              % (where, oid, k, p + size_b - len(blob)))
                return
            recs = check_class_stream(blob[p + 4:p + size_b], CLASS_12_CODES, errors, where,
                                      "MCLD/%d/block%d" % (oid, k))
            if recs is not None and [r[0] for r in recs] != sorted(CLASS_12_CODES):
                errors.append("%s MCLD: object %d block %d: fields not the full class 12 set"
                              % (where, oid, k))
            p += size_b
    if p != len(blob):
        errors.append("%s MCLD: %d trailing bytes" % (where, len(blob) - p))


def check_run_index(blob, recs, name, part, errors, where):
    """BTEP/BTEC: element i is the stream offset of chunk `part` id i; offsets[] its chain."""
    r = [x for x in recs if x[0] == name]
    chunks = [x for x in recs if x[0] == part]
    if len(r) != 1:
        errors.append("%s %s: %d records (expected 1)" % (where, name, len(r)))
        return
    b = blob[r[0][3]:r[0][3] + r[0][4]]
    if len(b) < 12:
        return
    count, elem = struct.unpack_from("<II", b, 0)
    if elem != 4:
        errors.append("%s %s: element size %d != 4" % (where, name, elem))
        return
    if count != len(chunks):
        errors.append("%s %s: %d elements but %d %s chunks"
                      % (where, name, count, len(chunks), part))
        return
    elems = list(struct.unpack_from("<%dI" % count, b, 12 + 4 * (count + 1))) if count else []
    offs = list(struct.unpack_from("<%dI" % (count + 1), b, 12))
    for i, (nm, rid, _n2, roff, rlen) in enumerate(chunks):
        if rid != i:
            errors.append("%s %s: element %d has directory id %d"
                          % (where, name.decode(), i, rid))
            continue
        if elems[i] != roff:
            errors.append("%s %s: element %d = %#x != %s offset %#x"
                          % (where, name.decode(), i, elems[i], part.decode(), roff))
            continue
        sub = blob[roff:roff + rlen]
        if len(sub) < 8:
            continue
        cnt2, _ver, start = struct.unpack_from("<HHI", sub, 0)
        if start != offs[i]:
            errors.append("%s %s: element %d start %#x != %#x"
                          % (where, name.decode(), i, start, offs[i]))
        last = struct.unpack_from("<I", sub, 8 + 4 * (cnt2 - 1))[0] if cnt2 else start
        if last != offs[i + 1]:
            errors.append("%s %s: element %d last pos %#x != %#x"
                          % (where, name.decode(), i, last, offs[i + 1]))


# ---------------------------------------------------------------- per-file


def check_text97(path, blob, doc, errors):
    """Publisher 95/97: the text pool pointer triple inside the Contents header."""
    diroff = doc.trailer_offset
    cand = [o for o in range(0x22, min(len(blob) - 12, 0x600), 2)
            if struct.unpack_from("<I", blob, o)[0] == diroff]
    good = None
    for o in cand:
        a, z = struct.unpack_from("<II", blob, o + 4)
        if 0x22 <= a <= z <= len(blob):
            good = (o, a, z)
            break
    if good is None:
        errors.append("no text-pool triple (diroff=%#x)" % diroff)
        return None
    o, a, z = good
    seg = blob[a:z]
    # Invariants measured over 114 documents: the pool is NUL-free and every CR is
    # followed by an LF (the counts are equal in every file).
    if 0 in seg:
        errors.append("text pool %#x..%#x contains a NUL byte" % (a, z))
    if seg.count(b"\n") > seg.count(b"\r"):
        errors.append("text pool %#x..%#x: %d LF vs %d CR (LF must be part of CRLF)"
                      % (a, z, seg.count(b"\n"), seg.count(b"\r")))
    return o, a, z


def check_file(path):
    errors = []
    blob = read_quill(path)
    if blob is None:
        try:
            import pubcore
            doc = pubcore.parse_contents(path)
        except Exception as exc:            # no Contents either
            return ["no Quill stream and no Contents: %s" % exc]
        triple = check_text97(path, doc.contents, doc, errors)
        return errors, ("text97 %#x..%#x" % (triple[1], triple[2])) if triple else "text97 ?"
    recs = parse_directory(blob, errors)
    names = [r[0] for r in recs]
    by_name = {}
    for r in recs:
        by_name.setdefault(r[0], []).append(r)

    if "INK " in by_name:
        r = by_name["INK "][0]
        if r[4] < 4:
            errors.append("INK chunk shorter than 4")
        else:
            v, v2 = struct.unpack_from("<HH", blob, r[3])
            if v < 0x68 or v2 >= 0x73 or 0x6A <= v <= 0x6B:
                errors.append("INK version %#x/%#x rejected by the loader gate" % (v, v2))
    if "SGP " in by_name:
        r = by_name["SGP "][0]
        if r[4] < 4 or struct.unpack_from("<I", blob, r[3])[0] > r[4]:
            errors.append("SGP size word exceeds chunk")

    text_end = None
    if "TEXT" in by_name:
        r = by_name["TEXT"][0]
        if r[4] % 2:
            errors.append("TEXT length %d is not a multiple of 2" % r[4])
        try:
            blob[r[3]:r[3] + r[4]].decode("utf-16-le")
        except UnicodeDecodeError:
            errors.append("TEXT is not valid UTF-16LE")
        text_end = r[3] + r[4]

    for name in ("FDPP", "FDPC"):
        for r in by_name.get(name, []):
            check_fdp(blob[r[3]:r[3] + r[4]], name, errors, path)
    if text_end is not None:
        for name in ("FDPP", "FDPC"):
            for r in by_name.get(name, []):
                b = blob[r[3]:r[3] + r[4]]
                count = struct.unpack_from("<H", b, 0)[0]
                if count:
                    last = struct.unpack_from("<I", b, 8 + 4 * (count - 1))[0]
                    if last > text_end:
                        errors.append("%s: last position %#x past TEXT end %#x"
                                      % (name, last, text_end))

    for name in ("STSH", "FONT"):
        for r in by_name.get(name, []):
            check_table20(blob[r[3]:r[3] + r[4]], name, errors, path)
    if "STRS" in by_name:
        r = by_name["STRS"][0]
        check_strs(blob[r[3]:r[3] + r[4]], errors, path)
    for name, hint in ((b"BTEP", 4), (b"BTEC", 4), (b"TOKN", 0xC), (b"TCD ", None)):
        for r in by_name.get(name, []):
            check_element_array(blob[r[3]:r[3] + r[4]], name.decode("latin-1"), errors,
                                path, hint)
    for name, part in ((b"BTEP", b"FDPP"), (b"BTEC", b"FDPC")):
        if name in by_name:
            check_run_index(blob, recs, name, part, errors, path)
    for r in by_name.get(b"MCLD", []):
        check_mcld(blob[r[3]:r[3] + r[4]], errors, path)
    # FDPP is the paragraph class, FDPC the text-run class (spec 13.17): every id in
    # every descriptor blob must be a field of that class, written with its type code.
    for name, codes in ((b"FDPP", CLASS_2_CODES), (b"FDPC", CLASS_1_CODES)):
        for r in by_name.get(name, []):
            b = blob[r[3]:r[3] + r[4]]
            if len(b) < 8:
                continue
            count = struct.unpack_from("<H", b, 0)[0]
            ids = [struct.unpack_from("<H", b, 8 + 4 * count + 2 * i)[0] for i in range(count)]
            for bp, size in pool_of(b, count, ids) or []:
                check_class_stream(b[bp + 4:bp + size], codes, errors, path,
                                   "%s blob@%#x" % (name.decode(), bp))
    if "SYID" in by_name:
        for r in by_name["SYID"]:
            b = blob[r[3]:r[3] + r[4]]
            if len(b) >= 8:
                hwm, count = struct.unpack_from("<II", b, 0)
                if 8 + 4 * count != len(b):
                    errors.append("SYID size identity %d != %d" % (8 + 4 * count, len(b)))
    return errors, names


def main(argv):
    files = argv[1:] or DEFAULT_FILES
    if len(files) == 1 and any(c in files[0] for c in "*?"):
        pat = files[0]
        files = sorted(glob.glob(pat))
        if "**" not in pat:                     # also sweep subdirectories
            files += sorted(glob.glob(pat.replace("/*", "/**/*"), recursive=True))
            files = sorted(set(files))
    bad = 0
    for f in files:
        res = check_file(f)
        if isinstance(res, list):
            print("%-24s FAIL %s" % (f, res[0]))
            bad += 1
            continue
        errors, names = res
        if isinstance(names, str):          # Publisher 95/97 text-pool mode
            print("%-24s %s %s" % (f, "ok  " if not errors else "FAIL", names))
            for e in errors:
                print("    " + e)
            bad += bool(errors)
            continue
        if errors:
            bad += 1
            print("%-24s FAIL (%d)" % (f, len(errors)))
            for e in errors:
                print("    " + e)
        else:
            print("%-24s ok  %d records: %s" % (f, len(names), " ".join(sorted({n.decode("latin-1") for n in names}))))
    print("\n%d file(s), %d with violations" % (len(files), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
