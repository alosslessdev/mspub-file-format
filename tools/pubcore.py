"""Publisher 95/97/98 document container reader.

Verified facts (see notes/EVIDENCE.md):
 * Outer container is an OLE2/CFB v3 compound file (512-byte sectors).
 * The document proper lives in the root-level stream named "Contents".
 * Publisher 97/98 additionally use "Quill/QuillSub/CONTENTS" for text,
   "Escher/EscherStm" for the drawing layer, and "Object N" substorages
   for embedded OLE objects.
 * Contents stream:
     0x00 u16 magic 0xACE8 (bytes e8 ac)
     0x02 u8  version magic (0x22 = 95/97/98 family, 0x2c = 2000/2002 family)
     0x03 u8  0
     0x04 u32 unknown (varies per file)
     0x08 u32 stream length in bytes (== len(Contents))
     0x0C u16 unknown
     0x0E u16 unknown
     0x10 u16 unknown
     0x12 u32 text-section offset (used by the 97 text path)
     0x16 u32 trailer/directory offset
     0x1A u32 unknown offset (varies)
 * Directory at trailer offset:
     u16 count
     u16 idHighWaterMark   (== max(id) in every measured file)
     count * 10-byte records: u16 id, u16 parentId, u32 chunkOffset, u16 flags
     then 10 zero bytes, then the first chunk
 * Each chunk starts with a u16 type marker; payload length is derived from the
   next chunk offset in the directory (chunks are stored in ascending order).
""" 
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import List, Optional

try:
    import olefile
except ImportError:  # pragma: no cover
    olefile = None


# Chunk type markers observed in the wild.  Names follow libmspub where known;
# "?" entries are observed but not yet explained.
CHUNK_TYPES = {
    0x0000: "SHAPE",
    0x0001: "SHAPE1",
    0x0002: "IMAGE",
    0x0003: "SHAPE3",
    0x0004: "LINE",
    0x0005: "RECT",
    0x0006: "SHAPE_OBJECT",
    0x0007: "SHAPE7",
    0x0008: "SHAPE8",
    0x000F: "GROUP",
    0x0010: "TABLE",
    0x0014: "PAGE",
    0x0015: "DOCUMENT",
    0x0016: "SHAPE16",
    0x0021: "IMAGE_DATA",
    0x0030: "GROUP30",
    0x0031: "LOGO",
    0x0047: "PALETTE",
    0x0044: "DOCUMENT44",
    0x005C: "PALETTE5C",
    0x0063: "CELLS",
    0x006C: "FONT",
    0x0088: "GENERAL_CONTAINER",
}


@dataclass
class Chunk:
    index: int
    id: int
    parent: int
    offset: int
    flags: int
    type_marker: int
    size: int
    data: bytes
    children: List[int] = field(default_factory=list)

    @property
    def seq_skip(self) -> int:
        """Deprecated alias for `flags` (older tooling used this name)."""
        return self.flags

    @property
    def type_name(self) -> str:
        return CHUNK_TYPES.get(self.type_marker, "UNKNOWN_0x%04X" % self.type_marker)


@dataclass
class Document:
    path: str
    streams: List[str]
    header: bytes
    version_magic: int
    trailer_offset: int
    directory_count: int
    contents: bytes
    chunks: List[Chunk]

    def by_id(self, chunk_id: int) -> Optional[Chunk]:
        for c in self.chunks:
            if c.id == chunk_id:
                return c
        return None

    def of_type(self, type_marker: int) -> List[Chunk]:
        return [c for c in self.chunks if c.type_marker == type_marker]

    def root_children(self) -> List[Chunk]:
        ids = {c.id for c in self.chunks}
        return [c for c in self.chunks if c.parent not in ids]


def list_streams(path: str) -> List[str]:
    o = olefile.OleFileIO(path)
    try:
        out = []
        for e in o.direntries:
            if e is None:
                continue
            name = e.name
            if isinstance(name, bytes):
                name = name.decode("latin-1")
            if isinstance(name, list):
                name = "/".join(n.decode("latin-1") if isinstance(n, bytes) else n for n in name)
            kind = {1: "storage", 2: "stream", 5: "root"}.get(e.entry_type, str(e.entry_type))
            size = e.size if e.entry_type == 2 else 0
            out.append("%s\t%s\t%d" % (kind, name, size))
        return sorted(out)
    finally:
        o.close()


def read_stream(path: str, name: str) -> Optional[bytes]:
    o = olefile.OleFileIO(path)
    try:
        if not o.exists(name):
            return None
        return o.openstream(name).read()
    finally:
        o.close()


def parse_contents(path: str, contents: Optional[bytes] = None) -> Document:
    if contents is None:
        contents = read_stream(path, "Contents")
    if contents is None:
        raise ValueError("no Contents stream in %s" % path)
    d = contents
    if len(d) < 0x20:
        raise ValueError("Contents stream too short")
    magic = struct.unpack_from("<H", d, 0)[0]
    if magic != 0xACE8:
        raise ValueError("bad Contents magic %04x" % magic)
    version_magic = d[2]
    trailer_offset = struct.unpack_from("<I", d, 0x16)[0]
    count = struct.unpack_from("<H", d, trailer_offset)[0]
    id_high_water = struct.unpack_from("<H", d, trailer_offset + 2)[0]
    recs = []
    p = trailer_offset + 4
    for _ in range(count):
        if p + 10 > len(d):
            break
        cid, parent, off, flags = struct.unpack_from("<HHIH", d, p)
        recs.append((flags, cid, parent, off))
        p += 10

    # Order by file offset to derive chunk extents.
    ordered = sorted(recs, key=lambda r: r[3])
    extents = {}
    for i, r in enumerate(ordered):
        start = r[3]
        end = ordered[i + 1][3] if i + 1 < len(ordered) else len(d)
        extents[start] = max(0, end - start)

    chunks = []
    for i, (seq_skip, cid, parent, off) in enumerate(recs):
        size = extents.get(off, 0)
        data = d[off:off + size]
        tm = struct.unpack_from("<H", d, off)[0] if off + 2 <= len(d) else -1
        chunks.append(Chunk(i, cid, parent, off, seq_skip, tm, size, data))

    ids = {c.id for c in chunks}
    for c in chunks:
        if c.parent in ids:
            # children are resolved lazily by the caller via by_id
            pass
    return Document(path, list_streams(path), d[:0x22], version_magic,
                    trailer_offset, count, d, chunks)


def walk(path: str):
    return parse_contents(path)


if __name__ == "__main__":
    import sys, collections
    for arg in sys.argv[1:]:
        doc = parse_contents(arg)
        c = collections.Counter(ch.type_name for ch in doc.chunks)
        print("%s  ver=%02x chunks=%d trailer=%#x" % (arg, doc.version_magic, len(doc.chunks), doc.trailer_offset))
        for k, v in c.most_common():
            print("   %-20s %d" % (k, v))
