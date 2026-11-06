"""Font-slice instrumentation for the Publisher 95/97/98 family.

Subcommands:
  scan      per-corpus marker 0x6C count + 0x1E font-table parse validation
  names     print decoded font tables (optionally for one file)
  mfm       decode p98/x/FONTS.MFM table of contents
  embed     search every OLE stream of every doc for EOT / TTF payloads
  textsec   dump text-section header + 0x1D run records for one file
"""
from __future__ import annotations

import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import p98_corpus as pc

CORPORA = ["p95/x", "p97/ext2", "p97deluxe/x", "p98/x"]


# ---------------------------------------------------------------- 0x1E parse
def parse_font_table(data: bytes):
    """Parse a 0x1E chunk.  Returns dict or None.

    Layout (see notes/p98/slices/fonts.md):
      +0x00 u16 marker 0x001E
      +0x02 u16 constant 0x0408
      variant A (95):  +0x04 u16 n, +0x06 u16 n, +0x08 u16 bodyLen,
                       +0x0A u16 0x0001, +0x0C u16 0xFFFF, offsets u16 at +0x0E
      variant B (97+): +0x04 u32 n, +0x08 u32 n, +0x0C u32 bodyLen,
                       +0x10 u16 0x0001, +0x12 u16 0xFFFF, +0x14 u16 0xFFFF,
                       offsets u32 at +0x16
    Offsets are relative to the start of the offset array; record i occupies
    [off[i], off[i+1]); each record is 2 tag bytes + name + NUL terminator.
    """
    if len(data) < 14:
        return None
    marker, const = struct.unpack_from("<HH", data, 0)
    if marker != 0x1E:
        return None
    for variant, o in (("A", 0x0E), ("B", 0x16)):
        try:
            if variant == "A":
                n1, n2, body = struct.unpack_from("<HHH", data, 4)
                ok = data[0x0A:0x0E] == b"\x01\x00\xff\xff"
            else:
                n1, n2, body = struct.unpack_from("<III", data, 4)
                ok = data[0x10:0x16] == b"\x01\x00\xff\xff\xff\xff"
            if not ok:
                continue
            if n1 != n2 or n1 > 4096:
                continue
            width = 2 if variant == "A" else 4
            arr = o
            if arr + (n1 + 1) * width > len(data):
                continue
            if variant == "A":
                offs = list(struct.unpack_from("<%dH" % (n1 + 1), data, arr))
            else:
                offs = list(struct.unpack_from("<%dI" % (n1 + 1), data, arr))
            if offs[0] != (n1 + 1) * width:
                continue
            if offs[-1] != len(data) - arr or offs[-1] != body:
                continue
            if any(b <= a for a, b in zip(offs, offs[1:])):
                continue
            recs = []
            for a, b in zip(offs, offs[1:]):
                rec = data[arr + a:arr + b]
                if len(rec) < 3:
                    break
                tag = rec[0] | (rec[1] << 8)
                raw = rec[2:]
                if len(raw) >= 4 and raw[1] == 0 and raw[3] == 0:
                    enc = "utf16"
                    name = raw.decode("utf-16-le", "replace").rstrip("\x00")
                else:
                    enc = "ansi"
                    name = raw.rstrip(b"\x00").decode("latin-1")
                recs.append({"tag": tag, "name": name, "enc": enc,
                             "rawlen": len(raw)})
            if len(recs) != n1:
                continue
            return {"variant": variant, "const": const, "n": n1,
                    "body": body, "records": recs, "arr": arr}
        except (struct.error, UnicodeError):
            continue
    return None


# ------------------------------------------------------------------ MFM
def parse_mfm(path):
    data = open(path, "rb").read()
    # header: 52 bytes of task text (ASCII + 0x80), then 26-byte binary header
    hdr = 0x3A
    magic = data[0x3A:0x3E]
    # candidate: u32 count at 0x3E?
    out = {"size": len(data), "magic": magic.hex(), "records": []}
    rec0 = 0x54
    rec_size = 32
    n = 0
    p = rec0
    prev_end = 0
    while p + rec_size <= len(data):
        name = data[p:p+14]
        if not name.rstrip(b"\x00").endswith(b".PFM"):
            break
        off, size = struct.unpack_from("<II", data, p + 14)
        tail = struct.unpack_from("<5H", data, p + 22)
        out["records"].append({"name": name.rstrip(b"\x00").decode("latin-1"),
                               "off": off, "size": size, "tail": tail})
        n += 1
        p += rec_size
    out["count"] = n
    out["toc_end"] = p
    return out


# ------------------------------------------------------------------ main
def iter_docs(corpora=CORPORA):
    for corpus in corpora:
        for path, doc in pc.docs_only(pc.load(corpus)):
            yield corpus, path, doc


def cmd_scan():
    total_docs = total_chunks = 0
    per = {}
    font6c = []
    parsed = {}
    for corpus in CORPORA:
        pairs = pc.load(corpus)
        docs = pc.docs_only(pairs)
        n_chunks = 0
        c6c = []
        ft = {"A": 0, "B": 0, "B-utf16": 0, "B-ansi": 0, "A-ansi": 0,
              "fail": 0, "multi": 0, "files": 0}
        for path, doc in docs:
            n_chunks += len(doc.chunks)
            tabs = [c for c in doc.chunks if c.type_marker == 0x1E]
            for c in doc.chunks:
                if c.type_marker == 0x6C:
                    c6c.append((path, c.index, c.size))
            if not tabs:
                ft["fail"] += 1
            elif len(tabs) > 1:
                ft["multi"] += 1
            for c in tabs:
                r = parse_font_table(c.data)
                if r is None:
                    ft["fail"] += 1
                else:
                    ft["files"] += 1
                    ft[r["variant"]] += 1
                    if r["variant"] == "B":
                        encs = {x["enc"] for x in r["records"]}
                        k = "B-utf16" if "utf16" in encs else "B-ansi"
                        ft[k] += 1
        per[corpus] = (len(docs), n_chunks, ft, c6c)
        total_docs += len(docs)
        total_chunks += n_chunks
        font6c += c6c
    print("TOTAL docs=%d chunks=%d  0x6C chunks=%d" % (total_docs, total_chunks, len(font6c)))
    for corpus, (nd, nc, ft, c6c) in per.items():
        print("%-14s docs=%3d chunks=%5d 0x6C=%d  0x1E: %s"
              % (corpus, nd, nc, len(c6c), ft))
    if font6c:
        print("0x6C hits:", font6c[:20])


