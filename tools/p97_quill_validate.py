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

CODE_FIXED = {1: 2, 2: 4, 3: 4, 4: 6}   # code -> total record size
CODE_VAR = (0x10, 0x11)                  # {u16 tag; u32 len; payload[len-4]}, total 2+len


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
    ndistinct = len(set(ids))
    aligned = (body + 3) & ~3
    pool = None
    for cand in range(min(aligned, len(blob)), len(blob)):
        blobs = walk_blobs(blob, cand)
        if blobs is not None and len(blobs) == ndistinct:
            pool = (cand, blobs)
            break
    if pool is None:
        errors.append("%s %s: no descriptor pool with %d entries" % (where, name, ndistinct))
        return
    for bp, size in pool[1]:
        if parse_descriptors(blob[bp + 4:bp + size]) is None:
            errors.append("%s %s: unparsable descriptor blob at %#x" % (where, name, bp))
            break
    return pool[0]


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
    """Family B: {u32 count; u32 elemSize; u8 f0,f1,f2,u8; u32 off[count+1]; elements}."""
    if len(blob) < 16:
        errors.append("%s %s: shorter than 16-byte header" % (where, name))
        return
    count, elem = struct.unpack_from("<II", blob, 0)
    if elem_hint is not None and elem != elem_hint:
        errors.append("%s %s: element size %d != %d" % (where, name, elem, elem_hint))
    total = 16 + 4 * count + count * elem
    if total != len(blob):
        errors.append("%s %s: size identity %d != %d" % (where, name, total, len(blob)))


def check_mcld(blob, errors, where):
    if len(blob) < 8:
        errors.append("%s MCLD: shorter than header" % where)
        return
    tag, count = struct.unpack_from("<II", blob, 0)
    if 8 + 4 * count > len(blob):
        errors.append("%s MCLD: id list exceeds chunk" % where)


# ---------------------------------------------------------------- per-file


def check_file(path):
    errors = []
    blob = read_quill(path)
    if blob is None:
        return ["no Quill stream"]
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
    for name, hint in (("BTEP", 4), ("BTEC", 4), ("TOKN", 0xC), ("TCD ", None)):
        for r in by_name.get(name, []):
            check_element_array(blob[r[3]:r[3] + r[4]], name, errors, path, hint)
    for r in by_name.get("MCLD", []):
        check_mcld(blob[r[3]:r[3] + r[4]], errors, path)
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
        files = sorted(glob.glob(files[0]))
    bad = 0
    for f in files:
        res = check_file(f)
        if isinstance(res, list):
            print("%-24s NO QUILL STREAM" % f)
            continue
        errors, names = res
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
