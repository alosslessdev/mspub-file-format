# 03 — Chunk directory

The `Contents` stream stores a directory of **10-byte records** that maps every chunk id to its
byte offset, its parent and a descriptor word. The directory sits at `u32 @0x16` of the header
(chapter 02) and is followed by the chunks themselves.

## 3.1 Structure

```
directory:
  u16  count                            number of records
  count × 10 bytes:
     +0 u16  descriptor   (see §3.4; pubcore calls it seqSkip)
     +2 u16  id           chunk id, unique within the document
     +4 u16  parentId     id of the parent chunk, or 0x00FE for the root record
     +6 u32  chunkOffset  byte offset of the chunk inside Contents
  12 bytes  trailer      (see §3.5)
  <chunks>
```

**Binary evidence.** `MSPUB.EXE` VA `0x0045E06A` (the directory loader called from the open
function VA `0x0045F6B3`) reads a u16 count, then one more u16, then loops `count` times reading
**10 bytes** into five consecutive u16 temporaries. That 10-byte stride is the primary evidence
for the record size; the field assignment below is proven by cross-reference (§3.2, §3.3).

[OBSERVED] 128/128 files: the directory lies *before* all chunks, and `directory_offset + 2 +
10*count + 12 == first chunk offset`.

## 3.2 `id` and `parentId` — proven by cross-reference

Independent proof that the *second* u16 is the id and the *third* is the parent:

* The DOCUMENT chunk stores ids of other chunks at `+0x04`, `+0x06`, `+0x08`, `+0x46…+0x60`,
  `+0x68` and `+0x74…`. Every one of those values matches the **second** u16 of exactly one
  directory record, and the referenced chunk always has the expected type (128/128 files;
  chapter 04 §4.3).
* The PAGE chunk stores child ids at `+0x24`; those match the second u16 of the child records,
  and the child records' **third** u16 equals the page's own second u16 (712/712; chapter 05
  §5.6).

Corpus invariants (all 128 files):

| Property | Result |
|---|---|
| ids unique within a file | 128/128 (0 duplicates) |
| every `parentId` is either `0x00FE` or a valid id in the same file | 128/128 (0 dangling) |
| only record 0 has `parentId == 0x00FE`, and it is the DOCUMENT chunk | 128/128 |
| `chunkOffset` strictly ascending in directory order | 128/128 |

[OBSERVED] Because offsets are strictly ascending, `chunkSize = next.chunkOffset −
chunk.chunkOffset`, and the last chunk extends to `len(Contents)`.

## 3.3 Ordering guarantees

* Directory order == ascending chunk-offset order, so directory order is *write* order.
* The DOCUMENT record is always record 0 even though its chunk is not at the lowest offset
  (it is at the lowest offset among *root-level* chunks in some files only). Where the
  DOCUMENT chunk sits relative to other chunks varies by file.
* No gap exists between consecutive chunks: `offset[i+1] == offset[i] + size[i]` for every
  adjacent pair in every file. [OBSERVED]
* Page order (DOCUMENT `+0x08` plus the `+0x74` array) is a *separate* enumeration, but it too
  equals chunk-offset order in 128/128 files (chapter 04 §4.4).

## 3.4 The `descriptor` word at record +0

Record 0's descriptor equals `max(id)` of the file on 128/128 files. For every other record the
descriptor is drawn from a small, highly structured set:

```
descriptor = 0x1440 | (b0 << 3) | (b4 << 7) | (b5 << 8) | (b6 << 9)
```

i.e. the observed values are `0x1440 + 8*k` for k in {0, 1, 16, 32, 33, 64, 65, 68, 80, 81,
84, 96, 97}: `0x1440, 0x1448, 0x14C0, 0x1540, 0x1548, 0x1640, 0x1648, 0x1660, 0x16C0, 0x16C8,
0x16E0, 0x1740, 0x1748`. Bits 6, 10 and 12 are always set. [OBSERVED]

Two populations therefore exist: the document record (a small value equal to `max(id)`) and all
other records (a `0x14xx / 0x15xx / 0x16xx / 0x17xx` word). The same family appears in the
12-byte trailer after the directory (§3.5), which shows the word is a *stamp the writer emits in
several places*, not a property of one record.

**Semantics: [UNKNOWN].** What is excluded by measurement:

* not an offset — `0x16` chunks carry `descriptor = 0x16E0` while the chunk is 16 bytes long;
* not a length — the descriptor is constant across chunk sizes within a type;
* not a checksum — it is (almost) constant across all instances of a type, regardless of content;
* not a sequence number — many records in one file share the same value.

The binary reads this word as part of the 10-byte record and uses the *first* u16 as a slot index
into a 0x10-byte-per-entry in-memory block table (`entry+0x06` bits 12-14 = entry kind; helpers
VA `0x0052F9E0` set `entry+0x0C` from a 6-bit parent link). Several records sharing one value
cannot be a unique table index, so either the decompiler's field split of the 10 bytes is
imprecise or the value is masked before use; this needs one pass with a debugger to settle.

## 3.5 The 12-byte trailer

Immediately after the last record there are always 12 bytes:

```
u16  stamp       0x1640 ×123, 0x1540 ×2, 0x1648 ×2, 0x1548 ×1
u32  0
u32  0
u16  0
```

[OBSERVED] The stamp belongs to the same value family as the record descriptor (§3.4), which is
why the trailer is described as a record-shaped terminator. Meaning [UNKNOWN].

## 3.6 Chunk type census (whole corpus)

10640 chunks over 128 files. `parent types` lists the top three parent chunk types with counts.

