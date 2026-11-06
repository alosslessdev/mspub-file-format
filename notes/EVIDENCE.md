# Verified evidence ledger (shared across versions)

Facts below were measured directly and are the baseline every version chapter may
rely on. Anything not listed here must be established in the per-version notes.

## 1. Outer container [OBSERVED]

`d0 cf 11 e0 a1 b1 1a e1` — OLE2/CFB v3 (512-byte sectors, 4096-byte mini sectors).
Every shipped `.PUB` in the Publisher 95 CD (128 files) parses cleanly as CFB.

Root-level streams/storages observed:

| Name | Kind | Notes |
|---|---|---|
| `Contents` | stream | the document proper, see §2 |
| `Objects` | storage | holds `Object N` substorages |
| `\x01CompObj` | stream | OLE class/progid of the document |
| `\x03Internal` | stream | small, Publisher-internal |
| `\x05SummaryInformation` | stream | standard property set |
| `Object N` | storage | embedded OLE object; contains `Ole`, `CompObj`, `OlePres000/001`, `Ole10Native`, `Contents`, `Internal` |
| `Quill` | storage | **only Publisher 97/98**; `Quill/QuillSub/CONTENTS` |
| `Escher` | storage | **only Publisher 98** (verify); `Escher/EscherStm` |

Publisher 95 corpus census: 0 files with a `Quill` storage, 0 with `Escher`.

## 2. `Contents` header [OBSERVED]

All 128 Publisher 95 templates begin:

```
0x00  u16  0xACE8            magic (bytes e8 ac)
0x02  u8   version magic     0x22 = 95/97/98 family, 0x2C = 2000+ family
0x03  u8   0
0x04  u32  ?                 per-file value
0x08  u32  stream length     == len(Contents)  [OBSERVED on all files]
0x0C  u16  ?                 open
0x0E  u16  ?                 open
0x10  u16  ?                 open
0x12  u32  constant 574      NOT an offset (see below)
0x16  u32  directory offset  see §3
0x1A  u32  constant 34       NOT an offset
```

Measured across all 128 Publisher 95 templates:

| Field | Distinct values | Result |
|---|---|---|
| `u32 @0x04` | 2 | `0x0004012C` in 120 files, `0x33025F2C` in 8 |
| `u16 @0x0C` | 1 | `125` in all files |
| `u16 @0x0E` | 53 | open |
| `u16 @0x10` | 68 | open |
| `u32 @0x12` | 1 | `574` (0x23E) in all files |
| `u32 @0x16` | per file | directory offset |
| `u32 @0x1A` | 1 | `34` (0x22) in all files |

Consequence: `0x12` and `0x1A` are **fixed constants** of this format family, not
offsets into the stream (neither equals the first chunk offset on any file). The
region `0x22 … 0x23D` is a fixed-size area between the header and the first
variable data. `0x0E`/`0x10` are probably one 32-bit value split across two `u16`s.

Worked example — `p95/x/MSPUB.PUB`, `Contents` length 2780 (0xADC):

```
0000  e8 ac 22 00 2c 01 04 00 dc 0a 00 00 ...
                     ^magic  ^ver        ^0x08 = 0x0ADC = 2780 = stream length
```

## 3. Chunk directory [OBSERVED]

At `directory offset`: `u16 count`, then `count` × 10 bytes:

```
u16 seqSkip     unexplained; varies (0x16C0, 0x1640, 0x0123, ...)
u16 id          chunk id, unique within the document
u16 parentId    id of the parent chunk; 0x00FE / 0x0001 for roots
u32 chunkOffset byte offset of the chunk inside Contents
```

Chunks appear in ascending `chunkOffset` order, therefore
`chunkSize = next.chunkOffset - chunk.chunkOffset`, and the last chunk extends to
`len(Contents)`. Verified on 10640 chunks / 128 files: no duplicate offsets, no
zero/negative sizes.

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

## 5. Chunk type markers observed (P95 corpus, 10640 chunks)

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

## 6. TLV sub-records [OBSERVED framing; length table open]

Inside chunks, typed sub-records `{u8 id, u8 type, payload}`. Payload width is
implied by `type`; variable-width types carry a `u32` length.

Two corrections established by measurement (tools/tlvfind.py):

* A zero doublet `00 00` acts as a **list terminator**, not a zero-length block.
* Shapes and images are **not** pure TLV lists: they carry a binary prologue
  first (libmspub reads coordinates at +6, fill type at +0x2A, etc.).

Chunk types whose payload is a fixed prologue followed by an exactly terminating
TLV list (share of corpus chunks that terminate exactly at payload end):

| Marker | Prologue | Exact | n |
|---|---|---|---|
| 0x0014 PAGE | 0 | — | 712 (terminates, trailing bytes present) |
| 0x0022 | 16 | 489/489 | 489 |
| 0x0023 | 28 | 99/128 | 128 |
| 0x002D | 24 | 127/128 | 128 |
| 0x002E | 24 | 128/128 | 128 |
| 0x0039 | 46 | 128/128 | 128 |
| 0x0031 LOGO | — | no exact termination | 384 |
| 0x0015 DOCUMENT | — | no exact termination | 128 |

Shapes (0x00/0x01/0x02/0x03/0x04/0x05/0x06/0x07/0x08/0x16), groups (0x0F),
images (0x02/0x21) and the document chunk do not terminate as pure TLV lists, so
their payload is prologue+TLV with a prologue whose length varies by type.

The authoritative length table must come from the binary (see the
`getBlockDataLength` switch in the decompilation).

## 7. Version dispatch [OBSERVED]

`MSPUB.EXE` (95) reads the `Contents` magic and version byte; the string
"Publisher cannot load files from a different version" is the load gate. Version
magic `0x2C` is the 2000+ family and is rejected by the 95/97/98 binaries.
