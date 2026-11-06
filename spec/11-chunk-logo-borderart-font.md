# 11 — Document-level records: fonts, logo/design, border art, print setup

Most of a document's non-geometric data lives in **singleton records**: one chunk per
document (or a small fixed number), referenced by id from the DOCUMENT chunk. This
chapter documents their framing, size rules and the payloads that are understood.

All rules below were re-measured over the Publisher 95 corpus (130 documents) and, where
stated, over the whole 493-document corpus. Counts are stated per rule.

## 11.1 DOCUMENT slot map

The DOCUMENT chunk (`0x0015`) holds the ids of its singletons at fixed offsets. `0` means
the record is absent. Every non-zero value resolves to a chunk of the stated type
(130/130 per slot). [OBSERVED]

| Offset | Marker | Record | Present |
|---|---|---|---|
| `+0x04` | `0x0029` | print setup (DEVMODE/DEVNAMES) | 130/130 |
| `+0x06` | `0x0028` | paper/print parameter block | 130/130 |
| `+0x08` | `0x0014` | first page | 130/130 |
| `+0x46` | `0x0023` | fixed 4-slot table | 130/130 |
| `+0x48` | `0x0031` | design/object set #1 | 130/130 |
| `+0x4A` | `0x001E` | **font table** | 130/130 |
| `+0x4C` | `0x001F` | **line/border-art style table** | 130/130 |
| `+0x4E` | `0x0016` | story container | 130/130 |
| `+0x50` | `0x002A` | font-substitution table | 130/130 |
| `+0x52` | `0x002B` | document name list | 30/130 |
| `+0x54` | `0x0026` | paragraph-style names | 130/130 |
| `+0x56` | `0x0031` | design/object set #2 | 130/130 |
| `+0x58` | `0x0031` | design/object set #3 | 130/130 |
| `+0x5A` | `0x0034` | 14-byte sub-table | 70/130 |
| `+0x5C` | `0x0035` | DLL binding record | 74/130 |
| `+0x5E` | `0x0037` | colour list, 6-byte elements | 16/130 |
| `+0x60` | `0x0038` | colour list, 10-byte elements | 15/130 |
| `+0x68` | `0x0039` | 48-byte document record | 130/130 |

The three `0x0031` slots always name distinct chunks.

### 11.1.1 Slots that change meaning between generations

Measured over 487 documents (128 `p95`, 106 `p97`, 248 `p97deluxe`, 5 `p98`). Two slots in
the block above and one below it do **not** keep their meaning, so a reader must dispatch
on version rather than assume the P95 table: [OBSERVED]

| Offset | P95 | P97 / P97D | P98 |
|---|---|---|---|
| `+0x4E` | `0x0016` story container, 128/128 | `0x0016`, 354/354 | `0`, 5/5 — the P98 publications have no story container at all |
| `+0x6A` | **not an id**: the last-page index (`Npages − 1`) | `0x0031`, a **fourth** design set, 247/248 | `0x0045`, 5/5 |
| `+0x6E` | not an id (constant `2`) | `0` | `0x0047` **PALETTE**, 5/5 |

`+0x6E` is the palette reference introduced with Publisher 98 (chapter 09 §9.3) and is the
one document-level singleton whose slot sits outside the `0x46…0x68` block. The Publisher 98
DOCUMENT record is 72 bytes longer than the 95 one (chapter 04 §4.1), and these three slots
account for the re-purposing that came with that growth.

## 11.2 Story container `0x0016`

```
+0x00 u16 0x0016
+0x02 u8  0x1A              A
+0x03 u8  0x10              B
+0x04 u16 styleId           a style id, NOT a chunk id
+0x06 u16 0
+0x08 u16 id of the 0x001A chunk
+0x0A u16 id of the 0x001C chunk
+0x0C u16 id of the 0x002E chunk
+0x0E u16 id of the 0x002D chunk
```

