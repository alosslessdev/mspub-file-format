# Verified evidence ledger (shared across versions)

Facts below were measured directly and are the baseline every version chapter may
rely on. Anything not listed here must be established in the per-version notes.

**Corpus convention.** "The Publisher 95 corpus" means the 130 documents of `p95/x`:
128 `.PUB` templates plus the two `.JSP` publications (`CHEKLIST.JSP`, `INFOSHET.JSP`).
Where a count is still stated over 128 files it predates the `.JSP` inclusion and excludes
them explicitly (say so when citing).

## 1. Outer container [OBSERVED]

`d0 cf 11 e0 a1 b1 1a e1` — OLE2/CFB v3 (512-byte sectors, 4096-byte mini sectors).
Every one of the 130 Publisher 95 CD documents parses cleanly as CFB.

Root-level streams/storages observed:

| Name | Kind | Notes |
|---|---|---|
| `Contents` | stream | the document proper, see §2 |
| `Objects` | storage | holds `Object N` substorages |
| `\x01CompObj` | stream | OLE class/progid; 78 B × 106, 94 B × 10, 70 B × 12 in the P95 corpus |
| `\x03Internal` | stream | small, Publisher-internal |
| `\x05SummaryInformation` | stream | standard property set; 123/128 P95 files |
| `Object N` | storage | embedded OLE object; contains `Ole`, `CompObj`, `OlePres000/001`, `Ole10Native`, `Contents`, `Internal`. Its `Contents` is the **embedded server's** document (WordArt / packaged binary), never a Publisher `0xACE8` stream: 0 of 285 instances |
| `Quill` | storage | **Publisher 98 only**; `Quill/QuillSub/CONTENTS` |
| `Escher` | storage | **Publisher 98 only** (verify per corpus); `Escher/EscherStm` |

Corpus census: none of the 358 Publisher 95 / 97 documents has a `Quill` or
`Escher` storage; both appear only in the Publisher 98 corpus (2 .PUB + 3 .JSP
publications). The three `.JSP` files on the Publisher 98 CD (`CHEKLIST.JSP`,
`CLRCHK.JSP`, `INFOSHET.JSP`) are complete Publisher publications, not scripts.

## 2. `Contents` header [OBSERVED]

All 130 Publisher 95 documents begin:

```
0x00  u16  0xACE8            magic (0xACE7 is accepted too — legacy form)
0x02  u8   version magic     0x22 = 95/97/98 family, 0x2C = 2000+ family
0x03  u8   0
0x04  u16  format version    300 (0x012C) modern; 200 legacy; 710 legacy-ACE7
0x06  u16  writer stamp      0x0004 ×120, 0x3303 ×8 (GetVersion() of the writing OS)
0x08  u32  stream length     == len(Contents)  [OBSERVED on all files]
0x0C  u16  125               required when format version == 300 (704 when 200)
0x0E  u16  ?                 open
0x10  u16  ?                 open
0x12  u32  text-section off  start of the text store, see chapter 13 §13.14
0x16  u32  directory offset  see §3
0x1A  u32  constant 34       NOT an offset
```

The version gate is in `MSPUB.EXE` VA 0x0045F6B3: it reads 0x22 bytes, rejects a
magic other than 0xACE8/0xACE7, requires `u32@0x08 <= actual stream length`, then
requires (version 300 → `u16@0x0C == 125`) or (version 200 → `u16@0x0C == 704`).
Error 0xE = bad magic/short stream, 0xF = unsupported version.

Measured across all 128 Publisher 95 templates:

| Field | Distinct values | Result |
|---|---|---|
| `u32 @0x04` | 2 | `0x0004012C` (u16 0x012C/0x0004) in 120 files, `0x3303012C` (u16 0x012C/0x3303) in 8 |
| `u16 @0x0C` | 1 | `125` in all files |
| `u16 @0x0E` | 53 | open |
| `u16 @0x10` | 68 | open |
| `u32 @0x12` | 1 | `574` (0x23E) in all Publisher 95 files — the text-section offset (640 in 97, 894 in 98) |
| `u32 @0x16` | per file | directory offset |
| `u32 @0x1A` | 1 | `34` (0x22) in all files |

