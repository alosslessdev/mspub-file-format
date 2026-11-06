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

Splitting the pool on `0x0C` and each block on `0x0F` finds **255 blocks with four or
more cells in 72 documents, 6 528 cells total**. `[OBSERVED]`

Worked examples (from `notes/p98/slices/tables.md`):

| Document | Table | Evidence |
|---|---|---|
| `pricelst.pub` | 19 × 9 price list | text `[0x2AE, 0x6E9)`, story record at `0x1400` |
| `INVOICE1.PUB` | 13 × 4 invoice | text `[0x26C, 0x3E1)`, story record at `0xE00` |

**Column count** is carried by the shape record that owns the table: a `0x0001`
chunk's counted tail consists of 14-byte records (chapter 06 §6.3), and the leading
run of `0xFFFF`-valued entries gives the column count (9 for the price list, 4 for the
invoice). The cell count then divides exactly by it. `[OBSERVED on both examples;
INFERENCE that the rule generalises]`

Rows are not stored explicitly: a row boundary is a `0x0D 0x0A` at a cell boundary
inside the block. `[INFERENCE]`

## 10.4 Consequence for writers

* **Round-trip**: re-emit the text pool verbatim, including `0x0F`/`0x0C`, plus the
  story records — no table-specific code is needed.
* **Create**: emit the cell text separated by `0x0F`, blocks separated by `0x0C`, and
  set the column count in the owning `0x0001` record's 14-byte tail. Cell borders, fills
  and spans, if drawn at all, are ordinary shapes in the shape layer.
* A reader that wants to *detect* tables uses the separators, not geometry.

## 10.5 Open

* Layout of the 14-byte records in the `0x0001` tail beyond the leading `0xFFFF` run
  (which is the column count).
* Whether a row-level attribute (header row, banding) exists anywhere — no candidate
  field has been found.
* Cell spans/merges: no evidence in the corpus; a merged cell is probably an absent
  cell plus geometry in the shape layer. `[UNKNOWN]`
* The lattice detector is in `tools/p98_tables.py` (`lattice` subcommand) if a future
  corpus contains a real shape-grid table.
