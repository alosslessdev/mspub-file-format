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
| 0 | `0x0000` | 2 | none — id present, value explicitly zero |
| 1 | `0x0800` | 2 | none — boolean true |
| 2 | `0x1000` | 4 | u8 at +2 |
| 3 | `0x1800` | 4 | u16 at +2 |
| 4 | `0x2000` | 6 | u32 at +2 |
| 5 | `0x2800` | 10 | 8 bytes at +2 (two u32) |
| 0x10 | `0x8000` | `2 + len` | `len-4` bytes at +6 (nested list) |
| 0x11 | `0x8800` | `2 + len` | `len-4` bytes at +6 (nested list) |

`[OBSERVED]` the whole 32-entry code→size table is a real table in `QS98.DLL` at
**VA `0x404680C8`** (stride 8: `{u32 size; u32 variable}`), indexed by `tag >> 11` by the
element-size function `FUN_404076b1` (VA 0x404076b1). Its values are `2,2,4,4,6,10` for
codes 0–5, `variable=1` on 0x10/0x11, and `2` for every other code (0x06–0x0F,
0x12–0x1F) — codes 0x1C, 0x1D and 0x1E are merge markers with an id but no payload.
Code 5's 8-byte payload is emitted by `FUN_4044dc0f` (VA 0x4044dc0f: two u32 at +2 and
+6, tag `|0x2800`); codes 2/3/4 by `FUN_404196cb` / `FUN_40419676` / `FUN_40410809`;
code 1 and 0 by `FUN_40419623` (VA 0x40419623: `tag = value << 11 | id`, so a boolean true
is code 1 and false is code 0). The record framer is `FUN_4041082d`.

`[OBSERVED]` **correction to the previous revision**: the values `0x40A`, `0x1A03`,
`0x1A19` and `0x1A27` are *tags*, not field ids — `0x1A03 = code 3 | id 0x203`,
`0x1A19 = code 3 | id 0x219`, `0x1A27 = code 3 | id 0x227`, and `0x40A = code 0 | id 0x20A`
(a boolean written false). All four resolve inside the paragraph class exactly as its field
table declares (§13.17). Field ids are 11-bit and never exceed `0x233` in the corpus.

`[OBSERVED]` with this table 107/107 `FDPP`/`FDPC` blobs, 3/3 `STRS` entries and the
`SGP ` payload parse to their exact byte length with no slack; §13.17 supplies the id
meanings and the type/width/offset of every id.

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
+...        elements, one of two forms:
             contiguous (mode -1):  count * elemSize bytes
             packed (any other):    count x {u32 len; len-4 bytes}, one descriptor each,
                                    then one more {u32 0x0A; tag 0x2200 = 0xFFFFFFFF}
