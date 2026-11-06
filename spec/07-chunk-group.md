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
+0x16  u16 flags         values: 0x0080 ×2163, 0x0000 ×464, 0x0084 ×265, 0x0004 ×43 [UNKNOWN]
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

## 7.7 Open

* `+0x16` flags word: four values observed (`0x0080`, `0x0000`, `0x0084`, `0x0004`),
  semantics `[UNKNOWN]`.
* Whether the writer ever emits `count != count2` (capacity hint vs used count). Publishing
  uses the equality; a re-implementer should write both equal.
* Group-level fill/line attributes are not present in this record — `[UNKNOWN]` whether
  they exist elsewhere.
