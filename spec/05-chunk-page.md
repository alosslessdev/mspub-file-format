# 05 — PAGE chunk (`typeMarker 0x0014`)

One PAGE chunk per page. 712 instances in the 128-file corpus; 5…12 pages per document
(5 pages ×87, 6 ×27, 7 ×1, 8 ×12, 12 ×1 — `CATALOG.PUB` is the 12-page document).

All PAGE chunks have the same directory parent: the DOCUMENT chunk (712/712). [OBSERVED]

## 5.1 Size equation

```
size == 0x24 + 2 * u16@+0x1A          (712/712, zero exceptions)
```

Sizes therefore range 36 (no children) to 116 (40 children). There is no padding after the id
array: the next chunk's offset is exactly `offset + size`. [OBSERVED]

## 5.2 Layout

| Offset | Width | Field | Values over the 712 instances |
|---|---|---|---|
| 0x00 | u16 | typeMarker | `0x0014`, 712/712 |
| 0x02 | u8 | descriptor A | `0x1A`, 712/712 |
| 0x03 | u8 | descriptor B | `0x1A`, 712/712 |
| 0x04 | u16 | `settingsChunkId` | `0` ×575, else the id of a `0x2C` chunk ×137 |
| 0x06 | u16 | reserved (zero) | `0` ×712 |
| 0x08 | u16 | `pageFlag08` | `0` ×707, `1` ×3, `2` ×2 — [UNKNOWN], §5.5 |
| 0x0A | u16 | reserved (zero) | `0` ×712 |
| 0x0C | u16 | reserved (zero) | `0` ×712 |
| 0x0E | u16 | reserved (zero) | `0` ×712 |
| 0x10 | u16 | reserved (zero) | `0` ×712 |
| 0x12 | u16 | reserved (zero) | `0` ×712 |
| 0x14 | u16 | reserved (zero) | `0` ×712 |
| 0x16 | u16 | reserved (zero) | `0` ×712 |
| 0x18 | u16 | `pageKind` | `0` ×669, `1` ×3, `2` ×20, `4` ×20 — §5.4 |
| 0x1A | u16 | `childCount` | 0…40 |
| 0x1C | u16 | `childCount2` | always equals `+0x1A`, 712/712 |
| 0x1E | u16 | `elementSize` | `2`, 712/712 |
| 0x20 | u16 | reserved (zero) | `0` ×712 |
| 0x22 | u16 | reserved (zero) | `0` ×712 |
| 0x24 | u16[childCount] | `zOrder` — child chunk ids | see §5.6 |

The nineteen bytes `+0x06 … +0x17` are zero in all but five instances (the `+0x08`
exception). They are documented as reserved because the record never carries data there in the
Publisher 95 corpus. [OBSERVED]

## 5.3 The id-list header `+0x1A … +0x23`

`{u16 count, u16 count, u16 elementSize, u16 reserved, u16 reserved}` followed by
`count` u16 ids. The same header appears in GROUP (`0x000F`) two bytes earlier — at
`+0x16` with ids at `+0x22` — and closes exactly there on 827/827 GROUP chunks. The
duplicate count is a used/allocated pair that the Publisher 95 writer always keeps equal;
`elementSize == 2` matches the u16 ids. [OBSERVED for the values; INFERENCE for the
used/allocated reading]

## 5.4 `pageKind` at `+0x18`

| Value | Pages | Behaviour |
|---|---|---|
| 0 | 669 | normal page; the id list is its own children |
| 1 | 3 | behaves identically to 0 on this corpus — [UNKNOWN] (`CATALOG.PUB` 419 and 427, `RECIPT2.PUB` 260) |
| 2 | 20 | the id list is the z-order merge of this page's own children with the children of the **next** page in the document page list (20/20 verified order-preserving interleavings) |
| 4 | 20 | layer page: the id list is always empty (20/20) although the page still owns directory children; always sits immediately **after** a `pageKind == 2` page |

Reading: `4` = an object-container layer that is not itself displayed; `2` = the page that
composites the following layer's objects into its own z-order. [INFERENCE, supported by
40/40 structural matches; the alternative wording is "master page / page applying the
following master".]

There is **no master-name field, no page-number field, and no "is first page" flag** in the
PAGE record. The first page is identified only by DOCUMENT `+0x08`. The first page is always
`pageKind == 0`, `pageFlag08 == 0`, `settingsChunkId == 0`. [OBSERVED]