Fixed 16 bytes (130/130). Slot order is `1A, 1C, 2E, 2D` — not ascending marker order.
`+0x04` resolves to a live chunk in only 8 documents, so it must not be resolved as an
id. [OBSERVED for the layout; INFERENCE for the style-id reading]

## 11.3 Container header

`0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x002A`, `0x002B`, `0x0032`, `0x0034`, `0x0037`,
`0x0038` (and `0x001A`/`0x001C` with a per-type element size) share one header:

```
+0x00 u16 marker
+0x02 u8  A           structural landmark (see 11.9)
+0x03 u8  B           constant per type
+0x04 u16 nEntries
+0x06 u16 nEntries    duplicate
+0x08 u16 endOffset   == size - 0x0E      (offset-table flavour)
        u16 elementSize                   (fixed-element flavour)
+0x0A u16 format      0 / 1 / 5
+0x0C u16 0xFFFF      sentinel
+0x0E ...             offsets relative to chunk+0x0E (0xFFFF = empty), then payload
```

Two flavours:

* **Offset table** — element `k` runs from `chunk+0x0E+off[k]` to the next offset (or to
  `size`). Used by `0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x002A`, `0x002B`, `0x0032`.
* **Fixed element** — payload is `n × elementSize` bytes at `+0x0E`, so
  `size == 0x0E + elementSize·n`. Used by `0x0037` (6), `0x0038` (10), `0x001A` (14),
  `0x001C`/`0x002D`/`0x002E` (8).

**Publisher 97 widens the offset entries from `u16` to `u32`** and doubles the `A` byte
accordingly (e.g. `0x001F`: `A` 0x04 → 0x08). A reader must key the container parse on the
chunk's own `A` byte, not on the marker alone. [OBSERVED]

## 11.4 Size rules

`n` is `u16@+0x04` unless stated. Every rule is exact over the stated population.

| Marker | Rule | Result |
|---|---|---|
| `0x0016` | `size == 16` | 130/130 |
| `0x001A` | `size == 26 + 14·n` | 130/130 |
| `0x001C` | `size == 26 + 8·n` | 130/130 |
| `0x002D` | `size == 26 + 8·n` | 130/130 |
| `0x002E` | `size == 26` | 130/130 |
| `0x001E` | `u16@+0x08 == size − 0x0E` (n at `+0x04` duplicated at `+0x06`) | 130/130 |
| `0x001F` | same | 130/130 |
| `0x0023` | same | 130/130 |
| `0x0026` | same | 130/130 |
| `0x002A` | same | 130/130 |
| `0x002B` | same | 30/30 |
| `0x0032` | same | 390/390 |
| `0x0028` | `size == 26 + 5·u16@+0x10` | 130/130 |
| `0x0029` | `u16@+0x30 == size − 54` | 130/130 |
| `0x0031` | `size == 30 + 8·u16@+0x08` | 390/390 |
| `0x0034` | `size == 46 + 14·u16@+0x24` | 70/70 |
| `0x0035` | `size == 200` | 74/74 |
| `0x0036` | `size == 112` | 1/1 |
| `0x0037` | `size == 14 + 6·n` | 16/16 |
| `0x0038` | `size == 14 + 10·n` | 15/15 |
| `0x0039` | `size == 48` (95/97), 56 (98) | 488/488, 5/5 |
| `0x0027` | `size == 42` | 14/14 |

## 11.5 Font table `0x001E`

One per document, referenced from `DOCUMENT+0x4A`. The record is an **offset-table
container** whose widths change between generations, so a reader must detect the form by
exact fit rather than by version. Three forms occur; all 487 font tables in the corpus
parse under exactly one of them (487/487, no leftovers): [OBSERVED]

