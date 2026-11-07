# 10 — Tables and cell content

**Negative result: the Publisher 95–98 document format has no table record.**
There is no chunk marker for a table, no cell chunk, and no cell-definition
record. `[OBSERVED]` over all 493 documents (43 091 chunks).

This matters for a re-implementer: the markers that libmspub maps to tables and
cells belong to the Publisher 2000+ block model (chapter 12), not to this family.

## 10.1 Markers that do not exist here

| Marker (2000+ name) | Occurrences in 493 documents |
|---|---|
| `0x0010` TABLE | 0 |
| `0x0063` CELLS | 0 |
| `0x0066`, `0x0067`, `0x0068`, `0x0069`, `0x006B`, `0x006D` (table geometry / row-col arrays) | 0 each |
| `0x006C` FONT | 0 |
| `0x0046` BORDER_ART | 0 |
| `0x005C` PALETTE | 0 (this family uses `0x0047`, chapter 09) |

## 10.2 What a table actually is: a text story

A table in this format is **text**, laid out in a story with explicit cell and
frame-block separators. It is not a shape lattice.

The alternative hypothesis — "a table is a grid of rectangle shapes" — was tested
and **not supported**: a full-product lattice detector over the corpus finds only
19 complete lattices, in 5 of 493 documents, all of them children of a GROUP
(`0x000F`); exactly one of those buckets contains any text-bearing child
(`PLAIN.PUB` `0x031E`, a decorative 2×2 title/body box) and **none** has per-cell
text. Real data tables are text stories. `[OBSERVED]`

## 10.3 Cell structure in the text pool

The Publisher 95/97 text pool (chapter 13 §13.14 — the byte range
`Contents[u32@0x12, u32@0x16)`) uses two inline separators:

| Byte | Meaning in the pool |
|---|---|
| `0x0F` | cell separator (advance to the next cell) |
| `0x0C` | frame-block separator (start a new block) |
| `0x0D 0x0A` | paragraph break within a cell |

Splitting the pool on `0x0C` and each block on `0x0F` gives **255 blocks with four or more
split fields in 72 documents (6 528 fields)**. The last field of every such block is the
paragraph break that follows the final `0x0F`, not a cell: after dropping it the 255 blocks
hold **6 273 cells** (exactly one field dropped per block, 255/255). `[OBSERVED]`

Worked examples (from `notes/p98/slices/tables.md`):

| Document | Table | `0x0001` chunk | `A` cols | `B` rows | Evidence |
|---|---|---|---|---|---|
| `pricelst.pub` | 19 × 9 price list | `0x0131` | 9 | 19 | text `[0x2AE, 0x6E9)`, story record at `0x1400` |
| `INVOICE1.PUB` | 13 × 4 invoice | `0x013A` | 4 | 13 | text `[0x26C, 0x3E1)`, story record at `0xE00` |

### 10.3.1 Columns and rows are both stored in the `0x0001` tail

The counted tail of `0x0001` (14-byte records `{u32 a, u32 b, u32 c, u16 d}`, chapter 06
§6.4.1) is **two arrays, not one run**. Two `u16` counts in the fixed part of the record
delimit them:

| Field | Width | Meaning | Evidence |
|---|---|---|---|
| `+0x4A` | u16 | `A`, number of column-stop records | `A + B == N` 259/259 tail-bearing chunks |
| `+0x50` | u16 | `B`, number of row records | `A·B` equals the block's cell count 255/255 |

`N == (size − 106)/14` and `A + B == N` in **259/259** chunks with `N > 0`; those 259 chunks
hold 935 column records and 1 683 row records (2 618 total). The five Publisher 98 `0x0001`
chunks are 114 bytes (the Publisher 98 insertion, chapter 06 §6.3) and carry no 14-byte
tail; Publisher 98 text lives in Quill (chapter 13). `[OBSERVED]`

| Sub-array | Count | Record content | Evidence |
|---|---|---|---|
| records `0 … A−1` | `A` | column stops: `a` is an ascending x within the frame, `d == 0xFFFF` | `d == 0xFFFF` 935/935; `a` non-decreasing and `a[last] ≤ right−left` 259/259 |
| records `A … A+B−1` | `B` | rows: `a` cumulative row bottom, `b` **minimum** row height, `c` **nominal** row extent (`a[i] = a[i−1] + max(b,c)`), `d` selector (chapter 06 §6.4.1) | `a[last] == bottom−top` 259/259; `a` strictly increasing and `0 < a ≤ bottom−top` 259/259 |

