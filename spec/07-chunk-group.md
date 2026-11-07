# 07 — Group chunk (`0x000F`)

A group is a container shape: it owns a z-ordered list of child chunk ids (shapes and
nested groups) plus its own geometry. 2 935 instances across the 493-document corpus.

## 7.1 Layout

```
+0x00  u16 0x000F        marker
+0x02  u8  A             descriptor (0x18 in 95/97, 0x20 in 98)
+0x03  u8  B             descriptor (equals A)
+0x04  u16 rotation      1/10 degree (0.1°), counter-clockwise  (same as shapes, ch. 06)
+0x06  i32 left          EMU                                    (same as shapes, ch. 06)
+0x0A  i32 top
+0x0E  i32 right
+0x12  i32 bottom
+0x16  u16 flags         bit 7: uniform-rotation latch (§7.7); bit 2: bookkeeping copy of transient bit 1 (§7.7); values: 0x0080 ×2155, 0x0000 ×464, 0x0084 ×264, 0x0004 ×43 (95/97; 9/9 P98 groups carry 0x0000)
+0x18  u16 count         child count
+0x1A  u16 count2        equal to count in every conforming record
+0x1C  u16 elementSize   always 2 (the child ids are u16)
+0x1E  u16 0
+0x20  u16 0
+0x22  u16[count]        child chunk ids, in z-order
```

`[OBSERVED]` — Publisher 95 and 97.

The geometry block is identical to the shape block of chapter 06 and satisfies the same
invariants: `left ≤ right`, `top ≤ bottom`, and \|coordinate\| < 400 in in **2 935/2 935**
groups. 346 groups carry a non-zero rotation; the dominant values are 900 (105), 3150 (103),
2700 (36), 1800 (34) and 450 (21) — the 90°/315°/270°/180°/45° snap ladder in tenths of a
degree, consistent with the unit established in chapter 06 §6.2. [OBSERVED]

## 7.2 Size rule

```
size == 0x22 + 2 · count          (Publisher 95 / 97 — 2 926/2 926)
```

The rule holds exactly for every group in the Publisher 95 and 97 corpora; the Publisher 98
records use the shifted layout of §7.3 instead.

## 7.3 Publisher 98 layout

Zero-based offsets shift by `+8`, exactly as for the shape records (chapter 06 §6.3):

```
+0x02  A = 0x20, B = 0x20
+0x20  u16 count
+0x22  u16 count2
+0x24  u16 elementSize (2)
+0x26  u16 0
+0x28  u16 0
+0x2A  u16[count] child ids

size == 0x2A + 2 · count          (Publisher 98 — 9/9)
```

[OBSERVED] on the five Publisher 98 publications (9 groups).

## 7.4 Child resolution and z-order

Children are referenced by directory chunk id, in painting order (first = back). `[OBSERVED]`
in **2 935/2 935** groups the id array at `+0x22` (95/97) or `+0x2A` (98) is exactly the
directory's children of that group sorted by ascending `chunkOffset`, and every referenced
id resolves. So the two representations agree everywhere in the corpus, but the array is
the authoritative z-order: the directory only says *membership*.

Nesting: groups inside groups occur at every depth up to 5. `[OBSERVED]` depth histogram
(depth = number of enclosing groups) over the 2 935 groups:

| depth | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| groups | 563 | 1 012 | 715 | 513 | 99 | 24 |

The format has no visible depth field; a reader must recurse on the id list and guard
against cycles (the corpus has none).

## 7.4.1 Group rectangle is stored, not derived

`[OBSERVED]` the group's own `(l, t, r, b)` is an independent authored rectangle, not the
union of its children:

| relation | leaf groups | groups containing a group |
|---|---|---|
| all children inside the group box | 1 600 | 668 |
| some children inside | 157 | 78 |
| no child inside | 280 | 4 |
| group box == exact union of children | 1 365 / 2 037 | 643 / 750 |
| group box == all-zero (degenerate) | — | 139 |

Consequences for a reader: (a) do **not** recompute the group box from children — a
recomputation changes the document; (b) do **not** apply the group box as a transform to
child coordinates — children are stored in the same absolute page frame as the group
(the 1 600 all-inside cases confirm this; a nested transform would put them outside).
Transform composition is therefore the **identity**: a group contributes z-order, a clip
rectangle and its own rotation, not a coordinate offset.