| Form | Corpora | Counts | End offset | Offsets | Name encoding |
|---|---|---|---|---|---|
| V95 | all 128 `p95`, 1 `p97` | `u16` at `+0x04`, dup `+0x06` | `u16` at `+0x08` == `size − 0x0E` | `u16[count+1]` at `+0x0E`, relative to `+0x0E`, first = `2·(count+1)` | ASCII, NUL-terminated |
| V32 | 105 `p97`, 248 `p97deluxe`, 5 `p98` | `u32` at `+0x04`, dup `+0x08` | `u32` at `+0x0C` == `size − 0x16` | `u32[count+1]` at `+0x16`, relative to `+0x16`, first = `4·(count+1)` | ASCII, NUL-terminated |
| V32U | the same 5 `p98` documents | as V32 | as V32 | as V32 | **UTF-16LE**, NUL-terminated (2 bytes) |

V95 also carries `u16 1` at `+0x0A` and `u16 0xFFFF` at `+0x0C`; V32 carries `u16 1` at
`+0x10` and `u32 0xFFFFFFFF` at `+0x12`. Those two constants are the cheapest form
discriminator after the length fields.

Each entry is `{u8 charset, u8 lfPitchAndFamily, name}` — two prefix bytes, no length byte.
Entry *k* runs from `base + off[k]` to `base + off[k+1]`, so contiguity is
`off[k+1] == off[k] + 2 + len(name) + 1` (ASCII) or `+ 2` (UTF-16). Measured: 7 456 entries,
270 distinct faces over the 487 documents.

* `charset` ∈ {`0x00` ANSI, `0x01` DEFAULT, `0x02` SYMBOL, `0xFF`} in 95/97, matching the
  face (`Symbol` and `Wingdings` are `0x02`).
* `lfPitchAndFamily`: low 2 bits pitch, bits 4–6 family — `0x10` ROMAN for `Times New
  Roman`, `0x20` SWISS for `Arial`, `0x30` MODERN for `Courier`, `0x40` SCRIPT for
  `Comic Book`, `0x50` DECORATIVE for `Wingdings`. Bits 2–3 and bit 7 vary between
  documents for the same face and are **not** fields.
* **Publisher 98 caveat:** the first prefix byte is not the charset there — `Times New
  Roman` carries `0xCC`, while `Symbol` still carries `0x02`. The 98 encoding of the pair is
  `[UNKNOWN]`; only the 95/97 reading above is established.

Correction to the earlier statement that the table has "no length byte" and a fixed
stride: the stride is `2 + strlen + 1`, and the Publisher 97/98 tables widen every offset
to 32 bits, which is why a fixed-stride walk fails on those corpora.

## 11.6 Border art: `0x001F` and the `.BDR` library

One `0x001F` per document. 81 of 130 Publisher 95 documents carry the empty 16-byte form;
the rest carry **named border-art styles**. The marker `0x0046` BORDER_ART of the 2000+
block model does not exist here. The earlier statement that the entry prefix "is 2 or 4
bytes, discriminator unknown" is superseded: the entry has a fixed layout. [OBSERVED]

### The `0x001F` entry

```
+0x00  u16      1                 constant in 115/115 populated entries
+0x02  char[42] nameSlot          NUL-terminated ASCII name; bytes after the NUL are
                                  stale text from a previous longer name
+0x2C  u16      bandTwips         border band width, twips (80, 120, 200, 240, 480, 720 …)
+0x2E  u16      edgeWidthTwips    edge-tile width
+0x30  u16      edgeHeightTwips   edge-tile height
+0x32  u16[8]   tileOffset        byte offsets of the 8 tiles, relative to the entry start
+0x42  …                          the tiles, each a standard memory WMF
```

Verified over the whole corpus: **115 populated entries, 920 tiles, 920/920 tiles begin
`01 00 09 00 00 03`** (a `METAHEADER`, type 1, header 9 words, version `0x0300`). Twenty
further entries live in `0x001F` chunks whose entry table parses under neither width form
(e.g. `BRCATALG.PUB`, whose first entry is a `u16` id list); those remain `[UNKNOWN]`. The
eight slots are the border sides **clockwise from the top-left**: TL, top, TR, right, BR,
bottom, BL, left; the offsets are **not** monotonic and the same tile is often shared by two
slots, so a reader must take each tile's extent from its own WMF header, never from the gap
to the next offset. [OBSERVED]