```

`[OBSERVED]` reader `FUN_404223b4` (VA 0x404223b4) reads exactly 12 header bytes
(`count`, `elemSize`, then `f0 f1 f2 00` folded into three flags), then `4*(count+1)`
offset bytes. Whether element bytes follow — and in what form — is decided by the caller's
mode argument: **mode `-1`** reads `count*elemSize` contiguous bytes, **any other mode**
reads `count` consecutive `{u32 len; len-4 bytes}` items and decodes each one as a
descriptor stream into a fixed `elemSize` slot (`FUN_4042251d`, VA 0x4042251d). The mode
comes from the version, not from the header: `TOKN` gets 7 when the `INK ` version exceeds
0x6E and `-1` otherwise, and `TCD ` always gets `-1` (`FUN_4042278c`, VA 0x4042278c). All
corpus streams are version 0x72, so they take the mode quoted for each chunk below.

Size identity `len == 12 + 4*(count+1) + count*elemSize` therefore holds only in the
contiguous form: `BTEP`/`BTEC` `elemSize = 4` (3/3 each), `TCD ` `elemSize = 0` (2/2:
0x19 → 116 bytes, 0x10 → 80 bytes — the offset table is the *whole* payload).
`[OBSERVED]` `TOKN` breaks it (1/1: 52 bytes, `elemSize = 0xC`, count 1) because its
element area is packed: `{u32 0x16; 22-byte descriptor stream}`, then one more
`{u32 0x0A; 6-byte stream}` item whose only record is `tag 0x2200 = 0xFFFFFFFF`;
`f2 = 1` in the header, the same bit `FUN_404223b4` raises as its third flag.

`[OBSERVED]` **`BTEP` / `BTEC` are the run-table index, and this closes their identity.**
Both are written from two global containers (`+0x284` → `BTEP`, `+0x280` → `BTEC` of the
document object) by `FUN_4041a94b` (VA 0x4041a94b), and each `FDPP`/`FDPC` chunk is
appended to that container as it is emitted (`FUN_40419d9b` VA 0x40419d9b for `FDPP`,
`FUN_40419fe2` VA 0x40419fe2 for `FDPC`). The two arrays are:

* `offsets[0..count]` — the concatenated `pos` chain of the runs, i.e.
  `offsets[i] == start` of `FDPP`/`FDPC` id `i` and `offsets[i+1] == pos[count_i - 1]`
  of the same chunk.
* `elements[0..count-1]` — `elemSize = 4`, each a **u32 absolute stream offset of the
  `FDPP`/`FDPC` chunk with that directory id**.

`[OBSERVED]` 14/14 elements and 16/16 chain links over the three corpus documents:
`CHEKLIST.JSP` `BTEP` = `0, 0x764, 0xFE4, 0x25CE, 0x3D52, 0x4B2C, 0x5C5A` + chunk offsets
`0x5E00 0x6000 0x6200 0x6400 0x6600 0x6800` (= `FDPP` id 0…5), `BTEC` =
`0, 0xCF4, 0x3C32, 0x5C5A` + `0x6A00 0x6C00 0x6E00` (= `FDPC` id 0…2);
`CLRCHK.JSP` `BTEP` = `0, 0x67E, 0x77C` + `0x800 0xA00`, `BTEC` = `0, 0x77C` + `0xC00`;
`INFOSHET.JSP` `BTEP` = `0, 0xA22` + `0xC00`, `BTEC` = `0, 0xA22` + `0xE00`.

`[OBSERVED]` the per-object element arrays (`TOKN`, `TCD `) carry the **0-based text-object
ordinal in the directory record's `id` field** — the same value `FUN_4041a94b` passes for
both (`(short)element_index`). `CHEKLIST.JSP` has `TOKN` id 0 and `TCD ` ids 1 and 2, and
each `id + 1` is a member of that document's `MCLD` ordinal list (§13.11).

## 13.11 `MCLD` — document-level object records

```
+0x00  u32  tag         20 in CHEKLIST.JSP, 114 in CLRCHK.JSP, 1 in INFOSHET.JSP
+0x04  u32  count
+0x08  u32  ids[count]  1-based text-object ordinals, ascending
+...        count x { u32 sizeA; streamA[sizeA-4] ; u32 n; n x { u32 sizeB; streamB[sizeB-4] } }
```

`[OBSERVED]` the framing above walks all three corpus chunks to exactly their length
(3/3: 17 788 / 14 484 / 296 bytes; 18 + 94 + 1 objects, 339 streams total), and every
`size` is 4-byte aligned and at least 4. `[OBSERVED]` the first sub-block of each object
is the same 12-byte unit in all 113 objects: `0C 00 00 00` + `{id 0x200 = 0; id 0x201 =
u32}` — 8 bytes of descriptor stream, i.e. a two-field object header. The `n` blocks that
follow vary from 1 to 30 per object (`CLRCHK.JSP` exactly 1 in all 94 objects,
`INFOSHET.JSP` 2, `CHEKLIST.JSP` 1/15/17/26/29/30), so the earlier "12 and 134 in all
three" observation was the *first* object's pair only.

`[OBSERVED]` the two stream kinds are two different **classes of the §13.17 property
table**:

* `streamA` is always 8 bytes and is **class 18**, which has exactly two fields —
  `0x200` (boolean at +0x00) and `0x201` (u32 at +0x04). 113/113 objects; the boolean is
  a real value, not a constant: false (code 0) in 109 objects, true (code 1) in 4
  (`CHEKLIST.JSP` 15/3, `CLRCHK.JSP` 94/0, `INFOSHET.JSP` 0/1).
* every `streamB` is exactly **class 12**'s 25-field record: `sizeB = 134` in 226/226
  blocks, the stream 130 bytes, and all 25 ids appear in every block in ascending order.

| identity | result |
|---|---|
| `sizeA == 12` and `sizeB == 134` | 113/113 and 226/226 |
| `streamA` ids ⊆ class 18 (`0x200`,`0x201`) with matching codes | 113/113 |
| `streamB` ids == class 12's exact id set (`0x200`–`0x20E`, `0x211`–`0x21A`) | 226/226, 5 650/5 650 tags |
| `streamB` code == class-12 type for that id (`f` → code 0/1) | 5 650/5 650, 0 exceptions |
| `streamB` byte length == 130 (sum of the 25 encoded widths) | 226/226 |

`[INFERENCE]` the leading class-18 unit is the object's identity pair (a boolean plus a
u32; `0x37CF8` = 228 600 in every `CHEKLIST.JSP`/`INFOSHET.JSP` object, `0` in all of
`CLRCHK.JSP`) and each class-12 record is one document-level property set for that object.
The *names* of the 25 properties are `[UNKNOWN]`; §13.17 lists their types and target
offsets.

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
of it. `[OBSERVED]` the linkage has two halves, and the stream half is now pinned:

**1. Text object → run tables.** `BTEP`/`BTEC` are the index of the run tables: element
`i` is the absolute stream offset of `FDPP`/`FDPC` record id `i`, and `offsets[i]` is that
chunk's `start` (14/14 elements, §13.10). A reader that has the shape's text-object
ordinal can therefore reach the paragraph/character runs without any other structure.

**2. Shape → text object.** The Quill per-object chunks (`TOKN`, `TCD `) carry the 0-based
text-object ordinal in the directory record `id`, and `MCLD` lists the same ordinals
1-based (113 objects over the corpus, §13.11). In `CHEKLIST.JSP` the `TCD ` ids 1 and 2
and the `TOKN` id 0 all satisfy `id + 1 ∈ MCLD.ids`. `[OBSERVED]`

What is now **excluded**, with counts over the three text-bearing documents:

| candidate | result |
|---|---|
| `FDPP`/`FDPC` chunk ids are shape ids | no — they run 0…5 / 0…2 while the `Contents` shape chunks are ids `0x100`+, 3/3 docs |
| `SYID` ids are shape chunk ids | no — `SYID` values are ≤ `0x7F` (`CHEKLIST.JSP` max 17, `CLRCHK.JSP` max 127) and no `Contents` chunk id is below `0x100` |
| `SYID` ids are text-object ordinals | no — the sets differ in 2 of 3 documents: `CHEKLIST.JSP` `SYID` = `{1…14, 17}` vs `MCLD.ids` = `{1,2,3,5,7,…,20}` (4 and 6 are `SYID`-only, `15,16,18,19,20` are `MCLD`-only); `CLRCHK.JSP` 94 `SYID` ids vs 94 `MCLD` ids with 20+ differences; `INFOSHET.JSP` coincides trivially (one id, `1`) |

`[UNKNOWN]` the remaining half: which field of the `Contents` shape record holds the
text-object ordinal. Candidate measured in `CHEKLIST.JSP`: the 10 top-level shape chunks
(type `0x14`, parent `0x100`) each carry a u32 at chunk `+0x14` of `2, 6, 10, 14, 18, 22,
26, 30, 34, 38` — a strictly monotone `4k+2` ladder, i.e. an index with a 2-bit tag, not
the object ordinal. Experiment that would settle it: take a document with exactly two
text frames, swap their text, and diff every `Contents` shape record against the unchanged
`MCLD`/`TOKN` ids — the field that moves is the ordinal.

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

The section is bounded by two header fields: it starts at `Contents u32@0x12` and ends at
`Contents u32@0x16`; the first chunk of every document starts at or after that end, so the
section never overlaps the chunk area (0/493 documents). The first dword is one packed value:
`0x002EF0DE` — low word `0xF0DE` is the magic, high word `0x002E` is the header size (46).

```
<store>  <text store>          address comes from Contents u32@0x12
  +0x00  u32   0x002EF0DE      magic | header size (46)
  +0x04  u16   0x012C          format version echo (300)
  +0x06  u16   0x0200          constant
  +0x08  u16   0              constant
  +0x0A  u32   directory offset (== header u32@0x16)
  +0x0E  u32   textBase        == store + 46 (the header size in the magic)
  +0x12  u32   textEnd         end of the character array (start of the story records)
  +0x16  u32   0              constant
  +0x1A  u32   0              constant
  +0x1E  u32[4] pointer array  offsets of up to 4 text-object records; exactly 3 non-zero
  +0x2E  …                     the character array, [textBase, textEnd)
