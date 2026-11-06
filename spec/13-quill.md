# 13 — The Quill text engine (Publisher 98 only)

Publisher 98 moved text out of `Contents` into a separate text engine whose data lives in
the stream **`Quill/QuillSub/CONTENTS`**. Publisher 95 and 97 have no `Quill` storage at
all (0 of 358 documents), so all their text is embedded in `Contents`; a reader must
handle both eras.

Five documents in the corpus carry a Quill stream — the two blank `.PUB` files and the
three `.JSP` publications on the Publisher 98 CD. They are small but structurally
complete: between them they exercise 14 of the chunk kinds. `p98/x/MSPUB.PUB` and
`p98/x/ZMSPUB.PUB` have **byte-identical** streams (1 024 bytes), so the corpus holds four
distinct streams.

All layouts in this chapter were checked by `python tools/p97_quill_validate.py`
(5 documents, 62 records, 0 violations). Every statement carries a confidence tag.

## 13.1 Stream header (24 bytes at 0x00)

`[OBSERVED]` — identical field set in all five streams; `FUN_40422354` in `QS98.DLL`
(VA 0x40422354) validates exactly these fields, and `FUN_4041b093` (VA 0x4041b093) writes
the 24-byte header.

| Off | Width | Meaning | Corpus values |
|---|---|---|---|
| `0x00` | char[4] | signature `CHNK` (0x4B4E4843) | 5/5 |
| `0x04` | char[4] | second word `INK ` (0x204B4E49); constant, never validated | 5/5 |
| `0x08` | u16 | container sub-version; loader requires `< 8` | 4 |
| `0x0A` | u16 | **stream format version**; loader requires `> 0`, branches on 5 and 7 | 7 |
| `0x0C` | u16 | **total record count over all directory pages** | 6, 13, 14, 23 |
| `0x0E` | u16 | sub-build; only the high byte (3) is copied to the stream object | 0x0300 |
| `0x10` | u32 | **directory capacity in bytes** (reader's read budget) | 0x90, 0x138, 0x150, 0x400 |
| `0x14` | u32 | **logical stream size** (end of used space); must be `<=` physical size | 0x2A6, 0x14F0, 0x4C56, 0xC200 |

The first directory page header starts at `0x18`; there is no directory-offset field.

Two producer shapes exist and both are accepted because the reader clamps every read with
`min(page capacity, remaining budget)` and bounds the walk by `hdr 0x0C`:

* **writer A** (Publisher's incremental writer): `0x10 = count*24` exactly, `0x14` = exact
  used size, page capacity `0x200`. Seen in `MSPUB.PUB`, `ZMSPUB.PUB`, `CLRCHK.JSP`,
  `INFOSHET.JSP`.
* **writer B** (QS98 bulk rewrite, `FUN_4041b093`): `0x10 = pages*0x200`, `0x14` rounded up
  to a `0x200` multiple, page capacity `0x1F8`. Seen in `CHEKLIST.JSP`.

## 13.2 Directory (chunk-reference) pages

A page is an 8-byte header followed by 24-byte records:

```
+0  u16  capacity   bytes of record area offered by this page (0x200 writer A / 0x1F8 writer B)
+2  u16  count      records in this page; a value >= 0x8000 aborts the walk
+4  u32  next       absolute offset of the next page header, 0xFFFFFFFF = none
+8  count x 24-byte record
```

`[OBSERVED]` chaining, `CHEKLIST.JSP`: page 1 at `0x18 = {0x1F8, 19, 0xC000}`, page 2 at
`0xC000 = {0x1F8, 4, 0xFFFFFFFF}`, `19 + 4 = 23 = hdr 0x0C`.

`[OBSERVED]` **termination is by record count, not by the sentinel**: the reader decrements
`hdr 0x0C` by each page's `count` and stops when the budget reaches zero, so the last
page's `next` word is never consulted. A reader that tests `next == 0xFFFFFFFF` gets the
same picture on all well-formed files but is stricter than the engine.

Record (24 bytes):

```
+0x00  u16     0x0018         record size; 0x18 + 2 + 2n when an extra name is appended
+0x02  char[4] name           lookup key ("TEXT", "STSH", "PLC " is *not* a name, see below)
+0x06  u16     id             ordinal within the name; duplicates need distinct ids
+0x08  u16     1              name-slot count / flags; 1 in all 62 corpus records
+0x0A  u16     0
+0x0C  char[4] name2          secondary name; 50/62 equal to +0x02, 12 hold "PLC "
+0x10  u32     offset         absolute byte offset of the chunk inside the stream
+0x14  u32     length         exact byte count, chunk prologue included
```

`[OBSERVED]` `name2 = "PLC "` on exactly the property-list chunks: `BTEP`, `BTEC`, `STRS`,
`TOKN`, `TCD ` — it is a **class tag**, not a chunk name. `[OBSERVED]` in `QS98.DLL` the
immediate 0x20434C50 occurs only as the 4th argument of the record writer `FUN_404132c9`,
which stores it at record `+0x0C`.

**Correction to §13.2 of the previous revision**: the names `PL  `, `SHPT` and `STSH2` do
**not** exist. `[OBSERVED]` a byte scan of `p98/quill/QS98.DLL` (460 560 bytes) finds
`TEXT`, `STRS`, `SYID`, `FDPC`, `FDPP`, `STSH`, `FONT`, `TCD `, `TOKN`, `MCLD`, `BTEP`,
`BTEC`, `BMKT`, `PRNT`, `SGP `, `INK `, `CHNK`, `FTN `, `EOBJ` (each twice: a writer and a
loader reference) and `PLC ` once — and **zero** occurrences of `SHPT`, `STSH2`, or
`PL  `. The `STSH2`/`SHPT`/`PL  ` names in the earlier revision came from the Publisher
2000+ vocabulary and must not be dispatched on.

Additional names that exist only as code immediates and have no corpus instance:
`FREE` (the free-list pseudo-chunk), `EDN ` (endnote), `SGFD` (pre-0x6B style record).

## 13.3 Chunk kinds observed

| Name | Docs | Instances | Lengths | Role |
|---|---|---|---|---|
| `TEXT` | 3 | 3 | 1 404, 2 082, 23 130 | the character array |
| `STRS` | 3 | 3 | 30, 142, 774 | string/format table |
| `FDPP` | 3 | 9 | 512 ×9 | paragraph property runs |
| `FDPC` | 3 | 5 | 512 ×5 | character property runs |
| `STSH` | 5 | 10 | 30 … 1 324 | style sheets; exactly two per document |
| `SYID` | 5 | 5 | 8, 12, 68, 384 | style-id map |
| `FONT` | 5 | 5 | 60 … 156 | font table |
| `SGP ` | 5 | 5 | 4 | encoded document-property block |
| `INK ` | 5 | 5 | 4 | format version record |
| `BTEP` | 3 | 3 | 24, 32, 64 | position→value table |
| `BTEC` | 3 | 3 | 24, 40 | position→value table |
| `TCD ` | 1 | 2 | 80, 116 | table cell data |
| `TOKN` | 1 | 1 | 52 | token table |
| `MCLD` | 3 | 3 | 296, 14 484, 17 788 | document-level list |

`[OBSERVED]` — 62 records over the five streams.

Chunk payloads use exactly **three framings**, and the chunk name (plus its `PLC ` class
tag) selects which:

| framing | chunks | §  |
|---|---|---|
| raw | `TEXT`, `INK ` | 13.4, 13.12 |
| 20-byte prologue + offset table | `STSH`, `FONT` | 13.7 |
| 12-byte header + offset table + elements | `STRS`, `BTEP`, `BTEC`, `TOKN`, `TCD ` | 13.8–13.10 |
| fixed 512-byte page | `FDPP`, `FDPC` | 13.5 |
| `u32`-prefixed list | `SGP `, `MCLD`, `SYID` | 13.11, 13.9 |

## 13.4 `TEXT` — character array

`TEXT` is **UTF-16LE** with no count prefix, no BOM and no terminator:
`[OBSERVED]` `CHEKLIST.JSP` starts `20 00 4D 00 69 00 …` = " Microsoft Publisher 98\t…",
`CLRCHK.JSP` starts `4D 00 69 00 …` = "Microsoft Publisher 98 Color Sch…".
Length is always even (`[OBSERVED]` 3/3) and every chunk decodes as UTF-16LE.

The `FDPP`/`FDPC` run tables address the array by **absolute stream byte offset**, not by
character index: a run position is a byte offset that equals `0x200 + 2·charIndex` because
`TEXT` is always the first page-aligned chunk at `0x200` (`[OBSERVED]` 3/3). A reader must
therefore use `pos - TEXT.offset` as the byte offset.

## 13.5 `FDPP` / `FDPC` — property runs

Both chunks are **fixed 512-byte pages** (`[OBSERVED]` 14/14), written with the
caller-supplied-offset allocation mode of `FUN_404132c9`, so the chunk length is the page
size and not the payload size. The real extent is encoded by the header.

```
+0x00  u16      count        number of runs
+0x02  u16      1            layout version (loader does not branch on it)
+0x04  u32      start        first text offset covered by this chunk
+0x08  u32      pos[count]   run start offsets, ascending, absolute in the stream
+0x08+4c u16     id[count]   per-run descriptor id (see 13.6)
+align4         u32 size[nd] right-aligned pool of nd length-prefixed descriptor blobs
```

`[OBSERVED]` on all 14 chunks:

* `pos[]` is strictly ascending; `pos[count-1]` is the end of this chunk's text range.
* The `start` field chains: it is `0` for the first chunk of a name and equals the previous
  chunk's `pos[count-1]` for every later one (14/14). `CHEKLIST.JSP` `FDPP`:
  `0 → 0x764 → 0xFE4 → 0x25CE → 0x3D52 → 0x4B2C → 0x5C5A`; `FDPC`:
  `0 → 0xCF4 → 0x3C32 → 0x5C5A`.
* The last `pos` of the last chunk of a name equals `TEXT.offset + TEXT.length`
  (`0x5C5A` in `CHEKLIST.JSP`, `0x77C` in `CLRCHK.JSP`, `0xA22` in `INFOSHET.JSP`).
  So the runs of one name partition the whole character array.
* The number of distinct `id` values equals the number of blobs in the pool (`nd`), and the
  pool's blobs are right-aligned: the walk ends exactly at `0x200`. Leading slack between
  the id array and the pool start is unwritten and must be skipped by locating the pool
  from its end (the writer fills the page from the end backwards).
* `[OBSERVED]` 107 blobs across the 14 chunks parse exactly with the grammar of §13.6
  (0 failures).

`[OBSERVED]` corpus counts: `CHEKLIST.JSP` 6 `FDPP` chunks (23/25/26/32/34/23 runs) and 3
`FDPC` (18/46/48); `CLRCHK.JSP` 2 `FDPP` (79/16) and 1 `FDPC` (19); `INFOSHET.JSP` 1
`FDPP` (63) and 1 `FDPC` (34).

`[INFERENCE]` the per-run `id` is a 16-bit fingerprint of the run's property set; equal
runs in different documents carry the same id (`0x01FC` = plain paragraph, present in
`CLRCHK.JSP` and `INFOSHET.JSP`). The corpus does not contain a case where one id maps to
two different blobs within one chunk, but across chunks 19 ids do, so the mapping must be
positional (first-use order), not by id value.

## 13.6 The field-descriptor stream (shared by `FDPP`, `FDPC`, `STRS`, `SGP `)

All four carriers embed the same serializer output. A descriptor stream is

```
u32 totalSize          ; includes these 4 bytes
records[totalSize-4]
```

and each record is `{u16 tag; payload}`, where `tag = fieldId(11 bits) | code(5 bits)`:

| code | tag mask | record size | payload |
|---|---|---|---|
| 1 | `0x0800` | 2 | none |
| 2 | `0x1000` | 4 | u16 at +2 |
| 3 | `0x1800` | 4 | u16 at +2 |
| 4 | `0x2000` | 6 | u32 at +2 |
| 0x10 | `0x8000` | `2 + len` | `len-4` bytes at +6 (nested list) |
| 0x11 | `0x8800` | `2 + len` | `len-4` bytes at +6 (nested list) |

`[OBSERVED]` code→width for 2/3/4 comes from the three emitters in `QS98.DLL`:
`FUN_404196cb` (byte, tag `|0x1000`), `FUN_40419676` (u16, `|0x1800`), `FUN_40410809`
(u32, `|0x2000`), and the record framer `FUN_4041082d`. The codes 1, 0x10 and 0x11 and
their exact sizes are `[OBSERVED]` from the corpus: with this table 107/107 `FDPP`/`FDPC`
blobs, 3/3 `STRS` entries and the `SGP ` payload parse to their exact byte length with no
slack. Any other assignment leaves a remainder, so the table is pinned by exhaustion.

Field ids seen in the corpus (11-bit values): `0x200`–`0x228`, `0x40A`, `0x1A03`,
`0x1A19`, `0x1A27`. `[UNKNOWN]` their meanings; the emitter table lives at
`DAT_40463adc` in `QS98.DLL` and maps id→(type char, byte offset, width).

`SGP ` is exactly one descriptor stream: 4 bytes `04 00 00 00` = an empty stream
(`totalSize == 4`). A non-default page/section setting would populate it. `[OBSERVED]`
5/5 corpus chunks are the empty form.

## 13.7 `STSH` / `FONT` — 20-byte prologue + offset table

`[OBSERVED]` 15/15 chunks (`STSH` ×10, `FONT` ×5) satisfy the identity below; the reader is
`FUN_40422608` (VA 0x40422608), which reads exactly 0x14 bytes.

```
+0x00  u32  size        bytes after the prologue  (== chunkLength - 20)
+0x04  u32  count       number of entries
+0x08  u32  flags       masked to 14 bits by the loader; per-document, not consumed
+0x0C  u32  trailSize   bytes appended to every entry (4 for FONT and STSH id 0, 0 for STSH id 1)
+0x10  4 B  not read    per-document, often stale stack content
+0x14  u32  offset[count]   entry offsets, relative to +0x14
       ...  entries
```

Entry: `u16 cch`, then `cch` UTF-16LE code units, then `trailSize` bytes. No NUL is stored.

Size identity (holds 15/15):
`size == 4*count + Σ(2 + 2*cch_i + trailSize)`.

For `FONT` the 4-byte trailer is `u16 fontIndex, u8 charset, u8 pitchFamily`
`[OBSERVED]` `MSPUB.PUB` FONT entry = `"Times New Roman"` with trailer `00 00 01 00` →
index 0, charset 1 (`DEFAULT_CHARSET`), pitch 0. `[INFERENCE]` the index is a cache of the
saving machine's font table and a reader must re-resolve by name.

Corpus: `STSH` id 0 has `trailSize = 4` and id 1 has `trailSize = 0` in all five documents;
`FONT` always has `trailSize = 4`. `CHEKLIST.JSP` has the largest pair: `STSH` id 0 = 262 B
with 9 entries, id 1 = 1 324 B with 18 entries; `FONT` = 156 B with 5 entries.

`STSH` id 0 is the paragraph style sheet and id 1 the character style sheet `[INFERENCE]` —
consistent with the trailer sizes and with the loader reading them as two separate tables
(`FUN_4042278c` looks up `STSH` id 0 and id 1 and merges them via `FUN_40422ff9`).

## 13.8 `STRS` — string table

```
+0x00  u32  count       number of entries
+0x04  u32  8           element size; the loader asserts this for INK >= 0x6D
+0x08  u8   f0          flags → in-memory table bits 0/1/2; 0xFF in the corpus
+0x09  u8   f1          0
+0x0A  u8   f2          0
+0x0B  1 B  padding
+0x0C  u32  offsets[count+1]   table read as one block of 4*(count+1) bytes
+...        entry[count]       each {u32 size; descriptor stream[size-4]}
```

`[OBSERVED]` 3/3 chunks consume exactly their length with this layout:
`INFOSHET.JSP` `count = 1`, `12 + 8 + 10 = 30 = 0x1E`;
`CLRCHK.JSP` `count = 0x5E`, `12 + 4·95 + Σ = 774 = 0x306`;
`CHEKLIST.JSP` `count = 0x0F`, `12 + 64 + 66 = 142 = 0x8E`.
Each entry body parses as a descriptor stream (§13.6), e.g. `INFOSHET.JSP` entry 0 =
`0A 00 00 00 | 00 22 05 00 00 00` = one code-4 record, field `0x200` = 5.

**Correction to §13.4 of the previous revision**: the values after the header are not
string lengths and there is no contiguous UTF-16 block; they are the offset table and the
strings live inside the per-entry descriptor streams.

## 13.9 `SYID` — style-id map

```
+0x00  u32  highWater    next free style id
+0x04  u32  count
+0x08  u32  ids[count]   ascending
```

`[OBSERVED]` size identity `len == 8 + 4*count` in 5/5 chunks: `MSPUB.PUB` 8 B / 0 entries;
`INFOSHET.JSP` 12 B / 1; `CHEKLIST.JSP` 68 B / 15 (high-water 31); `CLRCHK.JSP` 384 B / 94
(high-water 127). Values are dense ascending style ids; `CHEKLIST.JSP` = `1…14` plus `0x0F`.

## 13.10 Element arrays — `BTEP`, `BTEC`, `TOKN`, `TCD `

```
+0x00  u32  count
+0x04  u32  elemSize     (minus 4 when a name table is attached)
+0x08  u8   f0
+0x09  u8   f1
+0x0A  u8   hasNameTable  1 when a §13.7 table is appended
+0x0B  u8   0
+0x0C  u32  offsets[count+1]
+...        elements[count * elemSize]
```

`[OBSERVED]` size identity `len == 16 + 4*count + count*elemSize` holds for every corpus
chunk: `BTEP`/`BTEC` `elemSize = 4` (3/3 each), `TOKN` `elemSize = 0xC` (1/1),
`TCD ` `elemSize = 0` with the stride carried by the header (2/2: 0x19 elements × 4 bytes
of offsets → 116 bytes; 0x10 → 80 bytes). Reader `FUN_404223b4`; the `elemSize == 0` form
means "keep the on-disk stride".

`[OBSERVED]` in `QS98.DLL` `BTEP`/`BTEC` are consumed by `FUN_4040775f` →
`FUN_404076d9`, which turns them into `(u16 count, count × (i32 start, i32 value))` ranges
searched by character position — i.e. a position→property map, not drawing data. The
property itself is `[UNKNOWN]`.

## 13.11 `MCLD` — document-level list

```
+0x00  u32  tag         20 in CHEKLIST.JSP, 114 in CLRCHK.JSP, 1 in INFOSHET.JSP
+0x04  u32  count
+0x08  u32  ids[count]  the ids equal the document's object ordinals (1..count)
+...        per-id sub-blocks
```

`[OBSERVED]` header and id list (3/3: 18, 94, 1 entries; ids dense and ascending, ending at
`tag`). The sub-blocks start with `u32 0C 00 00 00` followed by a 12-byte descriptor
stream in all three documents; the remainder is `[UNKNOWN]` — the first two sub-block
lengths are 12 and 134 in all three, which suggests a nested list rather than one record
per id.

## 13.12 `INK ` and the version gates

`INK ` is 4 bytes, `{u16 version, u16 maxVersion}`; all five streams hold `72 00 72 00`
(114/114). `[OBSERVED]` `FUN_40421ec1` accepts a file only when
`version ∉ [0x6A,0x6B] && version > 0x68 && maxVersion < 0x73`; anything else aborts the
open. The version drives every layout branch: `< 0x65` clears the modern name layout,
`< 0x6A` sets the legacy flag, `< 0x6D` selects the flat `STRS` body, `> 0x6C`/`> 0x6E`
select the modern `TCD `/`TOKN` variants.

`0x72` therefore selects: modern 24-byte record layout, modern `STRS`, no obfuscation
(stream flag bit1 clear, so no `FUN_40452ab4` decoding pass).

## 13.13 How text attaches to shapes

The Quill stream holds the character array and the run tables; the shapes reference ranges
of it. `[UNKNOWN]` — the linkage is the second-largest gap and the one that matters most
for rendering. What is now excluded:

* `FDPP`/`FDPC` chunk ids are *not* shape ids: they run 0…5 and 0…2 while
  `CHEKLIST.JSP` has 67 document chunks.
* `SYID` holds style ids (dense 1…n), not shape ids.

Remaining candidates: the per-run `start` field of `FDPP`/`FDPC` (which partitions the
text into 6 and 3 ranges respectively — matching the number of text frames in
`CHEKLIST.JSP`), and a text-frame id inside the shape record. Experiment: count the text
frames in `CHEKLIST.JSP` (shape chunks whose `0x0016`-referenced style is a text frame)
and compare with 6.

## 13.14 Publisher 95 / 97 — the in-`Contents` text layer

Publisher 95 and 97 have no `Quill` storage (0 of 358 documents on those two CDs). Their text
lives **inside `Contents`**, in a store that sits between the fixed header block and the chunk
directory. It is present in every document of every version, at a version-dependent offset, and
was previously unlocated. [OBSERVED]

| Version | Store offset | Documents | Text-object records |
|---|---|---|---|
| Publisher 95 | `0x23E` (574) | 130/130 | 3 per document (390) |
| Publisher 97 | `0x280` (640) | 357/358 (one legacy at 574) | 3 per document (1074) |
| Publisher 98 | `0x37E` (894) | 5/5 | **none** — the store is empty and the text is in Quill |

All 1 464 records in the 95/97 corpora satisfy the framing below (0 exceptions).

```
<store>  <text store>          starts at the version offset above
  +0x00  u16   0xF0DE          signature, 493/493 documents
  +0x02  u16   46              header length; textBase = store + 46
  +0x04  u16   0x012C          format version echo (300)
  +0x06  u16   0x0200          constant
  +0x08  u16   0              constant
  +0x0A  u32   directory offset (== header u32@0x16)
  +0x0E  u32   textBase        == store + u16@+0x02
  +0x12  u32   textEnd         end of the character array
  +0x16  u32   0              constant
  +0x1A  u32   0              constant
  +0x1E  u32[4] pointer array  offsets of up to 4 text-object records; exactly 3 non-zero
  +0x2E  …                     the character array, [textBase, textEnd)
```


The two `u32` at `+0x0E`/`+0x12` and the pointer array at `+0x1E` make the store self-describing: its size
is `directoryOffset − 0x23E`, which is why the directory offset cannot be derived from the header
constants.

### 13.14.1 Character array

`[textBase, textEnd)` is plain CP1252 text, not UTF-16: 152 055 bytes over the corpus, median
180 bytes per document, maximum 13 626, empty in 4 documents. Line breaks are `0D 0A`; other
control bytes present are `0x0F` ×2411, `0x0C` ×1067 (page/section break), `0x09` ×235, `0x0B` ×35,
`0x05` ×27. `0x92`/`0x93`/`0x94` occur as CP1252 quotes. The meaning of `0x0F` is [UNKNOWN]; it
is the most frequent inline code and the best first target for run-level formatting. [OBSERVED]

### 13.14.2 Text-object records

Exactly **three** per document in every Publisher 95/97 document (488 documents, 1 464 records),
at the three non-zero pointers, sorted by offset, the last one ending exactly at the directory
offset. All records share one layout:

```
+0x00  u16  0x001D        marker (not a directory chunk type: these records are not in the directory)
+0x02  u8   4             A
+0x03  u8   4             B
+0x04  u16  n             entry count
+0x06  u16  n             duplicate
+0x08  u16  2             element size of the id array
+0x0A  u16  k             0/1/2 — [UNKNOWN]
+0x0C  u32  0
+0x10  u32  0
+0x14  u16  0
+0x16  u32  textStart
+0x1A  u32  bound[n]      n ascending text offsets (the last ≤ textEnd + 2)
+0x1A+4n  u16 id[n]       n ascending small ids (< 0x100); a paragraph/run id
size == 0x1A + 6·n        1 464/1 464 records, zero exceptions
```

Verified over all 1 464 records [OBSERVED]:

| property | result |
|---|---|
| `size == 0x1A + 6·n` | 1 464/1 464 |
| `u16@+0x04 == u16@+0x06` | 1 464/1 464 |
| `u16@+0x08 == 2` | 1 464/1 464 |
| `u16@+0x0C`, `u16@+0x10`, `u16@+0x14` are zero | 1 464/1 464 |
| `textStart` inside `[textBase, textEnd]` | 1 464/1 464 |
| `bound[]` non-decreasing and inside `[textStart, textEnd + 2]` | 1 464/1 464 |
| `id[]` strictly ascending, all `< 0x100` | 1 464/1 464 |

The `+2` tolerance is systematic: the third record of 103 documents ends two bytes past
`textEnd`, i.e. the header's `textEnd` excludes the trailing `CR LF` that the last story still
covers. Reading: the three records are the document's three **text stories** (body / header /
footer, or the three text frames the templates use), each holding paragraph boundaries plus the
per-paragraph id list. [INFERENCE: the three-way split is constant in every document; the
record interior is otherwise consistent]

### 13.14.3 What this closes and what it does not

* Closes: "where is Publisher 95/97 text" — it is uncompressed CP1252 at a fixed, self-described
  location inside `Contents`, with a 3-record paragraph index.
* Still open: the **run-level formatting** (font, size, bold/italic/underline, alignment,
  numbering). No per-character attribute record has been found; the paragraph ids are the handle
  that a formatting record would key on. The leading candidate is the `0x0F` control byte inside
  the character array. [UNKNOWN — experiment: author one paragraph in bold + one underlined,
  save, and diff the store byte by byte]

### 13.14.4 Publisher 97 variant and corpus-wide invariants

The store is **relocated, not reshaped**, in Publisher 97: it starts at `0x280` instead of
`0x23E` (`+0x42`), the header is still 46 bytes, and `textBase` is therefore `0x2AE`
instead of `0x26C`. `[OBSERVED]` on 357 of the 358 Publisher 97 documents;
`p97/x/INFLNTLB.PUB` uses the Publisher 95 form, and the 131 documents at the `0x23E`
base are the 130 Publisher 95 files plus that one.

| field | P95 | P97 |
|---|---|---|
| store base | `0x23E` | `0x280` |
| `u16 +0x00` signature | `0xF0DE` | `0xF0DE` |
| `u16 +0x02` header length | 46 | 46 |
| `u32 +0x0A` directory offset | `Contents +0x16` | `Contents +0x16` |
| `u32 +0x0E` textBase | `0x26C` | `0x2AE` |
| `u32 +0x12` textEnd | per document | per document |
| text-object pointers | `+0x1E` | `+0x1E` (identical layout) |

Worked example — `p97/x/AUTHPERS.PUB`, store at `0x280`:
`DE F0 | 2E 00 | 2C 01 | 00 02 | 00 00 | 60 0A 00 00 | AE 02 00 00 | CC 02 00 00` — signature
`0xF0DE`, length 46, version 300, `0x0200`, 0, directory offset `0xA60`, textBase `0x2AE`,
textEnd `0x2CC`; the three text-object records sit at `0xA00`, `0xA20`, `0xA40` (pointers at
store `+0x1E`, `+0x22`, `+0x26`).

**Corpus-wide invariants over all 488 Publisher 95/97 documents**
(`tools/p97_quill_validate.py`, 488 files, 0 violations):

| invariant | result |
|---|---|
| a `u32` equal to the directory offset exists once in `0x22 … 0x600` | 488/488 |
| that word is followed by a `(textStart, textEnd)` pair inside `Contents` | 488/488 |
| the character pool contains **no NUL byte** | 488/488 |
| every `0x0A` is part of a `0x0D 0x0A` pair | 488/488 (one file adds 22 bare `0x0D`) |

Pool size over all 488 documents: 0 (17 documents) … 13 626 bytes, median 202. Byte census:
`0x0D` 15 654, `0x0A` 15 632, `0x0F` 6 281, `0x0C` 4 798, `0x09` 697, `0x0B` 120, `0x05` 81,
CP1252 high bytes `0x92` 408 / `0x93` 164 / `0x94` 149 / `0x97` 46 / `0x91` 6 / `0xF3` 12.
`[OBSERVED]`

Because the store's position is version-dependent and its size is
`directoryOffset − storeBase`, a reader must locate it by the signature `0xF0DE` at the
store base for the detected version, not by a constant absolute offset.

## 13.15 Validation

`tools/validate.py` checks that the chunk-reference chain terminates at `0xFFFFFFFF` inside
the stream (`quill_list_terminates`, 5/5).

`tools/p97_quill_validate.py` re-derives every identity in this chapter:

| corpus | documents | checks | result |
|---|---|---|---|
| `p98/x` (Quill mode) | 5 | header predicates, page chain, record count, `TEXT` decodability, `FDPP`/`FDPC` ascending positions + range chain + descriptor pool + blob parse, `STSH`/`FONT` size identity and entry bounds, `STRS` exact consumption, `SYID` size identity, element-array size identity, `MCLD` header | 0 violations |
| `p95/x`, `p97/x`, `p97deluxe/x` (text-pool mode) | 488 | store signature `0xF0DE`, header length 46, directory-offset word, `textBase == storeBase + 0x2E`, `textEnd` bounds, NUL-free pool, LF ⊆ CR | 0 violations |

The Quill side covers 62 records and 107 descriptor blobs; the 95/97 side covers 488
documents, 487 of which use the version-correct store base (the exception,
`p97/x/INFLNTLB.PUB`, uses the Publisher 95 base and is reported by the scanner rule, not
by a constant offset).

## 13.16 Open

| Item | Status | Experiment |
|---|---|---|
| field-id meanings in the descriptor stream | `[UNKNOWN]` | decode the id→(type, offset, width) table at `DAT_40463ADC` in `QS98.DLL` |
| text → shape linkage | `[UNKNOWN]` — narrowed: the run tables partition the character array (6 `FDPP` / 3 `FDPC` ranges in `CHEKLIST.JSP`), and the 95/97 pool splits into `0x0C`-terminated stories (28 stories vs 26 `0x0000` chunks in `CATALOG.PUB`), but no chunk stores the pool bounds as a `u32` | author a document with two text frames whose contents are swapped, save, and diff the run tables |
| run-level formatting in the 95/97 pool | `[UNKNOWN]` | author one bold and one underlined paragraph, save, diff the store byte by byte (§13.14.3) |
| `MCLD` sub-block interior | `[UNKNOWN]` | dump the three corpus `MCLD` chunks; correlate the 12/134-byte pair with object counts |
| `BTEP`/`BTEC` property identity | `[UNKNOWN]` | compare a document with table borders against one without |
| `TCD ` cell interior | `[UNKNOWN]` | dump a 2×2 table document; the container framing is already fixed (§13.10) |
