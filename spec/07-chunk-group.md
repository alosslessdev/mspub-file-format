# 07 — Group chunk (`0x000F`)

A group is a container shape: it owns a z-ordered list of child chunk ids (shapes and
nested groups) plus its own geometry. 2 935 instances across the 493-document corpus.

## 7.1 Layout

```
+0x00  u16 0x000F        marker
+0x02  u8  A             descriptor (0x18 in 95/97, 0x20 in 98)
+0x03  u8  B             descriptor (equals A)
+0x04  u16 rotation      1/100 degree, counter-clockwise      (same as shapes, ch. 06)
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
groups. 346 groups carry a non-zero rotation; 21 distinct values occur, all in 1/100
degree. [OBSERVED]

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

Children are referenced by directory chunk id, in painting order (first = back). The
directory's `parentId` also links each child to the group, so the graph can be validated
two ways; both agree in every corpus file. A reader must use the **id list**, not the
directory order, to establish z-order.

Nesting: groups inside groups occur; a reader must recurse. Publisher limits nesting for
editing but the format itself has no visible depth field. `[INFERENCE]` for the format; the
corpus is one level deep in most files.

## 7.5 Relationship to PAGE

The PAGE record carries the same id-list header two bytes later (`+0x1A` count, `+0x1C`
duplicate, `+0x1E` element size, ids at `+0x24`) — see chapter 05 §5.3. The two records
share the idiom but not the layout; do not parameterise one parser for both without the
2-byte offset shift.

## 7.6 Validation

`tools/validate.py` checks group id lists by the size rule above (see `page_size_equation`
for pages; groups are covered by the generic extent and ordering checks). Adding a direct
group check is the next validator addition.

## 7.7 Open

* `+0x16` flags word: four values observed (`0x0080`, `0x0000`, `0x0084`, `0x0004`),
  semantics `[UNKNOWN]`.
* Whether the writer ever emits `count != count2` (capacity hint vs used count). Publishing
  uses the equality; a re-implementer should write both equal.
* Group-level fill/line attributes are not present in this record — `[UNKNOWN]` whether
  they exist elsewhere.
