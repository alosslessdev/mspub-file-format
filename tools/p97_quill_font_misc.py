"""Decode the Quill (QS98) stream directory and the FONT / STSH name-table chunks.

Evidence generator for notes/p97/slices/quill_font_misc.md.

Facts this script demonstrates (QS98 = p98/quill/QS98.DLL):
 * Quill stream layout: 0x20-byte header ("CHNK"+"INK "), 24-byte directory
   records at +0x20, chunk payloads from the offset in each record.
 * Directory record = 24 bytes: u16 size, u32 name, u16 id, u16 a, u16 b,
   u32 class, u32 offset, u32 size.
 * Name-table chunk (FONT, STSH) payload:
       +0x00 u32 dataBytes      (== payloadLen - 20)
       +0x04 u32 recordCount
       +0x08 u32 0x0012C57C
       +0x0C u32 extSize        (bytes of trailer per record)
       +0x10 u8  flag, u8[3] A6 A7 32
       +0x14 u32 offset[recordCount]   (relative to +0x14)
            record = u16 cch, cch*UTF-16LE, extSize bytes
   Verified by: dataBytes == recordCount*4 + sum(2 + 2*cch + extSize).

Usage: python tools/p97_quill_font_misc.py [p98/x]
"""
from __future__ import annotations

import hashlib
import os
import struct
import sys

import olefile

STREAM = "Quill/QuillSub/CONTENTS"
NAME_TABLE = {"STSH", "FONT"}


def quill_stream(pub: str) -> bytes:
    ole = olefile.OleFileIO(pub)
    return ole.openstream(STREAM).read()


def directory(d: bytes):
    """Return (header_fields, records)."""
    hdr = {
        "magic": d[0:4],
        "tag": d[4:8],
        "u16_08": struct.unpack_from("<H", d, 0x08)[0],
        "version": struct.unpack_from("<H", d, 0x0A)[0],
        "count_0c": struct.unpack_from("<H", d, 0x0C)[0],
        "u16_0e": struct.unpack_from("<H", d, 0x0E)[0],
        "dirBytes": struct.unpack_from("<I", d, 0x10)[0],
        "usedEnd": struct.unpack_from("<I", d, 0x14)[0],
        "dataOff": struct.unpack_from("<H", d, 0x18)[0],
        "count_1a": struct.unpack_from("<H", d, 0x1A)[0],
        "u32_1c": struct.unpack_from("<I", d, 0x1C)[0],
    }
    recs = []
    base = 0x20
    for i in range(struct.unpack_from("<H", d, 0x0C)[0]):
        r = d[base + i * 0x18: base + (i + 1) * 0x18]
        size, name, rid, fa, fb, cls, off, ln = struct.unpack("<HIHHHIII", r)
        recs.append({
            "size": size, "name": name.to_bytes(4, "little").decode("latin-1"),
            "id": rid, "a": fa, "b": fb,
            "class": cls.to_bytes(4, "little").decode("latin-1"),
            "off": off, "len": ln,
        })
    return hdr, recs


def decode_name_table(p: bytes):
    data_bytes, count, magic, ext, flag = struct.unpack_from("<IIIII", p, 0)
    tail = p[0x11:0x14]
    offs = list(struct.unpack_from("<%dI" % count, p, 0x14))
    print("    dataBytes=%d (payload-20=%d) count=%d magic=%#x extSize=%d flag=%#x tag=%s"
          % (data_bytes, len(p) - 20, count, magic, ext, flag & 0xFF,
             tail.hex(" ") if isinstance(tail, bytes) else ""))
    base = 0x14
    total = count * 4
    for i, o in enumerate(offs):
        cch = struct.unpack_from("<H", p, base + o)[0]
        raw = p[base + o + 2: base + o + 2 + cch * 2]
        s = raw.decode("utf-16-le", "replace")
        tra = p[base + o + 2 + cch * 2: base + o + 2 + cch * 2 + ext]
        print("    [%d] off=%d cch=%d name=%r trailer=%s%s"
              % (i, o, cch, s, tra.hex(" "),
                 (" u16=%d" % struct.unpack_from("<H", tra, 0)[0]) if len(tra) >= 2 else ""))
        total += 2 + cch * 2 + ext
    print("    computed data bytes=%d  (%s)" % (total, "OK" if total == data_bytes else "MISMATCH"))


def main(corpus: str) -> int:
    pubs = sorted(os.path.join(corpus, f) for f in os.listdir(corpus)
                  if f.lower().endswith(".pub"))
    for pub in pubs:
        d = quill_stream(pub)
        print("== %s  quill stream %d B  md5 %s" % (pub, len(d), hashlib.md5(d).hexdigest()))
        hdr, recs = directory(d)
        print("   header:", " ".join("%s=%s" % (k, h if isinstance(h, bytes) else hex(h))
                                     for k, h in hdr.items()))
        for r in recs:
            p = d[r["off"]:r["off"] + r["len"]]
            print("   [%d] %-4r id=%d a=%d b=%d class=%-4r off=%#x len=%d %s"
                  % (recs.index(r), r["name"], r["id"], r["a"], r["b"], r["class"],
                     r["off"], r["len"], p[:12].hex(" ")))
            if r["name"].strip() in NAME_TABLE:
                decode_name_table(p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "p98/x"))
