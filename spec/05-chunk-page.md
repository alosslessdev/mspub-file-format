# 05 — PAGE chunk (`typeMarker 0x0014`)

One PAGE chunk per page. **727** instances in the 130-document corpus (712 in the 128 `.PUB`
files); 5…12 pages per document (5 pages ×87, 6 ×28, 7 ×1, 8 ×12, 9 ×1, 12 ×1 — `CATALOG.PUB`
is the 12-page document). Every equation in this chapter was re-checked on all 727 instances
with zero exceptions.

All PAGE chunks have the same directory parent: the DOCUMENT chunk (712/712). [OBSERVED]

## 5.1 Size equation

```
size == 0x24 + 2 * u16@+0x1A          (727/727, zero exceptions)
```

Sizes therefore range 36 (no children) to 116 (40 children). There is no padding after the id
array: the next chunk's offset is exactly `offset + size`. [OBSERVED]

## 5.2 Layout

| Offset | Width | Field | Values over the 712 instances |
|---|---|---|---|
| 0x00 | u16 | typeMarker | `0x0014`, 712/712 |
| 0x02 | u8 | descriptor A | `0x1A`, 727/727 |
| 0x03 | u8 | descriptor B | `0x1A`, 727/727 |
| 0x04 | u16 | `settingsChunkId` | `0` ×575, else the id of a `0x2C` chunk ×137 |
| 0x06 | u16 | reserved (zero) | `0` ×712 |
| 0x08 | u16 | `pageFlag08` | `0` ×722, `1` ×3, `2` ×2 in P95; a 4-bit authoring field, never read (write-only, §5.5) |
| 0x0A | u16 | reserved (zero) | `0` ×712 |
| 0x0C | u16 | reserved (zero) | `0` ×712 |
| 0x0E | u16 | reserved (zero) | `0` ×712 |
| 0x10 | u16 | reserved (zero) | `0` ×712 |
| 0x12 | u16 | reserved (zero) | `0` ×712 |
| 0x14 | u16 | reserved (zero) | `0` ×712 |
| 0x16 | u16 | reserved (zero) | `0` ×712 |
| 0x18 | u16 | `pageKind` | `0` ×684, `1` ×3, `2` ×20, `4` ×20 — §5.4 |
| 0x1A | u16 | `childCount` | 0…40 |
| 0x1C | u16 | `childCount2` | always equals `+0x1A`, 727/727 |
| 0x1E | u16 | `elementSize` | `2`, 727/727 |
| 0x20 | u16 | reserved (zero) | `0` ×712 |
| 0x22 | u16 | reserved (zero) | `0` ×712 |
| 0x24 | u16[childCount] | `zOrder` — child chunk ids | see §5.6 |