* **Column count is `A = u16@+0x4A`, not the length of the first `0xFFFF` run.** That run
  equals `A` in 134/259 chunks and over-counts in 125/259, because it continues into the
  row array whenever row 0 carries `d = 0xFFFF`. `[OBSERVED]`
* **Row count is `B = u16@+0x50`.** For every one of the 255 four-or-more-cell blocks,
  exactly one `(A,B)` pair among the document's `0x0001` chunks satisfies
  `A·B == cell count`; **255/255 blocks** satisfy it and the pair is **unique per block**
  (255/255). The identity also holds for all 259 tail-bearing chunks against some block
  (including 1–3-cell blocks), 259/259. `[OBSERVED]`
* **Row advance.** Over consecutive rows, `Δ = a[i] − a[i−1]` equals `max(b[i], c[i])` in
  1 248/1 424 pairs (50 more within 2 000 EMU); the first row's `a`, measured from the
  frame top, equals `max(b[0], c[0])` in 224/259. The 158 residual advances exceed both,
  and the extra distance is not explained by the record (§10.7). Reading `b` as text
  height and `c` as the nominal line/row metric is `[INFERENCE]`; the relations are
  `[OBSERVED]`.

### 10.3.2 The per-row selector `d`

In the 1 683 row records, `d` takes `0xFFFF` ×1 239, `0` ×333, `1` ×59, `2` ×12, `3` ×36
and `6` ×4. `0xFFFF` is the default/inherit value: the writer seeds it at creation
(`MSPUB.EXE` 95 VA `0x00542a57`, which stores `0xFFFF` at `+0x0C` of every column and row
record it creates, alongside the `0x1BE7C` minimum column width), and the row array is
entirely `0xFFFF` in 107/259 chunks. Every non-`0xFFFF` value is smaller than the element
count (`n = u16@+0x04`) of the document's `0x001A` singleton and of its `0x001C` singleton
in **152/152** chunks that use one, so `d` is consistent with a **document-local index
into one of the story tables**; the run list it is consistent with is mapped in chapter
11 §11.2.1 (26-byte header, `u32[n]` offsets, `n` 10-byte `{chunkId, flag, offset, index}`
slots whose ids resolve to the story's text runs/shapes 4 854/4 854).
`[OBSERVED for the counts, the seeding and the run list]`

No shipped binary reads `d` back: the only stores to a 14-byte record's `+0x0C` in
`MSPUB.EXE` 95 (3 826 functions), 97 (4 252) and 98 (5 360) are the `0xFFFF`/`0` seeds in
the table creators (`0x00542a57`, `0x0054891c`, `0x00549cd8` and their 97/98 builds), and
no function branches on or copies out a saved `d`. Saved non-`0xFFFF` values therefore
arrive with a whole-array copy (the same mechanism chapter 06 §6.4.1 documents for the
row `b` floor), exactly as a persisted style slot behaves. The reader must preserve `d`
verbatim; `0xFFFF` means "default style" and a small value is a style slot whose target
table is not selected by any reader — it is a **write-only selector**. `[OBSERVED for
the seeding and the scan scope; INFERENCE that the slot is style-shaped, supported by the
default/inherit distribution]`

## 10.4 Merges and spans: no encoding

A merged cell would have to make a row shorter than `A` (omitted separators) or carry a
per-cell span value. Neither exists:

* **No short row.** In all 255 four-or-more-cell blocks the cell count is exactly `A·B`
  for the unique `(A,B)` pair above (255/255, zero remainders), so each of the 6 273 cells
  is one of `B` complete rows of `A` cells.
* **No per-cell metadata.** The pool has no record between cells — `0x0F` is the entire
  cell structure — and the row record (chapter 06 §6.4.1 / §10.3.1) is per-row, not
  per-cell.

A "merged" heading such as `pricelst.pub` row 0 (`Category Name` followed by eight empty
cells) is therefore a normal `A`-cell row padded with empty cells; the merge is purely
visual and is reproduced by the empty cells, not by a span attribute. `[OBSERVED]`

## 10.5 Row attributes: exhaustive scan (negative)

Population and method: the 259 tail-bearing `0x0001` chunks are exactly the `0x0001` shapes
of the 72 documents that contain a four-or-more-cell block. Enumerating every byte of those
chunks outside chapter 06's field table (74 offsets: 35 constant corpus-wide, 39 with a
non-constant value set) and every byte of their `0x001D` story records (fully mapped by
chapter 13 §13.14.2) finds no field with the values `{0,1}`, no bit tied to the only
observable row-0 style change, and no array of length `B` outside the row sub-array, so no
header-row or banding flag exists in this record family.