Worked example — `p97/x/PAGEWIZ/AWARD.PUB` `0x001F` id `0x1212`: name `Chain Link`,
`band = 120`, tile offsets `(642, 1214, 1214, 1782, 2354, 2926, 3506, …)`, the top/TR pair
sharing offset 1214.

### The `PUBBRD/*.BDR` library

The 15 catalogue files on the CD use a different, much simpler container:

```
+0x00  u16  magic     0x5458 ('X','T')
+0x02  u16  version   1   (all 61 copies across the four CDs)
+0x04  u16  count N
+0x06  char[42][N]    name slots, NUL-terminated, stale text after the NUL
+0x06+42N       N × 22-byte records: bandTwips, edgeWidthTwips, edgeHeightTwips, u16[8]
+0x06+42N+22N   22-byte terminator
+…              the payload tiles, concatenated with no gaps
```

`size == 6 + 42·N + 22·(N+1) + Σpayload` holds for 61/61 files; the 22-byte record's
offsets are relative to the record itself, and every payload is a memory WMF (zero
placeable-WMF or BMP payloads in the whole set). [OBSERVED]

**Documents embed, they do not reference.** Of 527 `0x0021` IMAGE_DATA bodies, **zero** are
byte-identical to any `.BDR` payload; but 118 documents carry byte-identical border-art
tiles inside their `0x001F` chunk (900 occurrences, 38 distinct styles), each stored as
name + original `BORDERS\*.BDR` path + a private copy of the tiles. A reader therefore never
needs the CD library to render a document, and a `.BDR` file is a catalogue for the UI, not
a resource the document points at. [OBSERVED]

## 11.7 Design / object sets `0x0031` and `0x0032`

`0x0031` is a direct child of the DOCUMENT and is referenced from `+0x48`, `+0x56` and
`+0x58` (three per document in 487/487). A further 342 documents carry a **fourth**
`0x0031` that has no `0x0032` child and is not referenced from those slots; 1 461 of the
1 803 instances are the parent of exactly one `0x0032`. [OBSERVED]

### `0x0031` payload

```
+0x00  u16  0x0031
+0x02  u16  0x0808        stamp (fixed-part length B = 8)
+0x04  u16  0
+0x06  u16  child32Id     id of the 0x0032 child — 1461/1461 of the parents
+0x08  u16  count
+0x0A  u16  count         duplicate
+0x0C  u16  4             element size of each array
+0x0E  u16  arrayOffset   0 in the 30-byte form
+0x10  u32  0
+0x14  u32  0
+0x18  u16  0
+0x1A  u32  0x7FFFFFFF    sentinel
+0x1E  u32[count]         array A: chunk ids, last element 0x7FFFFFFF
+0x1E+4·count  u16[count]{id, value}   array B
```