The nineteen bytes `+0x06 … +0x17` are zero in all but five instances (of 727) (the `+0x08`
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

`pageKind` is a **three-bit field** (bits 0, 1 and 2 of the u16), not an opaque enum. The
three bits are read independently by three accessors, each of which fetches the u16 at the
chunk's record offset `+0x18`:

| Bit | Value | Accessor | Test | Meaning |
|---|---|---|---|---|
| 0 | `0x0001` | `FUN_004D2E40` @ `0x004D2E40` | `return field & 1` | background hidden — "Ignore Background" |
| 1 | `0x0002` | `FUN_0041F8CC` @ `0x0041F8CC` | `return (field & 2) >> 1` | page composites the **following** page |
| 2 | `0x0004` | `FUN_0041F895` @ `0x0041F895` | `return (field & 4) >> 2` | page is the **layer** (background) page |

All three funnel through **`FUN_0040515B` @ `0x0040515B`**, which reads the u16 at record
offset `+0x18` (`seek(chunkId, chunkOffset + 0x18); read 2`) and operates on the chunk id
returned by **`FUN_004010E7` @ `0x004010E7`** — the *i*-th element of the DOCUMENT's page
array, i.e. the *i*-th page id. [OBSERVED, binary]

What each bit does:

* **bit 1 (value 2), the compositing page.** **`FUN_004D2E71` @ `0x004D2E71`** is the
  apply-background operation. Its guard is `FUN_0041F8CC(i)` (already kind 2 → no-op). It
  then takes page `i` and page `i+1`, ensures spare capacity in page `i`'s id array, and:
  `memmove(end of page i's id array, page i+1's ids, page i+1's count * 2)`,
  `page i.count += page i+1.count`, `page i+1.count = 0`, then
  `page i.+0x18 |= 2` and `page i+1.+0x18 |= 4`. This is exactly the corpus relation: the
  kind-2 page's id list is its own list with the following page's list appended, and the
  following page's list is empty. [OBSERVED, binary]

* **bit 2 (value 4), the layer page.** **`FUN_0041F803` @ `0x0041F803`** dispatches on the
  pair: `if (kind(i) has bit1) dissolvePair(i); else if (kind(i) has bit2) dissolvePair(i-1)`.
  **`FUN_00464A3F` @ `0x00464A3F`** is the reverse of `FUN_004D2E71`: it walks page `i`'s
  id array, removes each element whose directory parent is the layer page
  (`FUN_00416EBA` and `FUN_00405F4C` move it back to page `i+1`), then executes
  `page i.+0x18 &= 0xFFFD` and `page i+1.+0x18 &= 0xFFFB` — clearing bits 1 and 2 and thus
  returning both pages to kind 0 (or leaving bit 0 untouched). [OBSERVED, binary]

* **bit 0 (value 1), "Ignore Background".** **`FUN_004D769D` @ `0x004D769D`** toggles exactly
  this bit on the current page (`field = ((field & 1) == 0) ^ field & 1 ^ field`). It is the
  handler for menu command `0x54`, dispatched in **`FUN_0042D244` @ `0x0042D244`**
  (`case 0x54: FUN_004D769D();`); the menu label is the string pair
  `PTR_s_Igno_re_Background_0046DE64` ("Igno&re Background"), whose help text is
  `"Hides and doesn't print the background on this page."`
  **`FUN_0043851F` @ `0x0043851F`** check-marks that menu item from
  `(current page record + 0x18) & 1`, or — in single-page view — from `FUN_004D2E40(i+1)`.
  The drawing path reads the same bit: `FUN_00441D44` @ `0x00441D44` selects the background
  blit flag `0x100` when bit 0 is set, `0x80` when the following page's bit 0 is set.
  [OBSERVED, binary]

The domain is therefore `{0, 1, 2, 4}` in this corpus because Publisher 95 writes the three
bits one operation at a time and never leaves two set; the masks themselves are independent,
so a reader must treat `+0x18` as three flags. Values 3/5/6/7 do not occur (0/727). [OBSERVED
for the corpus; the independence is [OBSERVED] from the masks in the three accessors]

**Kind 1 is not "another kind of page":** it is an otherwise normal page whose
"Ignore Background" toggle is on. Such a page keeps its own id list unchanged (it has no
applied background pair in this corpus), which is why the three instances behave identically
to kind 0 for z-order. (`CATALOG.PUB` 419 and 427, `RECIPT2.PUB` 260.) [OBSERVED]

There is **no master-name field, no page-number field, and no "is first page" flag** in the
PAGE record. The first page is identified only by DOCUMENT `+0x08`. The first page is always
`pageKind == 0`, `pageFlag08 == 0`, `settingsChunkId == 0`. [OBSERVED]

## 5.5 `pageFlag08`

**Never read by any code path.** It is a write-only / pass-through field: the load path
decompresses the file record into the chunk object's buffer verbatim (`FUN_00444C1D` @
`0x00444C1D`, filling the buffer returned by `FUN_00401148` @ `0x00401148`, which zeroes
fresh allocations — so a newly created page carries `0`), and the save path emits
record bytes without interpreting them (`FUN_0052FDC8` @ `0x0052FDC8` →
`FUN_0052FD3E` @ `0x0052FD3E`; the stream-to-stream record copy is `FUN_00538D18` @
`0x00538D18`). No routine computes `+0x08` and no routine consumes it.

