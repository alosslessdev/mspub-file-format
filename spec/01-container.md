# 01 — Outer container (OLE2 / CFB)

A Publisher 95 document is a **Compound File Binary (CFB) v3** file ([MS-CFB]) whose payload
lives in one stream named `Contents`. Publisher does not use a proprietary outer envelope: the
container is byte-for-byte a Microsoft structured-storage file, and any CFB reader can open it.

All 128 files of the Publisher 95 corpus (`p95/x/**/*.PUB`) parse as CFB with zero errors.

## 1.1 CFB header

| Offset | Width | Field | Value observed in the corpus |
|---|---|---|---|
| 0x00 | 16 | Header signature | `d0 cf 11 e0 a1 b1 1a e1` [OBSERVED] |
| 0x18 | u16 | Minor version | `62` (0x3E) in 128/128 files [OBSERVED] |
| 0x1A | u16 | Major version | `3` — CFB v3, 512-byte sectors [OBSERVED] |
| 0x1C | u16 | Byte order | `0xFFFE` [OBSERVED] |
| 0x1E | u16 | Sector shift | `9` → 512-byte sectors [OBSERVED] |
| 0x20 | u16 | Mini sector shift | `6` → 64-byte mini sectors [OBSERVED] |
| 0x2C | u32 | Number of FAT sectors | varies with file size (1…12 observed) [OBSERVED] |
| 0x38 | u32 | Mini-stream cutoff | `4096` (0x1000) in all files [OBSERVED] |
| 0x3C | u32 | First mini-FAT sector | 1…12 observed, never `ENDOFCHAIN` [OBSERVED] |
| 0x40 | u32 | Number of mini-FAT sectors | 1…12 observed [OBSERVED] |
| 0x44 | u32 | First DIFAT sector | `0xFFFFFFFE` (ENDOFCHAIN) [OBSERVED] |
| 0x48 | u32 | Number of DIFAT sectors | `0` in all files [OBSERVED] |
| 0x50 | u32 | First directory sector | `1` in all files [OBSERVED] |
| 0x60 | 16 | CLSID | all zero in all files [OBSERVED] |

Corpus-wide header census (22 distinct combinations, all sharing the same
minor/major/sector/mini/cutoff values; they differ only in FAT and mini-FAT sector counts):

```
(62, 3, 512, 64, 4096, nfat=1, nminifat=1)  89 files
(62, 3, 512, 64, 4096, nfat=1, nminifat=2)  10 files
(62, 3, 512, 64, 4096, nfat=2, nminifat=1)   6
(62, 3, 512, 64, 4096, nfat=2, nminifat=3)   3
(62, 3, 512, 64, 4096, nfat=1, nminifat=3)   1
… 17 further combinations, each 1–3 files
```

[OBSERVED] No Publisher 95 file uses CFB v4 (4096-byte sectors), DIFAT sectors, or a non-zero
header CLSID.

## 1.2 Stream set

Root-level children of `Root Entry`, present in every file unless noted:

| Name | Kind | Contents |
|---|---|---|
| `Contents` | stream | the document proper — see chapter 02 |
| `\x01CompObj` | stream | OLE class descriptor, §1.4 |
| `\x03Internal` | stream | 12 or 16 bytes, §1.5 |
| `Objects` | storage | container for embedded OLE objects, §1.6 |
| `\x05SummaryInformation` | stream | standard property set; present in **127/128** files, absent only in `p95/x/MSPUB.PUB`; 4 of the present ones are zero-length (`*_CD.PUB`) — see chapter 16 |

[OBSERVED] No Publisher 95 file contains a `Quill` storage (the Publisher 97/98 text engine) or
an `Escher` storage (the Publisher 98 drawing layer). Those storages first appear in the later
releases; see the version-difference chapter.

### 1.2.1 Mini-stream behaviour

Publisher follows the MS-CFB rule exactly: a stream shorter than the 4096-byte cutoff is stored
in the mini-stream, otherwise in normal FAT sectors. [OBSERVED]

* `p95/x/MSPUB.PUB` — `Contents` is 2780 bytes, stored in the mini-stream
  (root entry `isectStart = 3`, root mini-stream size 3008).
* 126 files — `Contents` is ≥ 4096 bytes and lives in FAT sectors;
  `p95/x/PAGEWIZ/AUDIOLBL.PUB` has `Contents` = 5646 bytes at FAT sector 9.

There is **no** Publisher-specific deviation from [MS-CFB] in sector size, mini-sector size,
cutoff, FAT structure or directory-entry format. [OBSERVED]