`size == 30 + 8·count` (1 803/1 803), because the two arrays are `4·count` bytes each.
Array A is a list of the design's object chunk ids; its last element is `0x7FFFFFFF` in all
52 non-empty instances, and the ids it names are `0x000F` GROUP (1 187), `0x0005` RECT
(153), `0x0001` (144), `0x0003` (97), `0x0002` (65), `0x0006` (60), `0x0007` (24),
`0x0000` (16), `0x0004` (3). Array B is a list of `{u16 id, u16 value}` pairs over a
different id set (all types occur); the value domain observed is 0…45 and its meaning is
`[UNKNOWN]`. [OBSERVED for the framing and the id sets; UNKNOWN for B's semantics]

Worked example — `p95/x/PAGEWIZ/CLASSIC.PUB` id `0x0105`, 446 bytes, count 52:

```
+0x06 = 0x0106   the 0x0032 child
+0x1E = 0x010A 0x0115 0x0123 0x012B 0x013F … 0x0727 0x7FFFFFFF
```

### `0x0032` payload — the name table

Same container family as §11.3, with the same two width forms:

| Form | Counts | End offset | Offsets | Entries |
|---|---|---|---|---|
| L1 (u16) | `u16` at `+0x04`, dup `+0x06` | `u16` at `+0x08` == `size − 0x0E` | `u16[count+1]` at `+0x0E`, first = `2·(count+1)` | ASCII names |
| L2 (u32) | `u32` at `+0x04`, dup `+0x08` | `u32` at `+0x0C` == `size − 0x16` | `u32[count+1]` at `+0x16`, first = `4·(count+1)` | ASCII names |

Measured: 387 L1 (all in `p95` plus 3 `p97`), 1 070 L2 (all `p97`/`p97deluxe`/`p98`), and
4 L2 instances in `p97/x/PAGEWIZ/JAZZY.PUB` and `PLAIN.PUB` whose offset array is
non-monotone (`offs[0] = 5`) — an unexplained writer variant, `[UNKNOWN]`. 1 455 names
total. The names are the design's object names (`Titles`, `Corner`, `Pinstripes`,
`Table of Contents`, …), and `count` matches the `0x0031` count that owns them.

Worked example — `p95/x/PAGEWIZ/CLASSIC.PUB` id `0x0106`, 589 bytes, count 52, L1:
`+0x08 = 0x023F = 575 = 589 − 14`, offsets `0x6A, 0x70, 0x77, … 0x023F`, first string at
`+0x0E + 0x6A = 0x78` = `"Title\0"`, next at `0x7E` = `"Column\0"`.

The three slots correspond to the three design sets every Publisher template is built on;
the naming is `[INFERENCE]`, the structure is `[OBSERVED]`.

## 11.8 Print setup records `0x0028`, `0x0029`, `0x0036`

* `0x0028` — paper/print parameter block. Six fixed application codes
  (`0x14B7, 0x18B7, 0x14A8, 0x14DE, 0x14E0, 0x142A`, i.e. 5303/6327/5288/5342/5344/5162)
  in every document, then `n = (size−26)/5` five-byte records `{u16 code, u16 value, u8 0}`.
  The codes exceed the chunk-id space, so they are application constants, not references.