Scan scope (closed negative): every function in the Publisher 95 decompilation
(`C:\pwrk\decomp95`, 3 293 functions), the Publisher 97 tree (`notes/p98/decomp97`, chunk
table base `DAT_005D08B4`) and the Publisher 98 tree (`notes/p98/decomp98`, base
`DAT_006170CC`), plus the helper modules, which never reference the chunk stream at all
(`PUBDLG.DLL`, `MSPUBW32.DLL`, `PUB3STP.DLL`, `MSPUBQ32.DLL`, `COMPLINC.DLL`,
`PUBOLE32.DLL`, `PUB4STP.DLL`, `QS98.DLL`: no `0xACE8` stream-magic reference and no
chunk-table access in any of their decompiled trees). Findings:

* The only accessors that fetch a u16 from a chunk record by field offset are
  `FUN_0040515B` (offset `+0x18`) and the arbitrary-offset reader `FUN_00444DB5`
  (`seek(cursor); read`). Every call site of `FUN_00444DB5` uses a length of
  `0x0C`, `0x16`, `0x18`, `0x22`, `0x2C`, `0x2E`, `0x30` or `0x3E` — **no call uses 8**.
* Direct 16-bit loads at `record + 0x08` from a chunk-table object occur only in
  `FUN_0042ACB4` (`0x0042ACB4`), `FUN_00452B84` (`0x00452B84`), `FUN_0045F6B3`
  (`0x0045F6B3`), `FUN_0046234B` (`0x0046234B`), `FUN_005536EE` (`0x005536EE`) and
  `FUN_00578692` (`0x00578692`). In every case the record is the DOCUMENT (where `+0x08` is
  the first page id: `FUN_0046234B` repairs it by creating a page when it is 0) or the chunk
  named by `DOCUMENT/object record +0x4E` (the text/embedded store). None is a `0x14`
  record. [OBSERVED, binary]

The value set is a small per-page authoring stamp confined to one positional identity:
the **last page of the greeting-card templates**. In P95 it is `1` ×3 and `2` ×2, always
on chunk `0x10B` at page index 4 of 5 (`PAGEWIZ/CLASSIC.PUB` 1, `CLASS_CD.PUB` 2,
`JAZZY.PUB` 1, `MODERN.PUB` 1, `PLAIN.PUB` 2 — all `pageKind 0`). In P97 it is the last
page (index 19 of 20) of the same four cards (`CLASSIC` 7, `JAZZY` 8, `MODERN` 3, `PLAIN`
6; the `p97deluxe` companions carry `class_cd`/`modrn_cd` 3, `jazzy_cd` 2, `plain_cd` 5).
P98 carries all zero. The domain over all 727 pages is therefore
`{0,1,2,3,5,6,7,8}` — a 4-bit field (`8` occurs), zero everywhere except the card back
page, with the value varying by card design and generation. No writer exists in the
shipped code (the constructor zeroes it; no path stores to a `0x14` record's `+0x08`),
so the stamp arrives baked into the template and no consumer interprets it: a reader
must preserve it verbatim. [OBSERVED for the values and the positional identity; the
per-value semantics are unrecoverable from the shipped binaries — proven opaque over
the scan scope above, not an open question]

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

The binary confirms the merge is an *append at creation*: `FUN_004D2E71` @ `0x004D2E71`
(§5.4) copies the following page's id array onto the end of the compositing page's array and
zeroes the following page's count. The arbitrary insertion depths measured in saved files
(§5.4 of `notes/p95/slices/page.md`) are therefore later user z-order edits, not the
operation itself. [OBSERVED, binary]

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
u16@+0x18 & ~0x0007 == 0        ; three independent bits, §5.4
u16@+0x08 is preserved, never interpreted (§5.5)
every id in +0x24 resolves; none is a PAGE, DOCUMENT or 0x2C chunk; none repeats
all bytes +0x06..+0x17 are 0 except +0x08 and +0x09
```
