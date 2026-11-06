# Test corpus — sample files and expected results

The documents are copyrighted, so they are **not** distributed here. Each entry
names the Internet Archive item and the path inside it, plus the SHA-256 of the
exact file, so the same bytes can be obtained and verified.

`expect/<sample>.json` is the target output for that file: the facts an
implementation must reproduce. It is plain data — no code is shipped in this
directory, by design (see [../CLEANROOM.md](../CLEANROOM.md)).

| sample | item | path in item | size | sha256 | expected |
|---|---|---|---|---|---|
| `MSPUB_PUB.p95` | https://archive.org/details/microsoft-publisher-for-windows-95 | `x/MSPUB.PUB` | 5632 | `09fca9b767f3a3f8…` | [tests/expect/MSPUB_PUB.p95.json](tests/expect/MSPUB_PUB.p95.json) |
| `MODERN_PUB.p95` | https://archive.org/details/microsoft-publisher-for-windows-95 | `x/PAGEWIZ/MODERN.PUB` | 449024 | `c055e3d2020c42b6…` | [tests/expect/MODERN_PUB.p95.json](tests/expect/MODERN_PUB.p95.json) |
| `AUDIOLBL_PUB.p95` | https://archive.org/details/microsoft-publisher-for-windows-95 | `x/PAGEWIZ/AUDIOLBL.PUB` | 13824 | `dad98c391d63edd7…` | [tests/expect/AUDIOLBL_PUB.p95.json](tests/expect/AUDIOLBL_PUB.p95.json) |
| `CLASS_CD_PUB.p95` | https://archive.org/details/microsoft-publisher-for-windows-95 | `x/PAGEWIZ/CLASS_CD.PUB` | 770048 | `99073ed4564c4e4e…` | [tests/expect/CLASS_CD_PUB.p95.json](tests/expect/CLASS_CD_PUB.p95.json) |
| `AUDIOLBL_PUB.p97` | https://archive.org/details/microsoft-publisher-97 | `x/AUDIOLBL.PUB` | 16896 | `082fec8f832351c7…` | [tests/expect/AUDIOLBL_PUB.p97.json](tests/expect/AUDIOLBL_PUB.p97.json) |
| `CLASSIC_PUB.p97d` | https://archive.org/details/microsoft-publisher-97-cd-deluxe | `x/PageWiz/CLASSIC.PUB` | 397312 | `49aee291c093669e…` | [tests/expect/CLASSIC_PUB.p97d.json](tests/expect/CLASSIC_PUB.p97d.json) |
| `growth7_pub.p97d` | https://archive.org/details/microsoft-publisher-97-cd-deluxe | `x/PageWiz/growth7.pub` | 121344 | `5ccccd4483fe4a58…` | [tests/expect/growth7_pub.p97d.json](tests/expect/growth7_pub.p97d.json) |
| `MSPUB_PUB.p98` | https://archive.org/details/publisher98 | `x/MSPUB.PUB` | 19968 | `0eff0498172805bf…` | [tests/expect/MSPUB_PUB.p98.json](tests/expect/MSPUB_PUB.p98.json) |
| `CHEKLIST_JSP.p98` | https://archive.org/details/publisher98 | `x/CHEKLIST.JSP` | 77312 | `01c21814d4dbf956…` | [tests/expect/CHEKLIST_JSP.p98.json](tests/expect/CHEKLIST_JSP.p98.json) |
| `CLRCHK_JSP.p98` | https://archive.org/details/publisher98 | `x/CLRCHK.JSP` | 91136 | `8bf0d2a88c74d835…` | [tests/expect/CLRCHK_JSP.p98.json](tests/expect/CLRCHK_JSP.p98.json) |

## What each expected file contains

| key | meaning |
|---|---|
| `container.streams` | every CFB stream/storage with its kind and size |
| `header` | the 0x22-byte `Contents` header fields named in chapter 02 |
| `chunkCount`, `chunkTypes` | chunk inventory by type marker |
| `chunks` | `[id, parentId, typeMarker, offset, size]` in file order |
| `document` | page size in EMU and the coordinate-system word |
| `pages` | id, type, size, kind, and the child id list in z-order |
| `shapes` | `[id, typeMarker, rotationRaw, left, top, right, bottom]` |
| `images` | declared length, payload size, payload MD5, first 4 bytes |
| `palettes` | scheme name and the eight colour references |
| `objectRefs` | `[shapeId, objectOrdinal, flag]` |
| `text` | 95/97 text store: bounds, MD5, story records, cell/block census |
| `quill` | 98 Quill stream: record names and count |

Offsets are absolute inside the `Contents` stream unless the key says otherwise.
MD5s cover exactly the extracted bytes (image payload, text pool), so an
implementation can verify byte-exactness without the sample being public.