def cmd_names(argv):
    for corpus, path, doc in iter_docs([argv[0]] if argv else CORPORA):
        for c in doc.chunks:
            if c.type_marker != 0x1E:
                continue
            r = parse_font_table(c.data)
            print("%s chunk@0x%x size=%d -> %s" % (path, c.offset, c.size,
                                                   "FAIL" if not r else
                                                   "%s n=%d" % (r["variant"], r["n"])))
            if r:
                for i, rec in enumerate(r["records"]):
                    print("   [%d] tag=0x%04x enc=%s %r" % (i, rec["tag"], rec["enc"], rec["name"]))


def cmd_mfm(argv):
    p = argv[0] if argv else "p98/x/FONTS.MFM"
    out = parse_mfm(p)
    print("size=%d records=%d toc_end=0x%x magic=%s" % (out["size"], out["count"], out["toc_end"], out["magic"]))
    recs = out["records"]
    if recs:
        last = recs[-1]
        print("first:", recs[0])
        print("last:", last, "last_end=", last["off"] + last["size"])
        print("sum sizes=", sum(r["size"] for r in recs), "datastart=?", out["toc_end"])
        bad = [r for a, r in zip(recs, recs[1:]) if r["off"] != a["off"] + a["size"]]
        print("non-contiguous:", len(bad), bad[:3])
        import collections
        print("tail histogram:", collections.Counter(r["tail"] for r in recs).most_common(8))
        print("first names:", [r["name"] for r in recs[:12]])


def cmd_textsec(argv):
    path = argv[0]
    d = pubcore.parse_contents(path)
    data = d.contents
    t = struct.unpack_from("<I", d.header, 0x12)[0]
    print("textoff=0x%x" % t)
    magic, rel, ver = struct.unpack_from("<HHH", data, t)
    dir_off, tstart, tend = struct.unpack_from("<III", data, t + 0x0A)
    c1, c2, c3, c4 = struct.unpack_from("<HHHH", data, t + 0x16)
    o1, o2, o3, zero = struct.unpack_from("<IIII", data, t + 0x1E)
    print(" magic=0x%04x rel=0x%x ver=%d dir=0x%x text=[0x%x,0x%x) u16=%s offs=%s" %
          (magic, rel, ver, dir_off, tstart, tend, (c1, c2, c3, c4), (hex(o1), hex(o2), hex(o3))))
    print(" text bytes:", data[tstart:tend])
    for o in (o1, o2, o3):
        if not o:
            continue
        m = struct.unpack_from("<H", data, o)[0]
        print("  rec@0x%x type=0x%04x %s" % (o, m, data[o:o + 40].hex(" ")))


def cmd_embed():
    import re
    hits = []
    ttf_hits = []
    for corpus in CORPORA:
        for path, doc in pc.docs_only(pc.load(corpus)):
            blobs = [("Contents", doc.contents)]
            try:
                for name in pubcore.list_streams(path):
                    parts = name.split("\t")
                    if parts[0] != "stream":
                        continue
                    sn = parts[1]
                    try:
                        b = pubcore.read_stream(path, sn)
                    except Exception:
                        continue
                    if b and len(b) >= 16:
                        blobs.append((sn, b))
            except Exception:
                pass
            for sn, b in blobs:
                for m in re.finditer(rb"\x00\x01\x00\x00", b):
                    i = m.start()
                    if i + 12 <= len(b):
                        nt = struct.unpack_from("<H", b, i + 4)[0]
                        if 0 < nt < 200 and i + 12 + 16 * nt <= len(b):
                            for k in range(nt):
                                tag = b[i + 12 + 16 * k:i + 16 + 16 * k]
                                if tag == b"name":
                                    ttf_hits.append((path, sn, i))
                                    break
                # EOT: size, fontdata, version, ...
                for i in range(0, max(0, len(b) - 16)):
                    if b[i + 8:i + 12] in (b"\x00\x00\x01\x00", b"\x01\x00\x02\x00",
                                           b"\x02\x00\x02\x00", b"\x02\x00\x01\x00"):
                        sz = struct.unpack_from("<I", b, i)[0]
                        fd = struct.unpack_from("<I", b, i + 4)[0]
                        if sz == len(b) - i and 0 < fd < sz:
                            hits.append((path, sn, i, sz, fd))
    print("EOT-like:", len(hits))
    for h in hits[:20]:
        print("  ", h)
    print("TTF-like:", len(ttf_hits))
    for h in ttf_hits[:20]:
        print("  ", h)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    args = sys.argv[2:]
    {"scan": cmd_scan, "names": lambda: cmd_names(args),
     "mfm": lambda: cmd_mfm(args), "embed": cmd_embed,
     "textsec": lambda: cmd_textsec(args)}.get(cmd, cmd_scan)()
