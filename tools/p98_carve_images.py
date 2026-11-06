"""Carve and validate every IMAGE_DATA (chunk marker 0x0021) payload.

Measured model (see notes/p98/slices/images.md):

    chunk  := u16 0x0021 | u16 0x0800 | u32 L | L bytes
              ^+0         ^+2         ^+4       ^+8
    L == chunkSize-8  (100% of 527 chunks in p95/x, p97/ext2, p97deluxe/x)

    The L-byte payload is a WMF metafile (or, in principle, another format).
    WMF header (METAHEADER, 18 bytes):
        +0  u16 mtType       (1 = memory, 2 = disk)
        +2  u16 mtHeaderSize (words; 9 -> 18 bytes)
        +4  u16 mtVersion    (0x0300)
        +6  u32 mtSize       (words, INCLUDING the 18-byte header)
        +10 u16 mtNoObjects
        +12 u32 mtMaxRecord  (words)
        +16 u16 mtNoParameters
    Records start at mtHeaderSize*2 and are
        u32 size (words, includes the 6-byte record header) | u16 function | params

Usage
-----
    python tools/p98_carve_images.py                 # carve + report
    python tools/p98_carve_images.py --report-only   # do not write files
    python tools/p98_carve_images.py --corpora p95/x p97/ext2

Written files land in notes/p98/carved/<corpus-tag>/<stem>_c<index>_<id>.<ext>
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore  # noqa: E402

DEFAULT_CORPORA = ["p95/x", "p97/ext2", "p97deluxe/x", "p98/x"]
DEFAULT_OUT = os.path.join("notes", "p98", "carved")

# ---------------------------------------------------------------- WMF consts
WMF_RECORDS = {
    0x0000: "EOF", 0x001E: "SAVEDC", 0x0035: "REALIZEPALETTE",
    0x0037: "SETPALENTRIES", 0x0102: "SETBKMODE", 0x0103: "SETMAPMODE",
    0x0104: "SETROP2", 0x0106: "SETPOLYFILLMODE", 0x0107: "SETSTRETCHBLTMODE",
    0x0108: "SETTEXTCHAREXTRA", 0x0127: "RESTOREDC", 0x012A: "INVERTREGION",
    0x012B: "PAINTREGION", 0x012C: "SELECTCLIPREGION", 0x012D: "SELECTOBJECT",
    0x012E: "SETTEXTALIGN", 0x0139: "RESIZEPALETTE", 0x0142: "DIBCREATEPATTERNBRUSH",
    0x01F0: "DELETEOBJECT", 0x01F9: "CREATEPATTERNBRUSH", 0x0201: "SETBKCOLOR",
    0x0209: "SETTEXTCOLOR", 0x020A: "SETTEXTJUSTIFICATION", 0x020B: "SETWINDOWORG",
    0x020C: "SETWINDOWEXT", 0x020D: "SETVIEWPORTORG", 0x020E: "SETVIEWPORTEXT",
    0x020F: "OFFSETWINDOWORG", 0x0211: "OFFSETVIEWPORTORG", 0x0213: "LINETO",
    0x0214: "MOVETO", 0x0220: "OFFSETCLIPRGN", 0x0228: "FILLREGION",
    0x0231: "SETMAPPERFLAGS", 0x0234: "SELECTPALETTE", 0x0324: "POLYGON",
    0x0325: "POLYLINE", 0x0410: "SCALEWINDOWEXT", 0x0412: "SCALEVIEWPORTEXT",
    0x0415: "EXCLUDECLIPRECT", 0x0416: "INTERSECTCLIPRECT", 0x0418: "ELLIPSE",
    0x0419: "FLOODFILL", 0x041B: "RECTANGLE", 0x041F: "SETPIXEL",
    0x0429: "FRAMEREGION", 0x0436: "ANIMATEPALETTE", 0x0521: "TEXTOUT",
    0x0538: "POLYPOLYGON", 0x0548: "EXTFLOODFILL", 0x061C: "ROUNDRECT",
    0x061D: "PATBLT", 0x0626: "ESCAPE", 0x062F: "DRAWTEXT", 0x06FF: "CREATEREGION",
    0x0817: "ARC", 0x081A: "PIE", 0x0830: "CHORD", 0x0922: "BITBLT",
    0x0940: "DIBBITBLT", 0x0A32: "EXTTEXTOUT", 0x0B23: "STRETCHBLT",
    0x0B41: "DIBSTRETCHBLT", 0x0D33: "SETDIBTODEV", 0x0F43: "STRETCHDIB",
    0x02FA: "CREATEPENINDIRECT", 0x02FB: "CREATEFONTINDIRECT",
    0x02FC: "CREATEBRUSHINDIRECT", 0x00F7: "CREATEPALETTE",
    0x0219: "RESERVED219?",
}
RASTER_RECORDS = {"DIBBITBLT", "DIBSTRETCHBLT", "SETDIBTODEV", "STRETCHDIB",
                  "DIBCREATEPATTERNBRUSH", "CREATEPATTERNBRUSH", "BITBLT",
                  "STRETCHBLT"}

# -------------------------------------------------------------- format sniff
# Ordered most-specific first.
SIGNATURES = [
    (b"\x01\x00\x09\x00\x00\x03", "wmf"),
    (b"\xd7\xcd\xc6\x9a", "wmf-placeable"),
    (b"\x01\x00\x00\x00", "emf"),           # refined by the EMF ' EMF' dword
    (b"\x42\x4d", "bmp"),
    (b"\xff\xd8", "jpeg"),
    (b"\x89PNG", "png"),
    (b"GIF8", "gif"),
    (b"\x00\x00\x01\x00", "ico"),
]


def sniff(payload: bytes) -> str:
    """Return a format tag for a 0x21 payload."""
    for sig, name in SIGNATURES:
        if payload.startswith(sig):
            if name == "emf":
                # EMF: iType==1, then ' EMF' at +0x28
                if len(payload) >= 0x2C and payload[0x28:0x2C] == b" EMF":
                    return "emf"
                continue
            return name
    if len(payload) >= 8 and payload[:8] == b"\xd7\xcd\xc6\x9a":
        return "wmf-placeable"
    if len(payload) >= 4 and payload[0:4] == b"\x00\x00\x02\x00":
        return "pict?"
    if len(payload) >= 4 and struct.unpack_from("<I", payload, 0)[0] == 0x00090001:
        return "wmf"
    return "unknown:" + payload[:8].hex()


def wmf_walk(payload: bytes):
    """Walk a standard (non-placeable) WMF.

    Returns dict:
        ok      bool  header sane, record walk lands exactly on mtSize
        mt      (type, hdrwords, version, size, nobj, maxrec, nparams)
        consumed  bytes consumed by the record stream (header + records)
        records   list of (offset, words, function)
        eof       True if the last record was META_EOF
        err       str or None
    """
    out = {"ok": False, "mt": None, "consumed": 0, "records": [],
           "eof": False, "err": None}
    if len(payload) < 18:
        out["err"] = "shorter than 18-byte METAHEADER"
        return out
    mt = struct.unpack_from("<HHHIHIH", payload, 0)
    out["mt"] = mt
    mtype, hdrw, ver, size, nobj, maxrec, npar = mt
    if hdrw != 9:
        out["err"] = "mtHeaderSize=%d (expected 9)" % hdrw
        return out
    declared = size * 2          # bytes, includes the 18-byte header
    off = hdrw * 2
    recs = []
    while True:
        if off + 6 > len(payload):
            out["err"] = "record header past end at %#x" % off
            break
        rw, fn = struct.unpack_from("<IH", payload, off)
        if rw < 3:
            out["err"] = "record size %d words < 3 at %#x" % (rw, off)
            break
        rsize = rw * 2
        if off + rsize > len(payload):
            out["err"] = "record at %#x overruns payload (%d > %d)" % (
                off, off + rsize, len(payload))
            break
        recs.append((off, rw, fn))
        off += rsize
        if fn == 0x0000:                     # META_EOF
            out["eof"] = True
            break
    out["records"] = recs
    out["consumed"] = off
    if out["err"] is None and out["eof"] and off == declared:
        out["ok"] = True
    elif out["err"] is None and out["eof"] and off != declared:
        out["err"] = "walk ends %#x, mtSize says %#x" % (off, declared)
    return out


def iter_docs(corpora):
    for corp in corpora:
        files = sorted(f for f in glob.glob(os.path.join(corp, "**", "*"),
                                            recursive=True)
                       if f.lower().endswith(".pub"))
        for f in files:
            yield corp, f


def corpus_tag(corp: str) -> str:
    return corp.replace("\\", "/").strip("/").replace("/", "_")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="*", default=DEFAULT_CORPORA)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args(argv)

    framing = collections.Counter()     # (marker, tag, L==size-8)
    formats = collections.Counter()     # per corpus format tag
    vt = collections.Counter()          # wmf header shape (type,hdr,ver)
    rel = collections.Counter()         # L - mtSize*2
    rel_all = collections.Counter()
    slack = collections.Counter()       # L - consumed
    pad_nonzero = 0
    n_carved = 0
    n_valid = 0
    fails = []
    raster = collections.Counter()
    per_corpus = collections.Counter()
    carved_paths = []

    for corp, path in iter_docs(args.corpora):
        try:
            doc = pubcore.parse_contents(path)
        except Exception as e:                      # pragma: no cover
            print("PARSE-FAIL %s: %s" % (path, e), file=sys.stderr)
            continue
        stem = os.path.splitext(os.path.basename(path))[0]
        tag = corpus_tag(corp)
        for ch in doc.chunks:
            if ch.type_marker != 0x21:
                continue
            per_corpus[corp] += 1
            b = ch.data
            ok_frame = len(b) >= 8
            m0, m1, L = (struct.unpack_from("<HH", b, 0) + (0,))[:3] \
                if len(b) >= 6 else (None, None, None)
            if len(b) >= 8:
                m0, m1, L = struct.unpack_from("<HHI", b, 0)
            framing[(m0, m1, L == ch.size - 8)] += 1
            payload = b[8:]
            fmt = sniff(payload)
            formats[(corp, fmt)] += 1
            if fmt == "wmf":
                info = wmf_walk(payload)
                mt = info["mt"]
                if mt:
                    vt[(mt[0], mt[1], mt[2])] += 1
                    rel[L - mt[3] * 2] += 1
                rel_all[L - (mt[3] * 2 if mt else 0)] += 1
                if mt:
                    slack[L - info["consumed"]] += 1
                tail = payload[info["consumed"]:] if info["consumed"] else b""
                if any(tail):
                    pad_nonzero += 1
                for _off, _w, fn in info["records"]:
                    nm = WMF_RECORDS.get(fn)
                    if nm in RASTER_RECORDS:
                        raster[nm] += 1
                if info["ok"]:
                    n_valid += 1
                else:
                    fails.append((path, ch.index, info["err"]))
            else:
                fails.append((path, ch.index, "non-WMF payload: " + fmt))

            if not args.report_only:
                d = os.path.join(args.out, tag)
                os.makedirs(d, exist_ok=True)
                ext = fmt.split(":")[0]
                if ext == "wmf-placeable":
                    ext = "wmf"
                fn = "%s_c%03d_%03x.%s" % (stem, ch.index, ch.id, ext)
                p = os.path.join(d, fn)
                with open(p, "wb") as fh:
                    fh.write(payload)
                carved_paths.append(p)
                n_carved += 1

    # ------------------------------------------------------------- report
    print("== IMAGE_DATA (0x21) framing ==")
    for k, v in sorted(framing.items(), key=lambda kv: -kv[1]):
        print("  marker=%s tag=%s L==size-8=%s : %d" % (
            "0x%04X" % k[0] if k[0] is not None else None,
            "0x%04X" % k[1] if k[1] is not None else None, k[2], v))
    print("== chunks per corpus ==")
    for k, v in sorted(per_corpus.items()):
        print("  %-14s %d" % (k, v))
    print("== payload format tag ==")
    for k, v in sorted(formats.items()):
        print("  %-14s %-24s %d" % (k[0], k[1], v))
    print("== WMF METAHEADER (mtType, mtHeaderSize, mtVersion) ==")
    for k, v in vt.most_common():
        print("  %s : %d" % (k, v))
    print("== L - mtSize*2 (bytes of trailing padding) ==")
    for k, v in sorted(rel.items()):
        print("  %d : %d" % (k, v))
    print("== L - record-walk-end ==")
    for k, v in sorted(slack.items()):
        print("  %d : %d" % (k, v))
    print("  payloads with non-zero trailing bytes: %d" % pad_nonzero)
    print("== raster records inside the metafiles ==")
    for k, v in raster.most_common():
        print("  %-22s %d" % (k, v))
    print("== validation ==")
    print("  carved %d, WMF-valid %d, failures %d" % (n_carved, n_valid, len(fails)))
    for f in fails[:20]:
        print("  FAIL %s idx %d: %s" % f)
    if not args.report_only:
        print("  files written under %s" % args.out)


if __name__ == "__main__":
    main()