* **No boolean field.** None of the 74 unaccounted chunk bytes, and no `u16`/`u32` at any
  offset within that unaccounted region, takes both values `0` and `1`. The two-valued
  `u16` fields are
  `+0x16` `{0,4}`, `+0x26` `{0,0x81}`, `+0x3E`/`+0x40`/`+0x42`/`+0x44` `{0,0x39}` and
  `+0x48` `{0x0E,0x1E}`; 35 byte offsets are constant and 26 take more than two values. A
  bit-level scan of the same bytes finds no bit that separates the 95 chunks whose row 0
  carries a different selector `d` from the body.
* **No array of length `B` outside the row sub-array.** The `0x0001` size law is exactly
  `106 + 14·N`, with no spare bytes. The story records' `bound[]`/`id[]` arrays have
  `n = 0…13` entries (`n = 1` in 1 246/1 464 records) while `B` reaches 30 in this
  population, so they cannot be per-row.
* **The only per-row storage is the row record**, whose `a`/`b`/`c` are geometry
  (§10.3.1) and whose `d` is the selector of §10.3.2. `d` is not a header flag: `0`
  occurs on non-first rows (`pricelst.pub` rows 0, 7 and 13; `BRCATALG.PUB` rows 6–8) and
  row 0 carries `0xFFFF` in 125/259 chunks. It is not a banding flag: no chunk's row
  sequence is a strict two-value alternation (0/259).

Hence a header row or row banding is not a record flag anywhere in this family; it can
only be a property of the style `d` selects, and `d` is a write-only selector (§10.3.2):
no reader consumes it, so no shipped binary distinguishes a header row from a body row.
`[OBSERVED for the scan; INFERENCE for the style reading]`

## 10.6 Consequence for writers

* **Round-trip**: re-emit the text pool verbatim (including `0x0F`/`0x0C`), the story
  records, and the `0x0001` tail — `A` at `+0x4A`, `B` at `+0x50`, then `A` column records
  and `B` row records. The row records are not derivable from the text (they carry row
  geometry and the selector `d`), so a writer must preserve them rather than regenerate
  them.
* **Create**: emit the cell text separated by `0x0F`, blocks separated by `0x0C`, write
  `A` column stops with `d = 0xFFFF` and `B` row records whose `a` accumulates to the frame
  height, and set the two counts. Cell borders, fills and spans, if drawn at all, are
  ordinary shapes in the shape layer.
* A reader detects a table from the separators and recovers columns/rows from the
  `0x0001` counts, not from geometry.

## 10.7 Row-advance residuals: a frame-level text metric

The 158 advances that exceed `max(b,c)` by more than 2 000 EMU (126 consecutive rows +
32 first rows over the 259 tail-bearing chunks) are **not a row-record field**: the
excess over `max(b,c)` is constant within a frame — over every frame with two or more
non-last residual rows the non-last residuals agree to within 5 EMU (16/16 frames) —
while `d` varies within those same frames, so no per-row field can encode it. The last
row's excess differs because `a[last]` is pinned to the frame height
(`a[last] == bottom−top` 259/259, §10.3.1) and absorbs the frame-fit slack. The constant
is therefore the frame's inter-row paragraph gap, a text metric that lives outside the
row record, exactly as paragraph space-before/after does. A writer preserves the saved
`a` column rather than regenerating it. `[OBSERVED]`

* The lattice detector is in `tools/p98_tables.py` (`lattice` subcommand) if a future
  corpus contains a real shape-grid table.