```


The two `u32` at `+0x0E`/`+0x12` and the pointer array at `+0x1E` make the store self-describing. The
section end comes from `Contents u32@0x16`, **not** from the directory offset: the story records sit
between the character array and the first chunk, so the section is larger than the array.

### 13.14.1 Character array

The array is also where table cell structure lives: `0x0F` separates cells, `0x0C`
separates frame blocks (chapter 10 §10.3).


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
| `p98/x` (Quill mode) | 5 | header predicates, page chain, record count, `TEXT` decodability, `FDPP`/`FDPC` ascending positions + range chain + descriptor pool, **every `FDPP`/`FDPC` tag checked against the paragraph/text-run class of §13.17 (205 + 63 tags)**, `STSH`/`FONT` size identity and entry bounds, `STRS` exact consumption, `SYID` size identity, element-array size identity in either payload form (contiguous or packed) + ascending offsets, **`BTEP`/`BTEC` element = `FDPP`/`FDPC` chunk offset and `offsets[]` = the run chain (14 elements, 16 links)**, **`MCLD` full walk + class-18 headers and class-12 records (113 + 226 streams, 5 876 tags)** | 0 violations |
| `p95/x`, `p97/x`, `p97deluxe/x` (text-pool mode) | 488 | store signature `0xF0DE`, header length 46, directory-offset word, `textBase == storeBase + 0x2E`, `textEnd` bounds, NUL-free pool, LF ⊆ CR | 0 violations |

The Quill side covers 62 records and 107 descriptor blobs in the run tables, 339 `MCLD`
streams and the 14-element run index; the 95/97 side covers 488 documents, 487 of which use
the version-correct store base (the exception, `p97/x/INFLNTLB.PUB`, uses the Publisher 95
base and is reported by the scanner rule, not by a constant offset).

## 13.16 Open

| Item | Status | Experiment |
|---|---|---|
| text → shape linkage, the `Contents` half | `[UNKNOWN]` — the stream half is closed (§13.13): `BTEP`/`BTEC` reach the run tables by chunk offset and `TOKN`/`TCD `/`MCLD` agree on the text-object ordinals. What is missing is one fact: which field of the `Contents` shape record stores that ordinal. Excluded so far: `SYID` ids (2 of 3 documents differ from the ordinal set), `FDPP`/`FDPC` ids, and the shape-chunk `id` (always ≥ `0x100`); the only monotone per-shape candidate is the u32 at shape-chunk `+0x14` (`4k+2` ladder in `CHEKLIST.JSP`) | author a document with two text frames whose contents are swapped, save, and diff every `Contents` shape record against the unchanged `MCLD`/`TOKN` ids — the field that moves is the ordinal |
| run-level formatting in the 95/97 pool | `[UNKNOWN]` | author one bold and one underlined paragraph, save, diff the store byte by byte (§13.14.3) |
| `TCD ` offset-array meaning | `[UNKNOWN]` — the framing is closed (§13.10): the chunk is `12 + 4*(count+1)` bytes with `elemSize = 0`, i.e. the offset table *is* the payload (2/2), it is loaded per text object into object slot `0x17` (`FUN_4042278c`) and maintained as an ordered array by `FUN_4040f31b` (VA 0x4040f31b) in lockstep with the object's other per-position arrays. Blocking fact: what the `count+1` ascending u32s index. Excluded: text byte offsets (13 of the 26 values in `CHEKLIST.JSP` `TCD ` id 1 are odd, and a UTF-16LE character boundary is always even) and chunk-relative offsets (`0x3F7` is larger than the 116-byte chunk) | author a 2×2 table whose cells contain text of distinct lengths, save, and test whether the gaps between the values equal those lengths (§13.10) |

## 13.17 The property-field table in `QS98.DLL` (proven)

Every descriptor tag's 11-bit id is resolved through a per-class field table. Three
functions implement the whole mechanism, and their addressing pins the layout:
`FUN_4040d187` (VA 0x4040d187) is the class walker, `FUN_40407184` (VA 0x40407184) maps
`(class, id)` to a 6-byte descriptor, and `FUN_40407248` (VA 0x40407248) is the two-level
page lookup. `[OBSERVED]`

**Class directory.** Two parallel pointer arrays, stride 8, **18 used entries** (class 0 is
all zero, classes `> 0x12` are rejected by `FUN_40407184`):

```
VA 0x40463AD8 + 8*c   u32  pageDir   page directory for class c
VA 0x40463ADC + 8*c   u32  idSet     { u16 *ids; u32 count } for class c
```

`[OBSERVED]` **correction to the previous revision**: the table starts at `0x40463AD8`, not
`0x40463ADC`. Class `c`'s page directory is at `0x40463AD8+8c` and its id set at
`0x40463ADC+8c`; the earlier reading was one dword low, which is why class 0 looked
non-empty and every other class looked shifted. Class 1's id set is at `0x40462F60` with
count 35 — the value the previous revision attributed to "entry 1"'s first pointer.

**Id set** (`idSet`): `{u16 *ids; u32 count}`, count in the low byte of the dword at
`+4` (the walker reads it as one byte, so any class is limited to 255 ids). The `ids[]`
array precedes its header in `.rdata` (the linker packs arrays before headers; e.g. class 1
array at `0x40462F18`, header at `0x40462F60`).

**Page directory**: `{u32 base; u32 tag}` per 512-id page. `tag & 0x1F` is a right-shift
applied to `id & 0x1FF`; `base == 0` means the page is absent (tag `0xFFFF0000`). All 18
classes reach their ids through page 1 (ids `0x200`–`0x3FF`) with shift 0; page 0 is
present but unused except in classes 16/17, which use ids `0`–`2`.

**Descriptor** (6 bytes), at `base + (((id & 0x1FF) >> shift) * 6)`:

```
+0  u8   type    selector, see the type alphabet below
+1  u8   width   bytes to copy from / to the target record
+2  u8   offset  byte offset of the property inside the target record
+3  u8   flag    1 = only read when the caller asks for it (context bits 2/3)
+4  u16  kind    custom accessor index; 0 = the type alphabet is authoritative
```

`[OBSERVED]` the `flag` byte is filtered in `FUN_4040d187` by its `param_5` mask: bit 2
skips every field with `flag != 1`, bit 3 skips every field with `flag == 1`. `kind != 0`
diverts the field to a function table at **VA `0x40469540`**, stride 0xC
(`{apply; compare; diff}`), indexed by `kind`; two are proven: `kind 10` → `FUN_4040d349`
(VA 0x4040d349) which recurses into a nested **class 17** record, and `kind 14` →
`FUN_4040dcad` (VA 0x4040dcad) which walks a count-prefixed array of **class 16**
records with strides 6 and 8.

**Type alphabet** `[OBSERVED]` — the type byte is the on-disk *code* for the scalar cases,
and the setter that emits it is `FUN_404106ff` (VA 0x404106ff):

| sym | type | width use | on-disk code | payload | emitter |
|---|---|---|---|---|---|
| `B` | byte | 1 | 2 | u8 at +2 | `FUN_404196cb` |
| `W` | word | 2 | 3 | u16 at +2 | `FUN_40419676` |
| `D` | dword | 4 | 4 | u32 at +2 | `FUN_40410809` |
| `Q` | 6 of 8 bytes | 6 | 5 | two u32 at +2 | `FUN_4044dc0f` |
| `f` | boolean | 1 | 1 true / 0 false | none | `FUN_40419623` |
| `E` | erase marker | 0 | 0x1D | none | `FUN_40419623` |
| `L` | nested list (0x10) | byte count | 0x10 | `{u32 len; len-4 bytes}` | `FUN_4042355c` |
| `N` | nested list (0x11) | byte count | 0x11 | as `L` | `FUN_404215c8` |

`Q` declares width 6 but its on-disk slot is 8 bytes (the emitter writes two dwords), so a
`Q` field is a 3×u16 triple stored in an 8-byte slot. No `E` field occurs in the corpus.

**The class table** (all 18 classes, `n` = id count; `record >=` is the smallest target
record that holds every declared field):

| class | n | `id type`*`width`*`@record-offset` — `*` = flag 1, `/k` = custom kind | record >= |
|---|---|---|---|
| 1 | 35 | `200 B1@0e*` `202 f1@00` `203 f1@01` `204 f1@03` `205 f1@04` `208 B1@0d` `20c D4@54` `20f B1@0c` `210 f1@05` `211 D4@6c` `212 D4@68` `213 f1@06` `214 f1@07` `215 f1@08` `216 f1@0a` `217 f1@0b` `218 D4@58` `21a D4@5c` `21b D4@60` `21c f1@09` `21d W2@64*` `21e B1@02` `21f W2@80` `220 W2@82` `222 D4@70*` `223 D4@74*` `224 N50@20/10` `229 W2@84` `22a W2@86` `22b W2@88` `22d f1@8a` `22e D4@10` `22f D4@14` `230 D4@18` `231 D4@1c` | 0x8B |
| 2 | 43 | `200 B1@b4` `202 D4@b0` `203 W2@a2` `204 B1@00` `205 D4@20` `206 D4@24` `208 B1@01` `20a f1@04` `20c D4@0c` `20d D4@10/2` `20e D4@14` `212 D4@18` `213 D4@1c` `214 D4@a4` `215 D4@a8` `216 D4@d4` `217 f1@d8` `218 f1@d9` `219 W2@da*/12` `21a B1@dc` `21b f1@dd` `21c f1@de` `21d f1@df` `21e B1@b5` `21f D4@b8` `220 B1@bc` `221 D4@c0` `222 D4@c4` `223 D4@c8` `224 D4@cc` `225 B1@d0` `22a B1@e0` `22c B1@02` `22d B1@03` `230 B1@e1` `231 B1@e2` `232 L122@28/14` `233 B1@e3` `234 D4@06` `235 D4@ac` `236 B1@e4` `237 B1@e5` `239 B1@e6` | 0xE7 |
| 3 | 42 | `200 W2@70` `201 B1@78` `202 B1@79` `203 f1@7a` `204 D4@48` `205 D4@4c` `206 D4@50` `207 D4@54` `208 D4@68` `209 D4@6c` `20a D4@74` `20b D4@00` `20c Q6@04` `20d D4@0c` `20e Q6@10` `20f D4@18` `210 Q6@1c` `211 L12@30` `212 f1@7b` `213 B1@7c` `214 B1@7d` `215 D4@24` `216 Q6@28` `217 f1@7e` `218 D4@44` `219 D4@3c` `21a B1@7f` `21b D4@80` `21c D4@84` `21d D4@88` `21e D4@8c` `21f D4@90` `220 D4@94` `221 D4@98` `222 D4@58` `223 D4@5c` `224 D4@60` `225 D4@64` `226 D4@9c` `227 D4@a0` `228 f1@a4` `229 D4@a8` | 0xAC |
| 4 | 30 | `200 D4@00` `201 D4@04` `202 D4@08` `203 D4@0c` `204 D4@10` `205 D4@14` `206 B1@28` `207 D4@48` `208 W2@1c` `209 f1@29` `20a f1@1e` `20d W2@2a` `212 D4@34` `213 Q6@38` `214 D4@4c` `215 Q6@50` `216 f1@58` `218 B1@59` `219 f1@5a` `21a D4@30` `21b B1@40` `21c D4@18` `21d B1@5b` `21e D4@44/5` `21f W2@2c` `221 D4@20` `222 D4@24` `223 f1@5c` `224 D4@60` `225 f1@1f` | 0x64 |
| 5 | 1 | `200 D4@00` | 0x04 |
| 6 | 2 | `200 W2@00` `201 W2@02` | 0x04 |
| 7 | 3 | `200 D4@00` `201 D4@04` `202 D4@08` | 0x0C |
| 8 | 2 | `200 W2@00` `201 W2@02` | 0x04 |
| 9 | 2 | `200 W2@00` `201 W2@02` | 0x04 |
| 10 | 5 | `200 W2@00` `201 D4@04` `202 D4@08` `203 D4@10` `204 D4@18` | 0x1C |
| 11 | 1 | `200 D4@00` | 0x04 |
| 12 | 25 | `200 D4@04` `201 D4@00` `202 D4@0c` `203 D4@08` `204 D4@10` `205 D4@14` `206 D4@18` `207 D4@1c` `208 D4@20` `209 D4@24` `20a D4@28` `20b W2@2c` `20c f1@2e` `20d D4@38` `20e D4@48` `211 D4@4c` `212 D4@50` `213 B1@54` `214 f1@55` `215 D4@44` `216 D4@30` `217 D4@34` `218 D4@5c` `219 f1@2f` `21a f1@56` | 0x60 |
| 13 | 6 | `200 Q6@00` `201 f1@06` `202 f1@07` `203 D4@0c` `204 D4@10` `205 Q6@14` | 0x1A |
| 14 | 1 | `200 E0@00` | 0x00 |
| 15 | 1 | `200 D4@00` | 0x04 |
| 16 | 3 | `000 D4@00/8` `001 B4@00/9` `002 W2@04` | 0x06 |
| 17 | 2 | `000 W2@00` `001 L255@ff` | 0x02 |
| 18 | 2 | `200 f1@00` `201 D4@04` | 0x08 |

**Class roles, proven** `[OBSERVED]`. A class is selected by the property context the
caller builds (`FUN_4040d102`, VA 0x4040d102, stores the class at `context+0x0C`; the
walker reads it back from there):

| class | role | evidence | corpus identity |
|---|---|---|---|
| 0 | no table at all — a context that only replays pre-built bytes | `0x40463AD8` entry 0 is all zero; the `FDPC` writer (`FUN_40419fe2`, VA 0x40419fe2) initialises it with 0 | 1 writer, 0 lookups |
| 1 | **text-run (character) properties**, carrier `FDPC` | every `FDPC` blob's ids and codes match class 1 | 63/63 tags, 5 chunks, 0 exceptions |
| 2 | **paragraph properties**, carrier `FDPP` | the `FDPP` writer (`FUN_40419d9b`, VA 0x40419d9b) initialises the context with 2 and writes chunk `0x50504446`; every `FDPP` blob matches class 2 | 205/205 tags, 9 chunks, 0 exceptions |
| 5 | **page/section setup**, carrier `SGP ` | the `SGP ` writer (`FUN_4041a897`, VA 0x4041a897) uses class 5 and writes chunk `0x20504753`; class 5 has exactly the one u32 field `0x200` | `SGP ` is the empty stream in 5/5 |
| 12 | **`MCLD` document object record** | type of every tag in every `MCLD` block matches class 12, and the 130-byte serialised size equals the sum of the 25 encoded widths | 226/226 blocks, 5 650/5 650 tags |
| 18 | **`MCLD` object header** | class 18's two fields (`0x200` f, `0x201` D) are exactly the 8-byte leading unit | 113/113 objects |
| 16 | nested element of class 2 id `0x232` (`kind 14` array) | `FUN_4040dcad` walks `count` × class-16 records with strides 6/8 | 25 nested lists in `FDPP` |
| 17 | nested sub-record of class 1 id `0x224` (`kind 10`) | `FUN_4040d349` compares `0x19` class-17 records then re-emits them under id `0x224` | 14 nested lists in `FDPC` |

The corpus also confirms the *discriminating* part of the table, not just membership: for
`FDPP` the observed tag `0x1A19` (code 3, id `0x219`) is exactly class 2's `219 W2@da`,
and for `FDPC` the observed `0x224` (code `0x11`) is exactly class 1's `224 N50@20`.

`[OBSERVED]` an independent size check falls out of the shared applier `FUN_4040e82b`
(VA 0x4040e82b): it builds the target record with `FUN_4040657e` and passes **0x94 bytes
when the class index is 1 and 0xE8 when it is 2**. Those are exactly the two bounds the
class tables impose — class 1's highest field ends at `0x8B`, class 2's at `0xE7` — so the
record sizes 148/232 bytes confirm that the table and the engine agree on the record
layout, and that classes 1 and 2 are the two run-property records (`FDPC`, `FDPP`).

**What remains `[UNKNOWN]`.** The table gives type, width and target offset for all 206
ids, but no *meaning* for any of them. `[OBSERVED]` the descriptor is 6 bytes and its five
fields are fully accounted for, so the table holds no name or symbol pointer: the engine
addresses properties by number alone. Specifically unproven:

* the semantics of every id (which property of the target record each offset is);
* the roles of classes 3, 4, 6–11 and 13–15, which no corpus carrier selects. `STRS` has
  110 entries, 107 of them empty (`totalSize == 4`) and 3 carrying the single field
  `0x200` = u32, so the corpus cannot separate classes 4, 5 and 7 for it;
* whether `L`/`N` field ids exist for shapes other than the two nested cases above.

The one experiment that would settle the largest block: author a document that changes a
single visible property (font size, then alignment, then fill colour), save it, and diff
`FDPP`/`FDPC` — each change moves exactly one id's value, and its class-1 or class-2
record offset then names the property.