Correction: `0x12` is **not** a constant — it is the offset of the text section
(chapter 13 §13.14), which equals 574 for Publisher 95 only because every Publisher 95
document shares the same prefix; it is 640 in Publisher 97 and 894 in 98. Verified:
`u32@0x12` points at the `0x002EF0DE` store magic in 493/493 documents, and the section
`[u32@0x12, u32@0x16)` never overlaps a chunk (0/493). `0x1A` = 34 is still unexplained.

Worked example — `p95/x/MSPUB.PUB`, `Contents` length 2780 (0xADC):

```
0000  e8 ac 22 00 2c 01 04 00 dc 0a 00 00 ...
                     ^magic  ^ver        ^0x08 = 0x0ADC = 2780 = stream length
```

## 3. Chunk directory [OBSERVED — CORRECTED]

At `directory offset` (`u32 @ 0x16`): a **4-byte header**, then `count` × 10-byte records, then
**10 zero bytes**, then the first chunk:

```
u16 count
u16 idHighWaterMark        == max(id) in every file of every corpus
count × { u16 id, u16 parentId, u32 chunkOffset, u16 flags }
10 × 0x00
```

`id` is the chunk id (unique within the document, `>= 0x100`). `parentId` is `0x00FE` (Publisher
95 `.PUB`), `0x00FF` (the two `.JSP` publications) for the single root record, which is always the
DOCUMENT chunk; every other parent resolves to a live id. `flags` is the chunk manager's status
word: a closed 13-value domain (`0x1440 | bits`), bits 6/10 and node kind 1 (`0x1000`) always set,
modal value `0x1640`. `flags` is persisted verbatim and is not derived from document structure —
see chapter 03 §3.6.

Chunks appear in ascending `chunkOffset` order, therefore
`chunkSize = next.chunkOffset - chunk.chunkOffset`, and the last chunk extends to
`len(Contents)`. Verified on every record of all 493 documents: no duplicate offsets, no
zero/negative sizes, no gap (`offset[i+1] == offset[i] + size[i]`), and
`directoryOffset + 14 + 10·count == first chunk offset`.

**Superseded:** the earlier model `u16 count` + `count × {u16 seqSkip, u16 id, u16 parent,
u32 offset}` plus a 12-byte trailer. It reads the header's `idHighWaterMark` as record 0's first
field and every record's `flags` as the next record's first field; the "trailer stamp" it reported
is the last record's `flags` word followed by the 10 zero bytes. Do not cite the old model.

Every chunk begins with `u16 typeMarker`.

## 4. Document chunk (type marker 0x0015) [OBSERVED]

Page geometry is in **EMU** (914400 per inch), 32-bit LE.

`p95/x/MSPUB.PUB`, chunk id 0x0100 at 0x041E:

```
+0x00  u16 0x0015       type marker
+0x14  u32 0x007698F0   page width  = 7772400 EMU = 8.5 in
+0x18  u32 0x00997AA0   page height = 10058400 EMU = 11.0 in
```

Whole-corpus confirmation (width/height pairs > count):

| EMU | inches | count |
|---|---|---|
| 7772400 × 10058400 | 8.5 × 11 | 53 |
| 10058400 × 7772400 | 11 × 8.5 | 22 |
| 3886200 × 5029200 | 4.25 × 5.5 | 6 |
| 5029200 × 7315200 | 5.5 × 8 | 5 |
| 15544800 × 15544800 | 17 × 17 | 4 |
| 18288000 × 18288000 | 20 × 20 | 3 |

Every pair resolves to a clean physical paper/banner size in EMU.

## 5. Chunk type markers observed (P95 corpus, 10640 chunks over the 128 `.PUB` files)

The 130-document census (10 732 chunks, 36 markers, including `0x0036`) is chapter 03 §3.9;
that table supersedes this one for counts.