## 1.3 Directory

The CFB directory is a red-black tree of 128-byte entries. Publisher writes colour flags and
sibling links exactly as [MS-CFB] specifies; the tree rooted at the `Root Entry` child pointer
contains `Contents`, `Objects`, `\x01CompObj`, `\x03Internal` (and `\x05SummaryInformation`).
Entries inside `Objects` are described in §1.6.

Example — `p95/x/MSPUB.PUB` (5 entries):

| sid | type | name | size | isectStart | left | right | child |
|---|---|---|---|---|---|---|---|
| 0 | 5 root | `Root Entry` | 3008 | 3 | – | – | 3 |
| 1 | 1 storage | `Objects` | 0 | 0 | – | 4 | – |
| 2 | 2 stream | `\x03Internal` | 12 | 0 | – | – | – |
| 3 | 2 stream | `Contents` | 2780 | 1 | 1 | 2 | – |
| 4 | 2 stream | `\x01CompObj` | 94 | 45 | – | – | – |

[OBSERVED] (`Objects` is a sibling of `Contents` via its right pointer; `\x01CompObj` hangs off
`Objects.right`.)

## 1.4 `\x01CompObj`

Publisher 95 writes a fixed-shape OLE class descriptor. Lengths seen: 94 bytes (128 root
streams), 78 bytes and 102 bytes (inside `Objects`). Layout:

| Offset | Width | Value |
|---|---|---|
| 0x00 | u32 | `0xFFFE0001` (reserved) |
| 0x04 | u32 | `0x00000A03` (Win32 CompObj version) |
| 0x08 | u32 | `0xFFFFFFFF` (reserved) |
| 0x0C | 16 | CLSID `{00021200-0000-0000-C000-000000000046}` — Microsoft Publisher 2.0 |
| 0x1C | u32 | 0x18 = 24 |
| 0x20 | 24 | `"Microsoft Publisher 2.0\0"` (AnsiUserType) |
| 0x38 | u32 | 0x0E = 14 |
| 0x3C | 14 | `"MSPublisher.2\0"` (AnsiClipboardFormat / ProgID) |
| 0x4A | u32 | 0 |
| 0x4E | u32 | `0x71B239F4` (Unicode marker) |
| 0x52 | 12 | zero |

[OBSERVED] corpus census of the root `\x01CompObj`: **78 bytes in 106 files, 94 bytes in 10,
70 bytes in 12** — the stream is not fixed-length; the 94-byte form is the largest variant and
carries the same fields with different padding. The CLSID is
`{00021200-0000-0000-C000-000000000046}` in 127 files and
`{00021201-0000-0000-C000-000000000046}` in 1 file (a later revision of the same class), so the
low dword is `0x00021200`/`0x00021201`, not a fixed constant. The `Objects/Object N`
substorages reuse the same descriptor shape (§1.6).

## 1.5 `\x03Internal`

**The root stream is exactly 12 bytes in 493/493 corpus files** (P95 130, P97 108, P97 Deluxe
250, P98 5). The 16-byte form exists only inside `Object N` substorages (§1.6). The layout is a
6-byte fixed prefix, a 32-bit serial and a 16-bit payload length:

| Offset | Width | Meaning |
|---|---|---|
| `0x00` | u32 | constant `0x00010000` |
| `0x04` | u16 | `0` (reserved) |
| `0x06` | u32 | **object serial** — the document's `Object N` high-water mark |
| `0x0A` | u16 | byte length of the optional payload that follows the 12-byte header; `0` in 493/493 |

Example: `0000 0100 0000 0100 0000 0000` = constant, zero word, serial `1`, no payload; the
`… 0500 0000 0000` form is serial `5`.

[OBSERVED, `PUBOLE32.DLL` — the container layer `MSPUB.EXE` drives through
`_MatLReadFromFh`/`_MatLWriteToFh`]

* **Writer** VA `0x600174C0`, third argument non-zero (reached as `(fh, document, 1)` from
  `_MatSaveDocument@12`, VA `0x6001CD60`). It seeks to 0 and writes 12 bytes assembled from the
  dword at `0x6001F000` (`0x00010000`), a zero word, the dword at `document+0x2E`, and the low
  word of `document+0x4A`.
* **Reader** the same VA with the third argument zero (from `_MatOpenDocument@16`, VA
  `0x60011A90`, and from `_MatSaveDocument`). It reads exactly 12 bytes, rejects a stream whose
  first word is not `0x00010000`, restores `document+0x2E` from bytes `0x06…0x09`, and — only
  when the word at `0x0A` is non-zero — reads that many additional bytes into `document+0xA8`,
  capped by the capacity word `document+0x4A`. Both lengths are 0 throughout the corpus, so no
  root stream has a payload and nothing after `0x0C` is ever read.

