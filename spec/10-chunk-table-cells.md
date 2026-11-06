# 10 — Tables and cell content

**Negative result: the Publisher 95–98 document format has no table record.**
There is no chunk marker for a table, no cell chunk, and no cell-definition
record. `[OBSERVED]` over all 493 documents.

This matters for a re-implementer: the markers that libmspub maps to tables and
cells (`0x0010` TABLE, `0x0063` CELLS, `0x006C` FONT) **occur zero times** in the
entire corpus. Those values belong to the Publisher 2000+ block model
(chapter 12), not to this family.

## 10.1 Evidence

| Marker (libmspub 2000+ name) | Occurrences in 493 documents |
|---|---|
| `0x0010` TABLE | 0 |
| `0x0063` CELLS | 0 |
| `0x006C` FONT | 0 |
| `0x0046` BORDER_ART | 0 |
| `0x005C` PALETTE | 0 (this family uses `0x0047`, chapter 09) |

## 10.2 How a table is actually represented

A table is drawn as ordinary shape records — a set of rectangles (`0x0005`) and lines
(`0x0004`) — plus text-bearing frames on top. There is no structural grouping that
identifies "this is a table"; the only grouping primitive is the GROUP chunk
(`0x000F`, chapter 07), which a writer may or may not use.

Measured examples of grid-like shape sets in the corpus (sibling rectangles with
identical size under one parent):

| Template | Parent | Rects with equal size | Rect size (EMU) |
|---|---|---|---|
| `double1.pub` | `0x0119` | 17 of 39 | 342 900 × 19 050 (a row-rule strip) |
| `CLASSIC.PUB` | `0x02BF` | 27 | 123 825 × 123 825 |
| `JAZZY.PUB` | `0x027F` | 18 | 285 750 × 285 750 |

`[OBSERVED]` geometry; `[INFERENCE]` that such a set is a table — the format carries
nothing that distinguishes a table grid from a decorative grid of rectangles. A reader
that wants to detect tables must use geometry heuristics (equal-size rects sharing edges,
text frames inside the cells).

## 10.3 Cell text

Cell text is ordinary text: a shape carries the text runs described in chapter 13 (or,
for Publisher 95/97, the in-`Contents` text layer). A table cell is therefore "a shape
inside a grid", not a cell record. Row/column spans, borders and fill are the
corresponding shape attributes.

## 10.4 Consequence for writers

A writer that must round-trip a document does not need any table-specific code: it
re-emits the rectangles, lines and text frames. A writer that must *create* a table
emits a grid of rectangles plus text frames, and should group them with `0x000F` for the
user's convenience (optional — grouping has no effect on rendering).

## 10.5 Open

* Whether Publisher 95's "table" UI writes anything additional that this corpus does not
  contain (e.g. a table style record). Experiment: build a table in Publisher 95, save,
  and diff the chunk inventory against a hand-drawn grid. The corpus has no such file.
* The `double1.pub` strip set (342 900 × 19 050 EMU) is the best candidate for a real
  table rule; identifying its text frames would confirm the representation.
