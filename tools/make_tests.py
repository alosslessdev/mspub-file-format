"""Generate the clean-room test package: sample-file manifest + expected outputs.

Writes, into `tests/`:
  corpus.md            sample-file inventory (source media, path, size, sha256)
  expect/<name>.json   the observable facts an implementation must produce

Deliberately no code and no sample bytes are shipped: the documents are
copyrighted, so each entry names the Internet Archive item and path plus the
sha256 of the exact file, and the expected output is data an implementation can
diff against.

Usage: python tools/make_tests.py
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

SOURCES = {
    "publisher95": ("publisher98", "Publisher 95 CD", "Microsoft Publisher 98.iso"),
}
ITEMS = {
    "p95": "https://archive.org/details/microsoft-publisher-for-windows-95",
    "p97": "https://archive.org/details/microsoft-publisher-97",
    "p97d": "https://archive.org/details/microsoft-publisher-97-cd-deluxe",
    "p98": "https://archive.org/details/publisher98",
}

SAMPLES = [
    ("p95", "p95/x/MSPUB.PUB"),
    ("p95", "p95/x/PAGEWIZ/MODERN.PUB"),
    ("p95", "p95/x/PAGEWIZ/AUDIOLBL.PUB"),
    ("p95", "p95/x/PAGEWIZ/CLASS_CD.PUB"),
    ("p97", "p97/x/AUDIOLBL.PUB"),
    ("p97d", "p97deluxe/x/PageWiz/CLASSIC.PUB"),
    ("p97d", "p97deluxe/x/PageWiz/growth7.pub"),
    ("p98", "p98/x/MSPUB.PUB"),
    ("p98", "p98/x/CHEKLIST.JSP"),
    ("p98", "p98/x/CLRCHK.JSP"),
]


def md5(b: bytes) -> str:
    return hashlib.md5(b).hexdigest()


def expect(path: str) -> dict:
    raw = open(path, "rb").read()
    doc = pubcore.parse_contents(path)
    d = doc.contents

    out = {
        "file": {
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "container": {"streams": doc.streams},
        "header": {
            "magic": struct.unpack_from("<H", d, 0)[0],
            "versionByte": d[2],
            "formatVersion": struct.unpack_from("<H", d, 4)[0],
            "declaredLength": struct.unpack_from("<I", d, 8)[0],
            "headerTag": struct.unpack_from("<H", d, 0x0C)[0],
            "textSectionOffset": struct.unpack_from("<I", d, 0x12)[0],
            "directoryOffset": struct.unpack_from("<I", d, 0x16)[0],
            "idHighWaterMark": struct.unpack_from("<H", d, struct.unpack_from("<I", d, 0x16)[0] + 2)[0],
        },
        "chunkCount": len(doc.chunks),
        "chunkTypes": {},
        "chunks": [],
    }
    counts = {}
    for c in doc.chunks:
        counts["0x%04X" % c.type_marker] = counts.get("0x%04X" % c.type_marker, 0) + 1
    out["chunkTypes"] = dict(sorted(counts.items()))

    # Full chunk list is large but it is the most useful target: id, parent,
    # type, offset, size. Sorted by offset (the file order).
    for c in doc.chunks:
        out["chunks"].append([c.id, c.parent, c.type_marker, c.offset, c.size])

    dm = next((c for c in doc.chunks if c.type_marker == 0x15), None)
    if dm:
        out["document"] = {
            "id": dm.id,
            "coordinateSystem": struct.unpack_from("<H", dm.data, 0x12)[0],
            "widthEmu": struct.unpack_from("<I", dm.data, 0x14)[0],
            "heightEmu": struct.unpack_from("<I", dm.data, 0x18)[0],
        }

    pages = []
    for c in doc.of_type(0x14) + doc.of_type(0x41):
        p98 = c.data[2] == 0x1E
        cnt_off, kind_off, arr = (0x1E, 0x1C, 0x28) if p98 else (0x1A, 0x18, 0x24)
        n = struct.unpack_from("<H", c.data, cnt_off)[0]
        pages.append({
            "id": c.id, "type": c.type_marker, "size": c.size,
            "kind": struct.unpack_from("<H", c.data, kind_off)[0],
            "children": list(struct.unpack_from("<%dH" % n, c.data, arr)) if n else [],
        })
    out["pages"] = pages

    shapes = []
    for c in doc.chunks:
        if c.type_marker > 0x0008:
            continue
        x0, y0, x1, y1 = struct.unpack_from("<iiii", c.data, 6)
        shapes.append([c.id, c.type_marker, struct.unpack_from("<H", c.data, 4)[0], x0, y0, x1, y1])
    out["shapes"] = shapes

    images = []
    for c in doc.of_type(0x21):
        n = struct.unpack_from("<I", c.data, 4)[0]
        payload = c.data[8:8 + n]
        images.append({
            "id": c.id, "parent": c.parent, "declaredLength": n,
            "payloadSize": len(payload), "md5": md5(payload),
            "first4": payload[:4].hex(),
        })
    out["images"] = images

    palettes = []
    for c in doc.of_type(0x47):
        palettes.append({
            "id": c.id,
            "scheme": c.data[0x0E:0x90].decode("utf-16-le", "replace").split("\0")[0],
            "refs": ["%08X" % struct.unpack_from("<I", c.data, 0xA0 + 4 * i)[0] for i in range(8)],
        })
    out["palettes"] = palettes

    objs = []
    for c in doc.of_type(0x22):
        objs.append([c.parent, struct.unpack_from("<H", c.data, 0x0A)[0], c.data[0x0F]])
    out["objectRefs"] = objs

    # Text store (95/97) or Quill (98)
    store = None
    for off in range(0x40, min(len(d), 0x400), 2):
        if struct.unpack_from("<H", d, off)[0] == 0xF0DE:
            store = off
            break
    if store is not None:
        base = struct.unpack_from("<I", d, store + 0x0E)[0]
        end = struct.unpack_from("<I", d, store + 0x12)[0]
        text = d[base:end]
        entry = {"storeOffset": store, "textBase": base, "textEnd": end,
                 "textSize": len(text), "textMd5": md5(text)}
        ptrs = [struct.unpack_from("<I", d, store + 0x1E + 4 * i)[0] for i in range(4)]
        stories = []
        for ptr in [p for p in ptrs if p]:
            n = struct.unpack_from("<H", d, ptr + 4)[0]
            stories.append({
                "offset": ptr,
                "count": n,
                "size": 0x1A + 6 * n,
                "bounds": list(struct.unpack_from("<%dI" % n, d, ptr + 0x1A)) if n else [],
                "ids": list(struct.unpack_from("<%dH" % n, d, ptr + 0x1A + 4 * n)) if n else [],
            })
        entry["stories"] = stories
        blocks = 0
        cells = 0
        for blk in text.split(b"\x0c"):
            cs = blk.split(b"\x0f")
            if len(cs) >= 4:
                blocks += 1
                cells += len(cs)
        entry["cellBlocks"] = blocks
        entry["cells"] = cells
        out["text"] = entry

    q = None
    try:
        blob = pubcore.read_stream(path, "Quill/QuillSub/CONTENTS")
    except Exception:
        blob = None
    if blob:
        names = []
        off = 0x18
        seen = set()
        while off != 0xFFFFFFFF and off not in seen and off + 8 <= len(blob):
            seen.add(off)
            n = struct.unpack_from("<H", blob, off + 2)[0]
            nxt = struct.unpack_from("<I", blob, off + 4)[0]
            p = off + 8
            for _ in range(n):
                names.append(blob[p + 2:p + 6].decode("latin-1").rstrip())
                p += 24
            off = nxt
        q = {"size": len(blob), "records": len(names), "chunks": names}
        for i in range(0, len(names), 1):
            pass
        out["quill"] = q

    return out


def main():
    os.makedirs("tests/expect", exist_ok=True)
    manifest = []
    for label, path in SAMPLES:
        if not os.path.exists(path):
            print("missing sample:", path)
            continue
        data = expect(path)
        name = os.path.basename(path).replace(".", "_") + "." + label
        target = "tests/expect/%s.json" % name
        with open(target, "w", encoding="utf-8") as w:
            json.dump(data, w, indent=1)
        manifest.append({
            "sample": name,
            "source": ITEMS[label],
            "path": path.split("/", 1)[1] if "/" in path else path,
            "size": data["file"]["size"],
            "sha256": data["file"]["sha256"],
            "expect": target,
        })
        print("wrote", target)

    lines = [
        "# Test corpus — sample files and expected results",
        "",
        "The documents are copyrighted, so they are **not** distributed here. Each entry",
        "names the Internet Archive item and the path inside it, plus the SHA-256 of the",
        "exact file, so the same bytes can be obtained and verified.",
        "",
        "`expect/<sample>.json` is the target output for that file: the facts an",
        "implementation must reproduce. It is plain data — no code is shipped in this",
        "directory, by design (see [../CLEANROOM.md](../CLEANROOM.md)).",
        "",
        "| sample | item | path in item | size | sha256 | expected |",
        "|---|---|---|---|---|---|",
    ]
    for m in manifest:
        lines.append("| `%s` | %s | `%s` | %d | `%s` | [%s](%s) |" % (
            m["sample"], m["source"], m["path"], m["size"],
            m["sha256"][:16] + "…", m["expect"], m["expect"]))
    lines += [
        "",
        "## What each expected file contains",
        "",
        "| key | meaning |",
        "|---|---|",
        "| `container.streams` | every CFB stream/storage with its kind and size |",
        "| `header` | the 0x22-byte `Contents` header fields named in chapter 02 |",
        "| `chunkCount`, `chunkTypes` | chunk inventory by type marker |",
        "| `chunks` | `[id, parentId, typeMarker, offset, size]` in file order |",
        "| `document` | page size in EMU and the coordinate-system word |",
        "| `pages` | id, type, size, kind, and the child id list in z-order |",
        "| `shapes` | `[id, typeMarker, rotationRaw, left, top, right, bottom]` |",
        "| `images` | declared length, payload size, payload MD5, first 4 bytes |",
        "| `palettes` | scheme name and the eight colour references |",
        "| `objectRefs` | `[shapeId, objectOrdinal, flag]` |",
        "| `text` | 95/97 text store: bounds, MD5, story records, cell/block census |",
        "| `quill` | 98 Quill stream: record names and count |",
        "",
        "Offsets are absolute inside the `Contents` stream unless the key says otherwise.",
        "MD5s cover exactly the extracted bytes (image payload, text pool), so an",
        "implementation can verify byte-exactness without the sample being public.",
        "",
    ]
    with open("tests/corpus.md", "w", encoding="utf-8") as w:
        w.write("\n".join(lines))
    print("wrote tests/corpus.md with", len(manifest), "samples")


if __name__ == "__main__":
    main()
