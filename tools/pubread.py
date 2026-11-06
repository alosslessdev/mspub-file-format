"""Reference reader for Publisher 95/97/98 documents.

Implements exactly what spec/ documents, so the specification can be validated
mechanically: every parse here is a claim in the spec. Anything the spec does not
yet define is reported as `unknown` rather than guessed.

Usage:
    python pubread.py <file.pub>            # structural summary
    python pubread.py <file.pub> --json     # machine readable
    python pubread.py --corpus <dir>        # validate a whole corpus
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import palette as palette_table

EMU_PER_INCH = 914400

MAGIC = {0xACE8: "modern", 0xACE7: "legacy"}
FORMAT_VERSION = {200: "legacy-200", 300: "modern-300", 710: "legacy-710"}


class Reader:
    def __init__(self, path: str):
        self.path = path
        self.doc = pubcore.parse_contents(path)
        self.contents = self.doc.contents
        self.header = self._parse_header()
        self.pages = []
        self.shapes = []
        self.images = []
        self.quill = None
        self._build()

    # ---- container/header -------------------------------------------------
    def _parse_header(self) -> dict:
        d = self.contents
        magic = struct.unpack_from("<H", d, 0)[0]
        h = {
            "magic": magic,
            "magic_name": MAGIC.get(magic, "unknown"),
            "version_byte": d[2],
            "format_version": struct.unpack_from("<H", d, 4)[0],
            "declared_length": struct.unpack_from("<I", d, 8)[0],
            "actual_length": len(d),
            "field_0c": struct.unpack_from("<H", d, 0x0C)[0],
            "directory_offset": struct.unpack_from("<I", d, 0x16)[0],
        }
        h["length_matches"] = h["declared_length"] == h["actual_length"]
        h["format_name"] = FORMAT_VERSION.get(h["format_version"], "unknown")
        return h

    # ---- chunk graph ------------------------------------------------------
    def _build(self):
        by_id = {c.id: c for c in self.doc.chunks}
        self.by_id = by_id
        children = collections.defaultdict(list)
        for c in self.doc.chunks:
            children[c.parent].append(c)

        doc_chunk = next((c for c in self.doc.chunks if c.type_marker == 0x15), None)
        self.document_chunk = doc_chunk
        if doc_chunk is not None:
            data = doc_chunk.data
            self.document = {
                "id": doc_chunk.id,
                "size": doc_chunk.size,
                "coordinate_system": struct.unpack_from("<H", data, 0x12)[0],
                "width_emu": struct.unpack_from("<I", data, 0x14)[0],
                "height_emu": struct.unpack_from("<I", data, 0x18)[0],
                "width_in": struct.unpack_from("<I", data, 0x14)[0] / EMU_PER_INCH,
                "height_in": struct.unpack_from("<I", data, 0x18)[0] / EMU_PER_INCH,
            }
            self.document["pages"] = [c.id for c in children[doc_chunk.id]
                                      if c.type_marker == 0x14]

        for c in self.doc.chunks:
            if c.type_marker == 0x14:
                self.pages.append(self._parse_page(c, children))
            elif c.type_marker in (0x00, 0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x16):
                self.shapes.append(self._parse_shape(c))
            elif c.type_marker == 0x21:
                self.images.append(self._parse_image(c))

        self.palette = []
        for c in self.doc.of_type(0x47):
            if len(c.data) >= 0xA0 + 32:
                refs = struct.unpack_from("<8I", c.data, 0xA0)
                self.palette.append({
                    "id": c.id,
                    "size": c.size,
                    "scheme_name": c.data[0x0E:0x2E].decode("utf-16-le", "replace").rstrip("\0"),
                    "refs": ["%08x" % r for r in refs],
                    "rgb": [palette_table.decode_colorref(r) for r in refs],
                })

        try:
            blob = pubcore.read_stream(self.path, "Quill/QuillSub/CONTENTS")
        except Exception:
            blob = None
        if blob:
            self.quill = self._parse_quill(blob)

    def _parse_page(self, c, children):
        data = c.data
        page = {
            "id": c.id, "size": c.size, "type": "page",
            "child_count": struct.unpack_from("<H", data, 0x1A)[0] if len(data) >= 0x1C else 0,
            "shape_ids": [],
        }
        n = page["child_count"]
        off = 0x24
        if n and off + 2 * n <= len(data):
            page["shape_ids"] = list(struct.unpack_from("<%dH" % n, data, off))
        page["children"] = [x.id for x in children[c.id]]
        return page

    def _parse_shape(self, c):
        data = c.data
        s = {"id": c.id, "type_name": c.type_name, "size": c.size}
        if len(data) >= 0x16:
            s["rotation_tenths"] = struct.unpack_from("<H", data, 4)[0]  # 1/10 degree, mod 3600
            s["x0"], s["y0"], s["x1"], s["y1"] = struct.unpack_from("<iiii", data, 6)
            s["box_in"] = [round(v / EMU_PER_INCH, 3) for v in
                           (s["x0"], s["y0"], s["x1"], s["y1"])]
        return s

    def _parse_image(self, c):
        data = c.data
        img = {"id": c.id, "size": c.size}
        if len(data) >= 8:
            n = struct.unpack_from("<I", data, 4)[0]
            payload = data[8:8 + n]
            img["declared_payload"] = n
            img["payload"] = len(payload)
            img["signature"] = payload[:8].hex()
            img["format"] = sniff_image(payload)
        return img

    def _parse_quill(self, blob):
        """Quill chunk directory (Publisher 98 only).

        List header (8 bytes at the list offset, first list at 0x18):
            +0 u16 unknown (observed 0x0002), +2 u16 entry count, +4 u32 next list
        Entry record (24 bytes):
            +0 u16 0x18, +2 4cc name, +6 u16 id, +8 u32 flags, +0xC 4cc name2,
            +0x10 u32 data offset, +0x14 u32 data length
        The list chain ends when the next-list offset is 0xFFFFFFFF.
        """
        chunks = []
        # List header: {u16 tag, u16 count, u32 nextListOffset}; records follow.
        off = 0x18
        seen = set()
        while off != 0xFFFFFFFF and off + 8 <= len(blob) and off not in seen:
            seen.add(off)
            num = struct.unpack_from("<H", blob, off + 2)[0]
            nxt = struct.unpack_from("<I", blob, off + 4)[0]
            p = off + 8
            for _ in range(num):
                if p + 24 > len(blob):
                    break
                name = blob[p + 2:p + 6].decode("latin-1")
                cid = struct.unpack_from("<H", blob, p + 6)[0]
                flags = struct.unpack_from("<I", blob, p + 8)[0]
                name2 = blob[p + 12:p + 16].decode("latin-1")
                coff, clen = struct.unpack_from("<II", blob, p + 16)
                chunks.append({"name": name, "name2": name2, "id": cid,
                               "flags": flags, "offset": coff, "length": clen})
                p += 24
            off = nxt
        return chunks

    # ---- reporting --------------------------------------------------------
    def summary(self) -> dict:
        return {
            "path": self.path,
            "header": self.header,
            "document": getattr(self, "document", None),
            "pages": len(self.pages),
            "shapes": len(self.shapes),
            "images": self.images,
            "palette": self.palette,
            "quill_chunks": sorted({q["name"].strip() for q in self.quill}) if self.quill else [],
            "chunk_types": dict(sorted(collections.Counter(
                c.type_name for c in self.doc.chunks).items())),
        }


def sniff_image(b: bytes) -> str:
    if b[:4] == b"\xd7\xcd\xc6\x9a":
        return "wmf-placeable"
    if b[:4] == b"\x01\x00\x09\x00":
        return "wmf"
    if b[:4] == b"\x01\x00\x00\x00" and len(b) > 40 and b[40:44] == b" EMF":
        return "emf"
    if b[:2] == b"BM":
        return "bmp"
    if b[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if b[:4] in (b"\x00\x00\x01\x00", b"\x00\x00\x02\x00"):
        return "ico/cur"
    return "unknown"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--corpus")
    a = ap.parse_args()

    if a.corpus:
        files = sorted(glob.glob(os.path.join(a.corpus, "**", "*.PUB"), recursive=True))
        files += [f for f in glob.glob(os.path.join(a.corpus, "**", "*.JSP"), recursive=True)
                  if open(f, "rb").read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"]
        stats = collections.Counter()
        for f in files:
            try:
                r = Reader(f)
            except Exception as e:
                print("FAIL %s: %s" % (f, e))
                stats["failed"] += 1
                continue
            h = r.header
            stats["files"] += 1
            stats["len_ok"] += 1 if h["length_matches"] else 0
            stats["fmt_" + h["format_name"]] += 1
            stats["with_document"] += 1 if getattr(r, "document", None) else 0
            stats["pages"] += len(r.pages)
            stats["shapes"] += len(r.shapes)
            stats["images"] += len(r.images)
            stats["quill_files"] += 1 if r.quill else 0
            if r.document and r.document["width_emu"] == 0:
                stats["zero_width"] += 1
        print(json.dumps(dict(stats), indent=1))
        return

    r = Reader(a.path)
    if a.json:
        print(json.dumps(r.summary(), indent=1))
    else:
        s = r.summary()
        h = s["header"]
        print("%s  %s  format=%s  Contents=%d bytes%s"
              % (s["path"], h["magic_name"], h["format_name"], h["actual_length"],
                 "" if h["length_matches"] else "  !! declared length mismatch"))
        d = s["document"]
        if d:
            print("document: %.2f x %.2f in, coordinate system %d, %d pages"
                  % (d["width_in"], d["height_in"], d["coordinate_system"], len(d["pages"])))
        print("pages=%d shapes=%d images=%d quill_chunks=%s"
              % (s["pages"], s["shapes"], len(s["images"] or []), s["quill_chunks"]))
        for img in (s["images"] or [])[:6]:
            print("  image %#06x payload=%d format=%s" % (img["id"], img.get("payload", 0), img.get("format")))


if __name__ == "__main__":
    main()