* `0x0029` — print setup. Four EMU margins at `+0x16`, page width/height at `+0x48`/`+0x4C`
  (equal to the DOCUMENT's, 130/130), DEVMODE `dmPaperSize` at `+0x50`, then device, driver
  and port as NUL-terminated strings whose cumulative ends are the four `u16` at
  `+0x3E…+0x44`. Contains **no timestamps**.
* `0x0036` — a fixed 112-byte print-setup companion, one instance in the entire corpus
  (`CHEKLIST.JSP`), byte-identical across all four CD revisions. Fields `[UNKNOWN]`.

## 11.9 The `A` byte

`A` is a structural landmark, not a length. It equals the byte offset of the record's
primary count field in 15 of 21 container types (`0x001A`/`0x001C`/`0x001F`/`0x0023`/
`0x0026`/`0x002A`/`0x002B`/`0x002D`/`0x002E`/`0x0032`/`0x0037`/`0x0038` → 4; `0x0031` → 8;
`0x0028` → 0x10; `0x0034` → 0x24). Exceptions: `0x001E` (A = 8, count at `+0x04`), `0x002C`
(A = 0x18, counts at `+0x14`), `0x0029` (A = 0x2C, no count), `0x0027` (A = 0x16, a string
offset), `0x0035` (A = 0xC8, the chunk size), `0x0039` (A = 0x4C). [OBSERVED]

## 11.10 Colour lists `0x0037` / `0x0038`

`0x0037` (16 documents) uses 6-byte elements: `RR GG BB 20 flag`. The triple is unambiguous;
the `0x20` tag byte is the literal-RGB tag of chapter 09, and the trailing flag takes
{0,1,2,8,9,0x18}. `[INFERENCE]`: a document-level custom-colour list. `0x0038` (15
documents) declares 10-byte elements, but the corpus contains **no populated instance**, so
its element layout is `[UNKNOWN]`.

Population measured over all 487 documents: `0x0037` — 183 instances, count 0 in 129, 1 in
48, 2 in 5, 5 in 1, always `size == 14 + 6·count`; `0x0038` — 127 instances, **all 14 bytes
with count 0**. So the 10-byte element form exists in the writer but is never exercised by
any shipped publication: closing it needs an authored document with a custom colour, not
more corpus. [OBSERVED]

## 11.11 Publisher-98-only document records

Six markers occur in the Publisher 98 publications and nowhere else. All six are now
framed; the remaining unknowns are field semantics, listed in §11.13. All are direct
children of the DOCUMENT except `0x004C`/`0x0052`, which hang off `0x0045`. [OBSERVED, 5 documents]

| Marker | Size | Layout |
|---|---|---|
| `0x0040` | 28, fixed | `u16 0x0202` at `+0x04`, zeros elsewhere; 4 instances, byte-identical |
| `0x0041` | 40, fixed | **a page slot**, not a distinct feature — see below |
| `0x0045` | 8, fixed | `u16 id of the 0x004C chunk` at `+0x04`, `u16 id of the 0x0052 chunk` at `+0x06`; 5/5 |
| `0x0043` | 20 + 2·N | `N` at `+0x0A`, duplicate `+0x0C`; `N` `u16` chunk ids from `+0x14`. The ids are the top-level objects of every page except the first (the shape-gallery page), excluding `0x002C` — set-equal 5/5 |
| `0x004C` | 40 + 6·N | `N` at `+0x12`, duplicate `+0x14`; `N` `u32` 16.16 values at `+0x24`, sentinel `0x7FFFFFFF` at `+0x24+4N` (10/10 across both markers), then `N` `u16` ids at `+0x28+4N` — **109/109 ids resolve** to real chunks. Maps an id to a shape; the values equal the `u32` at `0x0008+0x58` |
| `0x0052` | 40 + 34·N | `N` at `+0x12`, duplicate `+0x14`; `N` `u32` keys, the same `0x7FFFFFFF` sentinel, then `N` × 30-byte records (the keys are a superset of the `0x004C` value array, 5/5) |

### `0x0041` is a page slot

`0x0041` is byte-identical to a 40-byte Publisher 98 PAGE (`0x0014`) except for two fields:

```
PAGE 0x14:  14 00 1e 1e 00 00 00 00 00 00 00 00 e0 d0 5c 01 e0 d0 5c 01 …
0x41:       41 00 1e 1e 00 00 00 00 00 00 00 00 e0 d0 5c 01 e0 d0 5c 01 …
                                            +0x22:  02 00 (PAGE)  /  08 00 (slot)
```

So `0x0041` is a page record whose `+0x22` slot kind is `8` instead of `2`. It carries the
same 40-byte framing (`B = 0x1E`, count at `+0x1E`, duplicate `+0x20`, array at `+0x28`).
The document's page count therefore includes `0x0041` records: `p98/x/MSPUB.PUB` has six
`0x0014` and one `0x0041`, which is the seven pages that make the DOCUMENT size rule of
chapter 04 §4.1 balance. [OBSERVED]

The 40-byte PAGE form, for reference:

| Offset | Width | Field | Observed |
|---|---|---|---|
| `+0x00` | u16 | marker | `0x0014` or `0x0041` |
| `+0x02` | u16 | stamp | `0x1E1E` |
| `+0x04` | u32 | 0 | — |
| `+0x08` | u32 | 0 | — |
| `+0x0C` | u32 | build stamp | `0x015CD0E0` in 4 of 5 publications, different in `ZMSPUB.PUB` |
| `+0x10` | u32 | same as `+0x0C` | — |
| `+0x14` | u32 | 0 | — |
| `+0x18` | u32 | 0 | — |
| `+0x1C` | u16 | 0 | — |
| `+0x1E` | u16 | count | page-child count |
| `+0x20` | u16 | count | duplicate |
| `+0x22` | u16 | slot kind | `2` = page, `8` = page slot |
| `+0x24` | u32 | 0 | — |
| `+0x28` | u16[count] | child ids | — |

## 11.12 Publisher 97-era records

Four markers occur in the Publisher 97 corpora and in neither 95 nor 98. All have exact
size rules; the interiors of three are `[UNKNOWN]`. [OBSERVED]

| Marker | Instances | Size | Parent | Framing |
|---|---|---|---|---|
| `0x002F` | 12 | 38, fixed | `0x0016` story container | `+0x04 u16 0x0002`, `+0x06 u16 0x021A`, `+0x08 u16 1`, `+0x0A u16 1`, `+0x0C u16 4`, `+0x1E u16 0x1E95`, `+0x22 u16 0xFFFF`; interior `[UNKNOWN]` |
| `0x003A` | 342 | 26 … 1 014 | `0x0031` design set | the 26-byte empty form is the u32 container (count 0 at `+0x04`, duplicate `+0x08`, end offset `size − 0x16` at `+0x0C`, `u32 4` at `+0x16`) in 330/330; the 12 populated instances (304…1 014 B) do **not** follow that rule — `[UNKNOWN]` |
| `0x003B` | 12 | 26, fixed | `0x002F` | byte-identical empty u32 container, 12/12 |
| `0x003F` | 35 | 180, fixed | `0x0015` document | `+0x04 u32 1`, `+0x08 u32 1`, two 32-bit stamps at `+0x10`/`+0x14`, then a NUL-terminated name (`"Every L7160,"…`); interior `[UNKNOWN]` |

The 26-byte empty form shared by `0x003A`/`0x003B` is the same container shape as the
`0x0032` L2 form (§11.7) — count, duplicate, end offset, `u16 1`, `u32 0xFFFFFFFF`, one
`u32` offset — which is why the pair is grouped here rather than with the fixed records.

## 11.13 Open

| Item | Status | Experiment |
|---|---|---|
| `0x0028` six application codes | `[UNKNOWN]` | look the constants up as a table in `MSPUB.EXE` |
| `0x001A` 14-byte element field order | `[UNKNOWN]` | save a document that adds one paragraph |
| `0x0016 +0x04` style id | `[INFERENCE]` | resolve against `0x0026`/`0x001F` entry order |
| `0x0036` fields | `[UNKNOWN]` | single instance; needs a document exercising print setup |
| `0x0038` element layout | `[UNKNOWN]` and **not reachable from the corpus** — 127/127 instances are the empty 14-byte form | author a document that uses the 10-byte colour form |
| `0x0031` array B (`{u16 id, u16 value}` pairs) | `[UNKNOWN]` semantics; framing proven (1 803/1 803) | correlate the value with the object's page or z-order |
| `0x0031` fourth instance (342 documents) | `[UNKNOWN]` role — no `0x0032` child, not referenced from `+0x48/+0x56/+0x58` | diff a document before and after adding a user design |
| `0x0032` non-monotone offset variant | `[UNKNOWN]` — 4 instances in `p97/x/PAGEWIZ/{JAZZY,PLAIN}.PUB` with `offs[0] = 5` | diff a save that adds one object name |
| Publisher 98 font prefix byte | `[UNKNOWN]` — `0xCC` for `Times New Roman` where 95/97 write `0x00` | needs a P98 document authored outside the CD samples |
| `0x0052` 30-byte record semantics | `[UNKNOWN]` — each record starts `u32 1`, the key, two per-document pointer-like `u32`s, a `u16` in {16, 64, 80}, then `0xCB18967C` (= f32 −9 999 996.0) twice and f32 18.0/0.0 | needs a P98 document with more than one text frame |
| `0x004E` / `0x004F` / `0x0050` framing | `[UNKNOWN]` — 2 instances each (290 B, 207/306 B, 110/155 B), all under a `0x000A` shape in `CHEKLIST.JSP` | same |