| Marker | Count | libmspub name |
|---|---|---|
| 0x0006 | 1322 | shape (object) |
| 0x0005 | 1110 | rectangle |
| 0x0000 | 1092 | shape |
| 0x000F | 827 | group |
| 0x0014 | 712 | page |
| 0x0004 | 696 | line |
| 0x0003 | 617 | shape |
| 0x0022 | 489 | ? |
| 0x0031 | 384 | logo |
| 0x0032 | 384 | ? |
| 0x0007 | 266 | shape |
| 0x0002 | 248 | image |
| 0x0001 | 218 | shape |
| 0x002C | 137 | ? |
| 0x0021 | 129 | image data |
| 0x0015 | 128 | document (exactly one per file) |
| 0x0029/0x0028/0x0023/0x001E/0x001F/0x0016/0x001A/0x001C/0x002D | 128 each | ? (one per file) |

The singleton set (one of each across all 128 files) is the document-level record
group: per-publication globals, not per-shape data.

## 6. Chunk payload model: FIXED RECORDS, not TLV [OBSERVED — supersedes earlier TLV claims]

**Correction.** The `{u8 id, u8 type, payload}` "TLV block" model (libmspub's
`MSPUBBlockID`/`MSPUBBlockType`) belongs to the Publisher 2000+ base parser. For
95/97/98 chunk payloads are **fixed binary records** whose layout is specific to
the chunk type marker. Measured over 484 documents (p95, p97, p97-deluxe, p98):

| Marker | Modal size | Count | Notes |
|---|---|---|---|
| 0x0022 | 18 | 2134/2134 | every chunk exactly 18 bytes; `u32@+4 == 10 == size-8`; payload `4d 4f` ("MO") + u16 ordinal + 6 zero bytes |
| 0x0021 IMAGE_DATA | varies | 527/527 | `u32@+4 == size-8`; payload starts `01 00 09 00` (WMF) |
| 0x0005 | 62 | 4474 | 70 in 2 chunks |
| 0x0000 | 102 | 4292 | 104 ×670, 106 ×54 |
| 0x0006 | 53 | 4039 | 61 in 2 chunks |
| 0x002D | 26 | 480 | 58 in 2 chunks |
| 0x002E | 26 | 482 | — |
| 0x0039 | 48 | 482 | 56 in 2 chunks |
| 0x0031 | 30 | 1742 | 662 ×6, 446 ×3 |

For every marker other than 0x0021/0x0022 the `u32@+4 == size-8` test fails, so
there is no generic length-prefixed container framing.

The size variants of a marker are not noise: they are the record's optional
trailing extension (most likely a counted array). Each chapter must state, per
marker, the fixed part and the rule that produces the variant sizes.

**Invalidated:** the earlier note in this file claiming "0x0022 = prologue 16 +
TLV list, 489/489 exact" and the 0x0014/0x0023/0x002D/0x002E/0x0039 "TLV start
offset" table. Those walks started on a trailing `00 00` and terminated
immediately. Do not cite them.

## 7. Shape geometry [OBSERVED]

For shape chunk markers (0x00, 0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x16):

```
+0x00  u16  type marker
+0x02  u8   A     per-type constant
+0x03  u8   B     per-type constant
+0x04  u16  rotation, tenths of a degree (counter-clockwise)
+0x06  s32  x0    left   \ 
+0x0A  s32  y0    top     |  EMU, absolute page coordinates
+0x0E  s32  x1    right   |
+0x12  s32  y1    bottom /
```

Verified on `p95/x/PAGEWIZ/MODERN.PUB`: 528 shape chunks, all bounding boxes inside
the 20 in × 20 in page after conversion at 914400 EMU/in, rotation 0.

## 8. Version dispatch [OBSERVED]

The 95/97/98 binaries accept only version magic 0x22 (and the legacy 0xACE7 magic
form); magic 0x2C (2000+) is rejected. The `Quill` text engine and the `Escher`
drawing layer do not exist in the Publisher 95 or 97 CD contents at all — they are
Publisher 98 additions (`SHARED/QUILL/QS98.DLL`, `MSO97.DLL`).