`document+0x2E` is the **next `Object N` number**, not a revision counter and not a live object
count:

* `_MatLoadObject@20` (VA `0x60016750`) hands the word to the storage creator as the first
  `"Object %d"` number to try, then increments it;
* `_MatCreateObject@32` (VA `0x60012A80`) and `_MatCloneObject@12` (VA `0x60012F90`) increment it
  after a new object storage is allocated, and `_MatSaveObject@20` (VA `0x600165A0`) increments it
  again when an object is published into the container;
* nothing decrements it — `_MatDeleteObject@4` (VA `0x60013250`) and `_MatReleaseObject@4` only
  free the storage.

It is thus a monotonic allocator that survives save/open through this field. The corpus agrees:
over the 130 P95 files the value is never below the number of live `Object N` storages
(**130/130**; equal in only 17) and reaches 241 in a file holding 23 objects, which is what a
never-decremented object serial produces and what an object *count* cannot.

## 1.6 `Objects` storage and embedded objects

`Objects` is present in all 130 files. It holds zero or more **`Object N`** substorages
(N = 0, 1, 2 …). Each `Object N` is an embedded OLE object and repeats the root layout plus the
OLE presentation streams:

| Stream | Meaning |
|---|---|
| `Contents` | **the embedded application's own document, not a Publisher document** — see below |
| `\x03Internal` | same 6-byte prefix as §1.5, but 12 or 16 bytes (591 × 12, 648 × 16 across the 493 files); every 16-byte instance is the 12-byte record plus four zero bytes |
| `\x01CompObj` | same 94-byte-style descriptor (102 bytes here) |
| `\x01Ole` | 20 bytes — OLE object header |
| `\x02OlePres000`, `\x02OlePres001` | presentation data (metafile/DIB) for the object |
| `\x01Ole10Native` | present when the object is a packaged (non-OLE) file |

[OBSERVED] 500 `\x01Ole` streams, 500 `\x02OlePres000`, 121 `\x02OlePres001`, 215
`\x01Ole10Native` across the corpus, all inside `Object N` substorages. The nesting is one level
deep in every file (no `Objects` inside an `Object N`).

**`Object N/Contents` is not a Publisher mini-document.** All **285** such streams in the P95
corpus were checked and **none** starts with the `0xACE8` magic:

| leading bytes | count | interpretation |
|---|---|---|
| `57 6f 72 64 41 72 74 20` (`"WordArt "`) | 284 | Microsoft WordArt 2.0 document (the object's own native format) |
| `78 56 34 12 4c 45` (`"xV4\x12LE"`) | 1 | packaged binary (`CLASS_CD.PUB`, `Object 93`, 148 832 bytes) — an `\x01Ole10Native` payload |

So the name `Contents` here is a *convention* that the embedded server also uses; a Publisher
reader must treat the subtree as opaque and hand it to the OLE server. An earlier revision of
this chapter claimed these were parseable 0xACE8 documents; that was an untested assumption and
is refuted by the measurement above. `\x03Internal` and `\x01CompObj` inside `Object N` follow
the same conventions as the root streams.

The link from a drawing shape to its `Object N` substorage is established by the shape chunk,
not by the container — see the shape chapters.

## 1.7 File size and sector arithmetic

Corpus file sizes range from 5 632 bytes (`MSPUB.PUB`) to 770 048 bytes. Every file size is a
multiple of 512 and satisfies `size = 512 * (1 + nb_sectors)`. [OBSERVED]

## 1.8 Summary of Publisher quirks vs [MS-CFB]

| Aspect | Publisher 95 | Deviation |
|---|---|---|
| Sector size | 512 | none |
| Mini sector / cutoff | 64 / 4096 | none |
| DIFAT | never used | none (legal for these sizes) |
| Directory entry count | 4–6 at root, grows with embedded objects | none |
| Header CLSID | zero | none |
| Stream names | control-character prefixes `\x01`…`\x05` | standard OLE convention |
| Nested documents | `Objects/Object N/Contents` holds the embedded server's document (WordArt / packaged file), never a Publisher `0xACE8` stream | Publisher-specific *use*, not a container deviation |

[OBSERVED] Conclusion: the Publisher 95 container is plain [MS-CFB] v3. All Publisher-specific
structure is inside the `Contents` stream (chapter 02 onward) and inside the `Object N`
substorages.
