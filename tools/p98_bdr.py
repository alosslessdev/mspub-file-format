#!/usr/bin/env python3
"""Independent decoder for the Publisher 95/97/98 border-art library `PUBBRD/*.BDR`.

Verified against the Publisher 98 binary (see notes/p98/slices/borderart.md):
  VA 0x0048292A  loads the entry names
  VA 0x0058A55E  compares one entry's image blob against the cached copy
  VA 0x004831EE  loads an entry's 8 tile WMFs into an in-memory record
  VA 0x004818A0  renders a border from that record
  VA 0x00483CA6  returns record->bandThicknessTwips * 635 (EMU per twip)

File layout
-----------
  0x00  u16  magic       0x5458 = 'XT' (ANSI names) | 0x6CF8 (UTF-16LE names)
  0x02  u16  version     always 1
  0x04  u16  count N     number of border-art entries
  0x06  N * R  name records, R = 42 (ANSI) / 84 (UTF-16LE), NUL-padded
  0x06+N*R  N * 22  entry records
  +22       sentinel record (band = 0, all 8 tile offsets = file length)
  ...       payload area: tile WMFs, concatenated

Entry record (22 bytes, all little endian):
  +0x00 u16 bandThickness   twips (x635 -> EMU)      corners are this x this
  +0x02 u16 edgeTileWidth   twips, logical width  of the horizontal edge tile
  +0x04 u16 edgeTileHeight  twips, logical height of the vertical edge tile
  +0x06 u16 tileOffset[8]   byte offsets *relative to the start of this record*

Tile slot order is clockwise from the top-left corner:
  0 TL corner, 1 top edge, 2 TR corner, 3 right edge,
  4 BR corner, 5 bottom edge, 6 BL corner, 7 left edge

A tile spans [record+tileOffset[k], record+tileOffset[k] + wmfSize) where
wmfSize = u32 @ (tile+6) * 2 (standard 18-byte WMF header, word count -> bytes).
Offsets are non-decreasing within a record; equal offsets mean "reuse the same
image in several slots".  The last record's payload runs to the file length,
which the sentinel's tileOffset[0] also states.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import struct
import sys

MAGIC_ANSI = 0x5458
MAGIC_WIDE = 0x6CF8
NAME_ANSI = 42
NAME_WIDE = 84
REC = 22
SLOTS = ("TL", "top", "TR", "right", "BR", "bottom", "BL", "left")


def parse(path):
    d = open(path, "rb").read()
    magic, version, count = struct.unpack_from("<3H", d, 0)
    if magic not in (MAGIC_ANSI, MAGIC_WIDE):
        raise ValueError("%s: not a .BDR (magic %#06x)" % (path, magic))
    namesz = NAME_ANSI if magic == MAGIC_ANSI else NAME_WIDE
    doc = {
        "path": path,
        "size": len(d),
        "magic": magic,
        "version": version,
        "count": count,
        "namesz": namesz,
        "names_off": 6,
        "recs_off": 6 + namesz * count,
        "sentinel_off": 6 + namesz * count + REC * count,
        "data_off": 6 + namesz * count + REC * (count + 1),
        "entries": [],
        "sentinel": None,
    }
    if doc["data_off"] > len(d):
        raise ValueError("%s: truncated table" % path)

    for i in range(count):
        raw = d[6 + i * namesz: 6 + (i + 1) * namesz]
        if namesz == NAME_WIDE:
            name = raw.decode("utf-16-le", "replace").split("\x00")[0]
        else:
            name = raw.split(b"\x00")[0].decode("latin-1")
        rec = doc["recs_off"] + REC * i
        band, ew, eh = struct.unpack_from("<3H", d, rec)
        offs = list(struct.unpack_from("<8H", d, rec + 6))
        doc["entries"].append({
            "index": i, "name": name, "raw_name": raw, "rec_off": rec,
            "band_twips": band, "edge_w_twips": ew, "edge_h_twips": eh,
            "slot_off": offs, "slots": [],
        })

    srec = doc["sentinel_off"]
    sband = struct.unpack_from("<3H", d, srec)
    soffs = list(struct.unpack_from("<8H", d, srec + 6))
    doc["sentinel"] = {"off": srec, "band": sband, "slot_off": soffs}

    # Resolve each slot to an absolute extent.  The end of a tile is the next
    # distinct absolute offset exercised anywhere in the file (entry slots then
    # the sentinel), which equals the WMF size for every tile in the corpus.
    starts = set()
    for e in doc["entries"]:
        for o in e["slot_off"]:
            starts.add(e["rec_off"] + o)
    starts.add(srec + soffs[0])
    ordered = sorted(s for s in starts if s <= len(d))

    for e in doc["entries"]:
        seen = {}
        for k, o in enumerate(e["slot_off"]):
            p = e["rec_off"] + o
            if p in seen:  # duplicate slot: point at the same tile record
                t = dict(seen[p])
                t["k"] = k
                t["slot"] = SLOTS[k]
                e["slots"].append(t)
                continue
            nxt = next((s for s in ordered if s > p), len(d))
            wmf = None
            size_ok = False
            if d[p:p + 4] == b"\x01\x00\x09\x00":
                wmf = struct.unpack_from("<I", d, p + 6)[0] * 2
                size_ok = (wmf == nxt - p)
            t = {"k": k, "slot": SLOTS[k], "abs": p, "next": nxt,
                 "span": nxt - p, "wmf_size": wmf, "size_ok": size_ok,
                 "sig": d[p:p + 4].hex(), "sha1": hashlib.sha1(d[p:nxt]).hexdigest()}
            seen[p] = t
            e["slots"].append(t)
        e["unique"] = sorted({s["abs"] for s in e["slots"]})
    return doc


def problems(doc):
    bad = []
    seen_names = {}
    for e in doc["entries"]:
        if not e["name"]:
            bad.append("entry %d: empty name" % e["index"])
        if e["name"] in seen_names:
            bad.append("entry %d: duplicate name %r (first at %d)"
                       % (e["index"], e["name"], seen_names[e["name"]]))
        seen_names.setdefault(e["name"], e["index"])
        prev = -1
        for k, o in enumerate(e["slot_off"]):
            if o < prev:
                bad.append("entry %d: slot offset %d decreases at slot %d" % (e["index"], o, k))
            prev = o
            s = e["slots"][k]
            if not s["size_ok"]:
                bad.append("entry %d slot %s: span %d != wmf %s @%#x"
                           % (e["index"], s["slot"], s["span"], s["wmf_size"], s["abs"]))
        if len(set(e["unique"])) > 8:
            bad.append("entry %d: more than 8 unique tiles" % e["index"])
    s = doc["sentinel"]
    if s["band"] != (0, 0, 0):
        bad.append("sentinel band %r not zero" % (s["band"],))
    if len(set(s["slot_off"])) != 1:
        bad.append("sentinel offsets not constant: %r" % (s["slot_off"],))
    if doc["sentinel_off"] + s["slot_off"][0] != doc["size"]:
        bad.append("sentinel offset %#x + %#x != file length %#x"
                   % (doc["sentinel_off"], s["slot_off"][0], doc["size"]))
    # payload area must be exactly covered, with no gaps between records
    if doc["entries"]:
        first = min(t["abs"] for e in doc["entries"] for t in e["slots"])
        if first != doc["data_off"]:
            bad.append("first payload at %#x != table end %#x" % (first, doc["data_off"]))
    return bad


def extract(doc, outdir):
    os.makedirs(outdir, exist_ok=True)
    d = open(doc["path"], "rb").read()
    stem = os.path.splitext(os.path.basename(doc["path"]))[0]
    out = []
    for e in doc["entries"]:
        safe = "".join(c if c.isalnum() or c in " -_()" else "_" for c in e["name"]).strip()
        for abs_off in e["unique"]:
            t = next(s for s in e["slots"] if s["abs"] == abs_off)
            fn = "%s_%02d_%s_%06x.wmf" % (stem, e["index"], safe.replace(" ", ""), abs_off)
            p = os.path.join(outdir, fn)
            with open(p, "wb") as fh:
                fh.write(d[abs_off:abs_off + t["span"]])
            out.append({"entry": e["index"], "name": e["name"], "slots":
                        [s["slot"] for s in e["slots"] if s["abs"] == abs_off],
                        "file": p, "offset": abs_off, "size": t["span"],
                        "sha1": t["sha1"]})
    return out


def wmf_extent(buf):
    """Return (xext, yext, records) of a non-placeable WMF payload."""
    size = struct.unpack_from("<I", buf, 6)[0] * 2
    q, end, ext, recs = 18, min(size, len(buf)), None, 0
    while q + 6 <= end:
        w, fn = struct.unpack_from("<IH", buf, q)
        if w == 0:
            break
        recs += 1
        if fn == 0x020C and q + 10 <= end:  # META_SETWINDOWEXT (y, x)
            y, x = struct.unpack_from("<hh", buf, q + 6)
            ext = (x, y)
        q += w * 2
    return ext, recs, size


def main():
    args = sys.argv[1:]
    outdir = None
    if "--extract" in args:
        i = args.index("--extract")
        outdir = args[i + 1]
        del args[i:i + 2]
    targets = []
    for a in args or ["p98/x/PUBBRD"]:
        targets += sorted(glob.glob(os.path.join(a, "*.BDR"))) if os.path.isdir(a) else [a]
    total_e = total_t = 0
    for p in targets:
        doc = parse(p)
        bad = problems(doc)
        uniq = sum(len(e["unique"]) for e in doc["entries"])
        total_e += doc["count"]
        total_t += uniq
        print("%-13s m=%#06x v=%d n=%2d recs@%#06x sent@%#06x data@%#06x size=%6d tiles=%3d bad=%d"
              % (os.path.basename(p), doc["magic"], doc["version"], doc["count"],
                 doc["recs_off"], doc["sentinel_off"], doc["data_off"], doc["size"], uniq, len(bad)))
        for b in bad:
            print("    !", b)
        if outdir:
            w = extract(doc, os.path.join(outdir, os.path.splitext(os.path.basename(p))[0]))
            with open(os.path.join(outdir, os.path.splitext(os.path.basename(p))[0] + ".json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"path": p, "entries": doc["count"], "tiles": w}, fh, indent=1)
            print("    extracted %d payloads under %s/" % (len(w), os.path.splitext(os.path.basename(p))[0]))
    print("TOTAL files=%d entries=%d unique-payloads=%d" % (len(targets), total_e, total_t))


if __name__ == "__main__":
    main()
