"""Validate the Quill payload formulas against every p98 corpus document.

Checks
  family A (FONT, STSH):  dataBytes == count*4 + sum(2 + 2*cch + trailerSize)
  family B (BTEP, BTEC, STRS, TOKN, TCD, INK, EOBJ, FTN):
                          total == 16 + 4*N + N*elemSize   (+ name table if flag@0x0A)
Run: python tools/p97_quill_familyb_check.py
"""
from __future__ import annotations

import glob
import os
import struct
import sys

import olefile

STREAM = "Quill/QuillSub/CONTENTS"
FAMILY_A = {"FONT", "STSH"}
FAMILY_B = {"BTEP", "BTEC", "STRS", "TOKN", "TCD ", "INK ", "EOBJ", "FTN ", "EDN "}


def records(d: bytes):
    n = struct.unpack_from("<H", d, 0x1A)[0]
    out = []
    for i in range(n):
        r = d[0x20 + i * 0x18: 0x20 + (i + 1) * 0x18]
        if len(r) < 24:
            break
        size, name, rid, flags, cls, off, ln = struct.unpack("<HIHIIII", r)
        out.append((size, name.to_bytes(4, "little").decode("latin-1"), rid, flags,
                    cls.to_bytes(4, "little").decode("latin-1"), off, ln))
    return out


def check_a(p: bytes, tag: str):
    data_bytes, count, magic, trailer, flag = struct.unpack_from("<IIIII", p, 0)
    offs = struct.unpack_from("<%dI" % count, p, 0x14)
    total = count * 4
    names = []
    for o in offs:
        cch = struct.unpack_from("<H", p, 0x14 + o)[0]
        names.append(p[0x14 + o + 2: 0x14 + o + 2 + 2 * cch].decode("utf-16-le", "replace"))
        total += 2 + 2 * cch + trailer
    ok = (total == data_bytes == len(p) - 20)
    print("   %-5s A count=%d trailer=%d magic=%#x flag=%#x  data=%d calc=%d len-20=%d %s %s"
          % (tag, count, trailer, magic, flag & 0xFF, data_bytes, total, len(p) - 20,
             "OK" if ok else "MISMATCH", names if tag == "FONT" else ""))


def check_b(p: bytes, tag: str):
    n, es = struct.unpack_from("<II", p, 0)
    f = p[8:11].hex()
    has_nt = p[10] != 0
    calc = 16 + 4 * n + n * es
    ok = calc == len(p)
    print("   %-5s B N=%-4d elemSize=%-3d flags=%s nt=%d calc=%d len=%d %s"
          % (tag, n, es, f, has_nt, calc, len(p), "OK" if ok else "MISMATCH"))
    return n, es, ok


def main() -> int:
    files = sorted(glob.glob("p98/x/*"))
    for fn in files:
        if not os.path.isfile(fn) or os.path.getsize(fn) < 512:
            continue
        try:
            ole = olefile.OleFileIO(fn)
            if not ole.exists(STREAM):
                continue
            d = ole.openstream(STREAM).read()
        except Exception:
            continue
        print("== %s  %d B  hdr=%s" % (os.path.basename(fn), len(d), d[:0x20].hex(" ")))
        for (size, name, rid, flags, cls, off, ln) in records(d):
            if off + ln > len(d) or ln == 0:
                print("   BAD RECORD %r id=%d off=%#x len=%d" % (name, rid, off, ln))
                continue
            p = d[off:off + ln]
            tag = name.strip()
            if tag in FAMILY_A and len(p) >= 20:
                check_a(p, tag)
            elif tag in FAMILY_B and len(p) >= 16:
                check_b(p, tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