## 7.5 Relationship to PAGE

The PAGE record carries the same id-list header two bytes later (`+0x1A` count, `+0x1C`
duplicate, `+0x1E` element size, ids at `+0x24`) — see chapter 05 §5.3. The two records
share the idiom but not the layout; do not parameterise one parser for both without the
2-byte offset shift.

## 7.6 Validation

`tools/validate.py` runs three direct group checks over all 493 documents:

| Check | Assertion | Result |
|---|---|---|
| `group_size_equation` | `size == 0x22 + 2·count` (95/97) / `0x2A + 2·count` (98) | 0 violations |
| `group_count_pair` | `u16@+0x18 == u16@+0x1A` (`+0x20`/`+0x22` in 98) | 0 violations |
| `group_bbox_ordered` | `l ≤ r`, `t ≤ b` | 0 violations |

The size rule was re-measured independently here: 2 935/2 935 groups satisfy it, and the
`+8`-shifted Publisher 98 form holds for 9/9 groups in the five 98 publications.

## 7.7 Flags and group-level attributes (closed)

* `+0x16` flags word — closed. Only bits 2 and 7 are ever set in the 95/97 corpus
  (`0x0080` ×2155, `0x0000` ×464, `0x0084` ×264, `0x0004` ×43 = 2 926/2 926; the 9/9
  Publisher 98 groups carry `0x0000` at the shifted offset `+0x1E`): bit 7 is the
  uniform-rotation latch, bit 2 the transient-bit-1 bookkeeping copy.
  Writer: the Publisher 95 group writer `FUN_004E8CA7` (VA `0x004E8CA7`) walks the
  group's children, skipping marker `0x0004` (lines never rotate — 0/2 774 corpus lines
  carry a non-zero rotation), latches the first rotatable child's rotation and clears a
  uniformity flag on any mismatch, and clears a nesting flag on any nested `0x000F`
  child lacking bit 7; it sets `0x0080` iff both flags survive, else clears it — and it
  unconditionally overwrites the group's own `+0x04` rotation with the latched child
  rotation (0 when no rotatable child exists or they disagree). Corpus consequence is
  one-directional and exact: bit 7 set ⇒ children uniform and every nested group
  carries bit 7 (2 419/2 419, 0 violations; nesting part 518/518), while 76 groups in
  12 template/gallery files (`PLAIN.PUB` 21, `CLASSIC.PUB` 18, `JAZZY.PUB` 11, …) are
  uniform yet clear — the latch records that the writer ran and found uniformity, not a
  standing invariant a reader may assume. `0x0084` is the combination (both bits set),
  `0x0004` bit 2 alone. Bit 2 is the shape bit-1-sync copy (chapter 06 §6.7.6: writer
  `0x00416C82`, 98 twins `0x00492A72`/`0x00502369`); no located code path reads it back.
  A reader MUST preserve both bits verbatim and MUST NOT recompute the latch (the 76
  clear-but-uniform groups prove recomputation changes the document).
  `[OBSERVED, binary]`
* Whether the writer ever emits `count != count2` (capacity hint vs used count). Publishing
  uses the equality; a re-implementer should write both equal.
* Group-level fill/line attributes — closed as **absent by construction**. The 34-byte
  fixed header leaves no room: the shape colour offsets (`+0x18`/`+0x1C` pair,
  `+0x20` selector, `+0x23` pen) fall inside the group's rotation/bbox/flags/count
  words, and the record is exactly `0x22 + 2·count` (2 926/2 926) with the id array
  starting at `+0x22`. Nor does any other record carry them: a corpus census over all
  2 935 groups (2 926 in 95/97, 9 in 98) shows every child id resolves to a shape
  (`0x0000`–`0x0008`, 98 also `0x0005`/`0x0008`) or a nested group — zero children of
  any other type, zero dangling ids — so a group's visible fill/line is exactly the
  member shapes' own attributes (chapter 06 §6.7); there is no group-level slot to
  find. Scan scope as chapter 06 §6.7.6 (3 EXEs + `PUBDLG`/`PUBOLE32`/`MSPUBW32` 95 +
  `QS98`). A reader draws each member with its own attributes and preserves the
  header bytes verbatim. `[OBSERVED, negative]`