| marker | count | bytes | size min/mode/max (distinct) | parent types |
|---|---|---|---|---|
| `0x0006` | 1322 | 70 066 | 53 / 53 / 53 (1) | 0x000F×1170, 0x0014×152 |
| `0x0005` | 1110 | 68 820 | 62 / 62 / 62 (1) | 0x000F×823, 0x0014×287 |
| `0x0000` | 1092 | 111 806 | 102 / 102 / 108 (4) | 0x0014×877, 0x000F×215 |
| `0x000F` | 827 | 35 904 | 38 / 38 / 228 (34) | 0x000F×695, 0x0014×132 |
| `0x0014` | 712 | 30 638 | 36 / 36 / 116 (28) | 0x0015×712 |
| `0x0004` | 696 | 41 064 | 59 / 59 / 59 (1) | 0x000F×460, 0x0014×236 |
| `0x0003` | 617 | 88 318 | 126 / 126 / 958 (12) | 0x0014×386, 0x000F×231 |
| `0x0022` | 489 | 8 802 | 18 / 18 / 18 (1) | 0x0003×489 |
| `0x0031` | 384 | 15 064 | 30 / 30 / 486 (13) | 0x0015×384 |
| `0x0032` | 384 | 12 244 | 16 / 16 / 769 (15) | 0x0031×384 |
| `0x0007` | 266 | 10 906 | 41 / 41 / 41 (1) | 0x0014×148, 0x000F×118 |
| `0x0002` | 248 | 31 360 | 126 / 126 / 182 (2) | 0x0014×136, 0x000F×112 |
| `0x0001` | 218 | 36 016 | 106 / 106 / 540 (18) | 0x0014×149, 0x000F×69 |
| `0x002C` | 137 | 8 300 | 58 / 58 / 100 (6) | 0x0014×137 |
| `0x0021` | 129 | 915 716 | 248 / 1368 / 114 148 (62) | 0x0002×115, 0x0027×14 |
| `0x0015` | 128 | 16 016 | 124 / 124 / 138 (5) | root |
| `0x0029` | 128 | 39 275 | 149 / 171 / 1066 (17) | 0x0015×128 |
| `0x0028` | 128 | 7 383 | 56 / 56 / 86 (6) | 0x0015×128 |
| `0x0023` | 128 | 3 945 | 28 / 30 / 36 (6) | 0x0015×128 |
| `0x001E` | 128 | 28 223 | 63 / 74 / 758 (93) | 0x0015×128 |
| `0x001F` | 128 | 181 796 | 16 / 16 / 33 828 (33) | 0x0015×128 |
| `0x0016` | 128 | 2 048 | 16 / 16 / 16 (1) | 0x0015×128 |
| `0x001A` | 128 | 33 036 | 26 / 54 / 1370 (31) | 0x0016×128 |
| `0x001C` | 128 | 22 136 | 26 / 34 / 890 (45) | 0x0016×128 |
| `0x002D` | 128 | 3 360 | 26 / 26 / 58 (2) | 0x0016×128 |
| `0x002E` | 128 | 3 328 | 26 / 26 / 26 (1) | 0x0016×128 |
| `0x002A` | 128 | 2 545 | 16 / 16 / 203 (3) | 0x0015×128 |
| `0x0026` | 128 | 11 205 | 35 / 35 / 649 (25) | 0x0015×128 |
| `0x0039` | 128 | 6 144 | 48 / 48 / 48 (1) | 0x0015×128 |
| `0x0035` | 74 | 14 800 | 200 / 200 / 200 (1) | 0x0015×74 |
| `0x0034` | 68 | 13 880 | 172 / 172 / 256 (2) | 0x0015×68 |
| `0x002B` | 30 | 887 | 27 / 29 / 34 (3) | 0x0015×30 |
| `0x0037` | 16 | 242 | 14 / 14 / 20 (2) | 0x0015×16 |
| `0x0038` | 15 | 210 | 14 / 14 / 14 (1) | 0x0015×15 |
| `0x0027` | 14 | 588 | 42 / 42 / 42 (1) | 0x0015×14 |

[OBSERVED] Notes:

* 37 distinct markers. No other marker value occurs in the corpus.
* `0x0016` is a container: `0x001A`, `0x001C`, `0x002D` and `0x002E` are its children.
* `0x0003` owns all 489 `0x0022` chunks; `0x0031` owns all 384 `0x0032` chunks.
* `0x0021` (image data) is owned by `0x0002` (image) and by `0x0027`.

## 3.7 Parent graph statistics

Depth = number of `parentId` hops to reach `0x00FE`:

| depth | chunks |
|---|---|
| 0 (document) | 128 |
| 1 | 2465 |
| 2 | 3550 |
| 3 | 855 |
| 4 | 1327 |
| 5 | 1398 |
| 6 | 764 |
| 7 | 137 |
| 8 | 16 |

[OBSERVED] No cycles, no orphan records, and no record whose parent is itself.

## 3.8 Validation predicates

```
directory_offset + 2 + 10*count <= len(Contents) and directory_offset >= 0x22
ids unique ; every parentId == 0x00FE or resolves to an id in the file
only record 0 has parent 0x00FE and it is the 0x15 chunk
chunkOffset strictly ascending ; offset[i+1] == offset[i] + size[i]
first chunk offset == directory_offset + 2 + 10*count + 12
record 0 descriptor == max(id)
all other descriptors in the 13-value set of §3.4
12-byte trailer: u16 stamp in {0x1540,0x1548,0x1640,0x1648}, then 10 zero bytes
every chunk's u16 type marker is one of the 37 markers listed in §3.6
```