## 5.5 `pageFlag08`

Five instances: `CLASSIC.PUB` 267 (1), `JAZZY.PUB` 267 (1), `MODERN.PUB` 267 (1),
`CLASS_CD.PUB` 267 (2), `PLAIN.PUB` 267 (2). All are the last page of a 5-page greeting-card
document, but neither page position nor page size discriminates (sibling designs
`MODRN_CD.PUB` 267 and `PLAIN_CD.PUB` 412 carry 0). [UNKNOWN] — see §5.9.

## 5.6 Child id list

Integrity (712/712): every id resolves, no id appears twice, and no list contains the page's
own id, another PAGE id, or the DOCUMENT id. [OBSERVED]

Relation to the directory children (chunks whose `parentId` is this page):

| Relation | Pages |
|---|---|
| identical, same order | 549 |
| identical after removing the page's own `0x2C` settings child | 131 |
| a superset — the `pageKind` 2/4 layer cases | 32 |
| anything else | 0 |

The list is the page's **z-order / display list**, bottom-most first. Two documented
divergences from "directory children verbatim": (a) the `0x2C` settings chunk is a directory
child but never a list member; (b) a layer page's objects are spliced into the compositing
page's list at their z position. [OBSERVED for the data; INFERENCE for z-order — the order
matches directory/offset order in every non-layer case, the same convention GROUP uses]

## 5.7 `settingsChunkId` (`+0x04`) and the `0x2C` chunk

137 PAGE chunks carry a non-zero `+0x04`, and there are exactly 137 `0x2C` chunks: a strict
1:1 bijection in both directions. For every pair the `0x2C` chunk's directory parent is the
referencing page, and the `0x2C` id never appears in any page's z-order list (0/712).
[OBSERVED]

The 575 pages with `+0x04 == 0` inherit the document geometry. The `0x2C` body begins with the
page width and height in EMU (58-byte form:
`2c 00 | 18 18 | <u32 widthEmu> <u32 heightEmu> …`; in `p95/x/MSPUB.PUB` id 278 the values are
`0x007698F0` = 8.5 in and `0x00997AA0` = 11 in, identical to DOCUMENT `+0x14/+0x18`).
[OBSERVED for the fields; INFERENCE that it is the page-geometry source]

## 5.8 Cross-check against DOCUMENT

For all 128 documents the page set `{DOCUMENT.+0x08} ∪ ids at DOCUMENT.+0x74…` equals the set
of PAGE chunk ids exactly, in ascending chunk-offset order, and the DOCUMENT array length is
`(DOCUMENT.size − 0x74)/2`. [OBSERVED]

## 5.9 Residuals

| Gap | Experiment that closes it |
|---|---|
| `pageFlag08` values 1/2 on 5 pages | toggle each unaccounted page property (page border, print-page-size override, section start) on a scratch document in Publisher 95, save, diff `+0x08`; or compare `CLASSIC.PUB` vs `CLASS_CD.PUB`, which are the same design saved differently |
| `pageKind == 1` on 3 pages | same diff experiment; check whether those pages carry a foreground overlay |
| can `+0x1C` differ from `+0x1A` | delete shapes from a page so the container shrinks, save, re-read: if the writer keeps the old capacity the two diverge |
| 18 reserved bytes `+0x06…+0x17` | apply a page border / rotate the page, save, diff — a non-zero write proves the rectangle interpretation |
| direction of the layer link | drag the layer page elsewhere in the page list, save: if the pairing follows position, `pageKind == 2` composites the *following* page |

## 5.10 Validation predicates

```
u16@+0x00 == 0x0014
bytes @+0x02,+0x03 == 1A 1A
size == 0x24 + 2 * u16@+0x1A
u16@+0x1C == u16@+0x1A ; u16@+0x1E == 2 ; u16@+0x20 == 0 ; u16@+0x22 == 0
u16@+0x04 == 0 or typeof(by_id(u16@+0x04)) == 0x2C
u16@+0x18 in {0,1,2,4}
every id in +0x24 resolves; none is a PAGE, DOCUMENT or 0x2C chunk; none repeats
all bytes +0x06..+0x17 are 0 except +0x08 and +0x09
```
