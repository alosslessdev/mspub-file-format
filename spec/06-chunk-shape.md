# 06 — Shape chunks

Shapes are the bulk of a Publisher document: 22 468 shape records across the 493-document
corpus (markers `0x0000`–`0x0008`; plus the document-level record `0x0016`, which is not a shape). This chapter defines their framing and
geometry exactly, and records what is proven about the per-marker field maps.

## 6.1 Framing

Every shape chunk is a **fixed record** with an optional counted tail. There is no
id/type sub-record stream (chapter 12).

```
+0x00  u16  type marker      the marker IS the object class
+0x02  u8   A                per-type constant (for 0x0003: per-document constant)
+0x03  u8   B                per-marker descriptor byte (base = B+10, or B for 0x04-0x07/0x16)
+0x04  u16  rotation         1/10 degree (0.1°), counter-clockwise, mod 3600
+0x06  i32  left             EMU, signed
+0x0A  i32  top              EMU, signed
+0x0E  i32  right            EMU, signed
+0x12  i32  bottom           EMU, signed
+0x16  ...  marker-specific fields
```

`[OBSERVED]` on every shape marker. `B` equals the fixed record length and does **not**
grow when the optional tail grows: `B` is 92 for `0x0000`, 96 for `0x0001`, 116 for
`0x0002`/`0x0003`, and 59/62/53/41 for `0x0004`/`0x0005`/`0x0006`/`0x0007`.

## 6.2 Geometry block

`[OBSERVED]` over 5 569 chunks of markers `0x0000`–`0x0007`:

* `left ≤ right` and `top ≤ bottom` in **5 569/5 569** cases — so the order is
  `(l, t, r, b)`, not `(x, y, w, h)`.
* The four values are **signed**: documents with page origin `(0,0)` contain shapes with
  negative `l`/`t` (objects placed left of / above the page).
* Unit is **EMU** (914 400 per inch), proven three independent ways: page-corner shapes
  land on `0` and `width`; the modal shape size equals a whole number of inches; and the
  four magnitudes are bounded by `0x01FFFFFF` (≈ 36.7 in) corpus-wide — no other candidate
  unit (twips, points, 1/100 mm) produces consistent page-relative boxes.
* Objects may lie **outside** the page rectangle: Publisher uses a pasteboard. The
  validator therefore checks ordering and a 400-inch sanity bound, not containment.

Rotation is a `u16` at `+0x04` in **tenths of a degree (0.1°)**, counter-clockwise, reduced
mod 3600. `[OBSERVED]` over 2 409 non-zero instances in the 493-document corpus:

| measurement | value |
|---|---|
| distinct values | 164, range 1 … **3598** |
| values `>= 3600` | **0** |
| values that are multiples of 450 (the 45° ladder) | 1 703 (70.7 %) |
| top values | 900 (425), 2700 (347), 450 (312), 3150 (312), 1800 (259) |

Two independent arguments pin the unit:

1. **Ceiling.** No value reaches 3600. Under a 1/100° reading the field would range over
   0…35 999 and, for the observed angle distribution, roughly 90 % of the samples would
   exceed 3600. Under 1/10° the ceiling is 3599 and the observed maximum of 3598 is the
   natural bound. `[OBSERVED]`
2. **Ladder.** 70.7 % of non-zero rotations are exact multiples of 450, i.e. the canonical
   45°/90°/135°/180°/225°/270°/315° snap ladder — which is what Publisher's rotate tool
   produces. The same set read as 1/100° would be 4.5°, 9°, 13.5° … — not a UI ladder.

The `900/2700/1800` values occur in 45–51 separate documents (page furniture rotated a
quarter or half turn); `450/3150` occur only in `MODERN.PUB`, `PLAIN_CD.PUB` and
`JAZZY.PUB`, the templates that use decorative diagonal elements. `[OBSERVED]`

**Prior-art refutation, restated precisely.** libmspub's *complement* `360 − v/10` is wrong:
the stored value is the rotation itself, not its complement (a 45° element stores 450, not
3150, in `MODERN.PUB`). Its *divisor* (10) is right. The earlier revision of this chapter
published "1/100 degree" from a 25-sample Publisher 95 subset; the 493-document
measurement above supersedes it.

## 6.3 Marker table

| Marker | Class | Instances | `B` (+0x03) | Fixed base | Optional tail |
|---|---|---|---|---|---|
| `0x0000` | free-form shape | 5 086 | `0x5C` (92) | 102 | `+2k`, k = 0…6 (102…114) |
| `0x0001` | free-form shape (variant) | 752 | `0x60` (96) | 106 | `+14k`, k = 0…31 |
| `0x0002` | image-bearing shape | 1 016 | `0x74` (116) / `0x8C` (140) | 126 (95/97), 150 (98) | `+8k` (126…222 observed) |
| `0x0003` | polygon shape | 2 627 | `0x74` (116) / `0x8C` (140) | 126 (95/97), 150 (98) | `+8k` |
| `0x0004` | line | 2 785 | `0x3B` (59) / `0x43` (67) | 59 (95/97), 67 (98) | — |
| `0x0005` | rectangle | 4 879 | `0x3E` (62) / `0x46` (70) | 62 (95/97), 70 (98) | — |
| `0x0006` | embedded-object shape | 4 050 | `0x35` (53) / `0x3D` (61) | 53 (95/97), 61 (98) | — |
| `0x0007` | smallest shape record | 1 159 | `0x29` (41) / `0x31` (49) | 41 (95/97), 49 (98) | — |
| `0x0008` | shape variant | 114 | `0x76` (118) | **128** = `B + 10` | `+2k`, k = 0…10 (count pair at `+0x76`) |
| `0x0009` | shape variant (98 only) | 5 | `0x35` (53) | **61** = `B + 8` | — |
| `0x000A` | shape variant (98 only) | 7 | `0x74` (116) | **126** = `B + 10` | `+8k` (198 at k = 9, 222 at k = 12) |
| `0x000B` | shape variant (98 only) | 5 | `0x4E` (78) | **86** = `B + 8` | — |
| `0x0016` | document-level record, **not a shape** | 488 | `0x10` (16) / `0x12` (18) | 16 (P95, +1 P97 file), 18 (P97) | — |

`[OBSERVED]` — instance counts are the sum over `p95/x` (130 docs), `p97/x` (108),
`p97deluxe/x` (250) and `p98/x` (5).

The four Publisher-98-only variants `0x0008`–`0x000B` all sit under a PAGE in the gallery
page of the five P98 publications, and their size rules above are exact (114/5/7/5
instances). `0x0008`, `0x000A` use the same `B + 10 + element·count` trailer as
`0x0002`/`0x0003`; `0x0009` and `0x000B` use a compact `B + 8` form with no array.
`0x0008` is no longer ambiguous: its trailer is a counted array of `u16` chunk ids whose
elements are **other `0x0008` records** (§6.4.2). The remaining interior fields of all four
variants are closed by the following decomposition — no interior byte is left unclaimed.
The 22-byte prologue (`+0x00 … +0x15`) is the shared shape prologue (§6.3): marker,
stamp (`0x7688`/`0x3535`/`0x747D`/`0x4E4E`, high byte = `B`), rotation `0x0000` in the
gallery copies, and the geometry quad — which is all-zero in the 5 gallery copies per
variant (`0x0008`: 5/114; `0x000A`: 5/7; `0x0009`/`0x000B`: 5/5) and a real centred box
satisfying `x0 < x1`, `y0 < y1` in every non-degenerate instance (109/109 `0x0008`,
2/2 `0x000A`; notes/p98/slices/markers98.md §3.1). The body (`+0x16 …`) is the shared
P98 shape body of §3.3 there: reserved zeros at `+0x18–+0x1F`, the unset-colour sentinel
`0xC0E40000` at `+0x20` (114/114 `0x0008`; palette slice F6 pins the same dword on RECT),
the `0xC0E4`-doublet family at the fixed offsets (`+0x26`, `+0x38`, `+0x3E`, `+0x44`,
`+0x54` in `0x0008`), per-variant identities (`0x0009` is byte-identical to `0x0006`
except marker/stamp; `0x000B` varies only in the six CLRCHK bytes `+0x2A/+0x31/+0x32/
`+0x35/+0x3B/+0x41`; `0x000A` carries the `S = 8/14` trailing element size with two
non-degenerate 8-byte-entry tails in CHEKLIST), the `0x0008` counted `u16`-id tail
whose 15 non-zero elements all name other `0x0008` records (§6.4.2), and the `+0x58`
object key — ordered-equal to the `0x004C` value list (`value >> 16`, 109/109 across
CHEKLIST/CLRCHK/INFOSHET; low word 0 in 108/109, `0x0001` in INFOSHET's second entry)
and read live by the Publisher 98 binary (`FUN_00425447`, VA `0x00425447`:
`if (marker == 8 …) key = *(record + 0x58)`; the same function tests
`(u32@+0x18 >> 19)` against `{5, 7, 8, 10, 0x70, 0x71, 0x73}`). The exact 32-bit
boundaries of doublet occurrences 3–8 are **proven opaque / write-only**: the Publisher
98 body is byte-packed (a field starts at odd `+0x2B`), the neighbouring bytes are zero
in all gallery copies, and no corpus pair varies a single field in isolation — the five
documents hold only the degenerate gallery copies plus, for `0x0008`, 109 placed
instances whose bytes move together. Scan scope: the three shipped executables
(`C:/pwrk/decomp95` 3 826 functions, `notes/p98/decomp97` 4 253, `notes/p98/decomp98`
5 361) plus `PUBDLG.DLL` 95 (`C:/pwrk/dlg95` 58), `MSPUBW32.DLL` 95 (`C:/pwrk/wiz95`
609), `PUBOLE32.DLL` 95 (`C:/pwrk/decomp-ole95` 208) and `QS98.DLL`
(`notes/p98q/decomp_quill` 2 104). A reader decodes the pinned fields above and
preserves every remaining body byte verbatim. `[OBSERVED, binary]`

**`B` is a per-marker constant descriptor byte, not a record length.** It coincides with
the fixed base only for `0x0004`…`0x0007` and `0x0016`; for `0x0000`/`0x0001`/`0x0002`/
`0x0003`/`0x0008` the base is `B + 10`. It never grows when the counted tail grows, which
is why `tools/validate.py` can treat it as an invariant (`record_length_byte`).

**Correction to the previous revision of this table**: `0x0008` has fixed base **128**, not
41 (41 is `0x0007`), and it has no Publisher 95/97 instance at all — the 114 instances are
all in the five Publisher 98 documents, where it is the most common shape marker after
`0x0005`. `0x0016` is 16 bytes in Publisher 95 but **18** in Publisher 97 (357 of 358
documents; one 16-byte legacy record remains in `p97/x`) and absent from the Publisher 98
corpus; the extra 2 bytes are a u16 at `+0x10`.

The Publisher 98 writer inserts **8 bytes** into every shape record (24 into the
image-bearing `0x0002`/`0x0003`). All four geometry fields stay at the same offsets, and
the growth is **not an append**: aligning the Publisher 97 and Publisher 98 records of
`0x0004`/`0x0005`/`0x0006`/`0x0007` (from `p97/x/MSPUB.PUB` and `p98/x/MSPUB.PUB`) shows
the trailing bytes of the fixed part preserved at the end of the longer record and the
insertion in the `+0x1C … +0x2A` region. `[OBSERVED]` for the four markers compared.
Byte-precise alignment of the `p97/x/MSPUB.PUB` vs `p98/x/MSPUB.PUB` pairs pins the
insertion down to the field level: `+0x18`/`+0x1C` (the text colour pair, §6.7.7) keep
their offsets and values (`00…00` / `01 00 00 00` in the marker-`0x0004`…`0x0007`
gallery pair); the 8 inserted bytes are `00 E4 C0 07 00 E4 C0 00 00` read at the 98
offsets — i.e. `+0x20 = 0xC0E40000` (the unset-colour sentinel, palette slice F6),
`+0x24 = 0xC0E40007` (same doublet family), `+0x28 … +0x2B` the pen block — and the
95/97 tail from the pen colour `+0x23` on is preserved byte-for-byte 8 bytes later
(common suffix 20/20 bytes on the `0x0004` pair; the `0x0005` pair carries the four
duplicated colour references `+0x23/+0x2E/+0x34/+0x3A` shifted likewise). The 98
readers consume exactly these relocated fields: `FUN_0042AF42` (VA `0x0042AF42`) reads
the width byte at `+0x2A`, the colour dword at `+0x20`, the pen bytes at
`+0x28/+0x29/+0x2D`, and calls `FUN_00429A08` (VA `0x00429A08`) with
`(colour@+0x20, width@+0x2A)`; widths go through the 98 mapper `FUN_004547F1` (VA
`0x004547F1`), byte-identical to the 95 mapper (`0xFF → 0`, `< 0x80` → `n` pt,
else quarter-point ladder). What is *not* claimed is the 32-bit boundary inside the
`00 E4 C0 07 00 E4 C0` run: the body is byte-packed there (as in §3.3 of
notes/p98/slices/markers98.md), so the run is stated as the three overlapping dwords
above and any finer split is **proven opaque** with the same scan scope as §6.3 —
preserved verbatim, never synthesised. `[OBSERVED, binary]`

`0x0016` is a per-document record holding the ids of four document-level chunks. It is
**not a shape** and must not be transformed.

| Off | Width | Meaning | Evidence |
|---|---|---|---|
| `0x00` | u16 | `0x0016` | 130/130 P95 |
| `0x02` | u8 | `0x1A` — descriptor byte `A` | 130/130 P95 |
| `0x03` | u8 | `0x10` (P95) / `0x12` (P97) — descriptor byte `B` == record size | 130/130, 357/358 |
| `0x04` | u32 | style id — **not** a chunk id (resolves to a live chunk in only 8/130 files, by coincidence) | 130/130 |
| `0x08` | u16 | id of the `0x001A` chunk | 130/130 |
| `0x0A` | u16 | id of the `0x001C` chunk | 130/130 |
| `0x0C` | u16 | id of the `0x002E` chunk (note: `0x2E` precedes `0x2D`) | 130/130 |
| `0x0E` | u16 | id of the `0x002D` chunk | 130/130 |
| `0x10` | u16 | Publisher 97 extension only (record is 18 bytes there) | 357/358 |

`[OBSERVED]` — slot order verified 130/130 on the Publisher 95 corpus (source:
`notes/p95/slices/shapeA.md` §7) and reproduced on `p97/x`/`p97deluxe/x`, where the record
is 18 bytes. The four child records have their own size laws, each `26 + n·elem` with
`n = u16@+0x04` of the child: `0x001A` 14-byte elements, `0x001C` 8-byte, `0x002D` 8-byte
(`n = 0` in 129 of 130 P95 files), `0x002E` always 26 bytes (`n = 0`).

## 6.4 Counted tail

For `0x0002`/`0x0003` the tail is a counted array: `u16 count` and a duplicate `u16 count`
at `+0x74`/`+0x76`, elements of 8 bytes starting at `+0x78` (95/97). `0x0001` uses a
**contiguous** array of 14-byte elements from `+0x6A` with `N = (size − 106)/14`
(§6.4.1); two `u16` — `A` at `+0x4A` (column stops) and `B` at `+0x50` (rows) — split that
array into two sub-arrays with `A + B = N` in **747/747** chunks of the Publisher 95/97
corpora (259 tail-bearing chunks, plus 488 with `N = 0` and `A = B = 0`). `[OBSERVED]` `0x0000` carries `+2k` with a duplicate pair `u16@+0x5C ==
u16@+0x5E == k` and an element size word `0x0002` at `+0x60`; its elements are **chunk ids
of sibling records** — 746/746 resolve to an existing id, 656/746 to a sibling.
`0x0008` appears only in the Publisher 98 corpus; its fixed base is 128 and its trailer is
the same counted form as `0x0000` — duplicate count at `+0x76`/`+0x78`, element size word
`0x0002` at `+0x7A`, elements from `+0x80` (§6.4.2).

### 6.4.1 The `0x0001` 14-byte tail elements

The tail is contiguous from `+0x6A` (`size = 106 + 14·N`; 2 618 records in 259 chunks of the
Publisher 95/97 corpora) and each record is `{u32 a, u32 b, u32 c, u16 d}`. The records are
**two arrays, not one run**: the counts in the fixed part delimit them. `[OBSERVED]`

| Sub-array | Count | Content | Evidence |
|---|---|---|---|
| records `0 … A−1` | `A` = u16@`+0x4A` (935 records) | column stops: `a` is an ascending x within the frame, `d == 0xFFFF` | `d == 0xFFFF` 935/935; `a` non-decreasing 676/676; `a[last] ≤ right−left` 259/259 |
| records `A … A+B−1` | `B` = u16@`+0x50` (1 683 records) | rows: `a` is the cumulative row bottom, `b` the minimum height, `c` the nominal height, `d` a selector | `a` strictly increasing 1 424/1 424; `a[A] < a[A−1]` (the only reset) 259/259; `a[last] == bottom−top` 259/259; `Δa == max(b, c)` 1 248/1 424 |

`A + B = N` in 259/259 tail-bearing chunks. **The column count is `A` from `+0x4A`, not the
length of the leading `d == 0xFFFF` run**: that run equals `A` in only 134/259 chunks and
over-counts in 125/259, because row 0 frequently carries `d = 0xFFFF` as well. `[OBSERVED]`

| Field | Column records (`0 … A−1`) | Row records (`A … A+B−1`) |
|---|---|---|
| `a` `+0x00` | ascending x tab stop | cumulative row bottom; `0 < a ≤ bottom−top`, last value `== bottom−top` |
| `b` `+0x04` | **minimum column width**: `0x1BE7C` (114 300 EMU = 9 pt) on every created column (VA `0x00542A57`) | **minimum row height** — the floor the distribution cannot go below; seeded `0` at creation (VA `0x00542A57`) and consumed as a floor by VA `0x0054703A` (below). The nonzero value present in every saved row is not written by any located setter; it survives edit/save unchanged |
| `c` `+0x08` | **nominal column width**; equal to `a[i]−a[i−1]` | **nominal row height**; equal to `a[i]−a[i−1]`, rewritten on a drag-resize (VA `0x0054EA5A`) |
| `d` `+0x0C` | `0xFFFF` ×935 | `0xFFFF` ×1 239, `0` ×333, `1` ×59, `3` ×36, `2` ×12, `6` ×4 |

**Row advance and the two metrics.** `a` is the running sum of `max(b, c)`, and the layout
routine that produces it is VA `0x0054703A`, called from the frame-resize handlers
(VA `0x00546D17` for the width axis, VA `0x0054BD36` for the height axis) as
`FUN_0054703A(row-array-pointer, B, target_extent, &total)`. It first sums every `b` (the
minimum total), then distributes the frame height over the `c` values proportionally,
raising any `c` that falls below its `b` to `b`, and finally writes
`a[i] = a[i−1] + max(b[i], c[i])` (the `piVar7[-1] <= iVar4` selection). The corpus agrees:
`Δa == max(b, c)` in 1 248/1 424 pairs (50 more within 2 000 EMU), and the first row is
measured from the frame top, where `a[A] == max(b, c)` in 224/259 chunks (3 more within
2 000 EMU). The remaining 158 advances exceed both and are not explained by the record
(chapter 10 §10.7).

The two metrics are **not** interchangeable, and neither is a criterion for the other:
`c` is what the user set (it is created as the even division of the frame extent and
survives editing as a nominal value), `b` is the floor the text imposes. `b > c` therefore
means the row grew to fit its text; it occurs on 32 of the 132 measured advances, and on
those rows the *saved* `a` follows `b`, not `c`. The column records use the same pair
transposed: `c` is the nominal width, `b` is the minimum width (a constant 9 pt on every
column Publisher creates). The identity `Δa == max(b, c)` holds for 1 248/1 424 row pairs;
for columns `b` is constant, so `Δa == c` in every created column.

`[OBSERVED]` for the counts, the geometry identities and the `b`/`c` split (writer
VA `0x00542A57`, layout VA `0x0054703A`, resize VA `0x0054EA5A`); the meaning of the row
selector `d` remains chapter 10 §10.3.2. The one gap is the *origin* of a saved `b > 0`:
`0x00542A57` seeds `b = 0`, `0x0054703A` reads it as a floor and never writes it, and a
write scan of the two builds (3 825 functions in `MSPUB.EXE` 95, 4 252 in 97) finds no
store into the `+0x04` slot other than those two constants — the only other writers touch
`a` (`+0x00`) and `c` (`+0x08`). Every corpus row nonetheless carries a nonzero `b`, so
the value arrives with a whole-array copy rather than through a field setter.

The price-list frame (`pricelst.pub`, chunk `0x0131`) has `A = 9` and `B = 19` (`N = 28`):
its nine column stops are the nine price columns, and chapter 10 §10.3.1 shows `A · B`
equals the block's cell count for every four-or-more-cell block.

A parser derives `N` from the record size and `A`/`B` from `+0x4A`/`+0x50`; for the markers
with a count pair (`0x0000`, `0x0002`/`0x0003`, `0x0008`) it must additionally verify
`size == base + count · elem`. `[OBSERVED]`

### 6.4.2 The `0x0008` tail is a counted array of `0x0008` ids

`0x0008` uses the `0x0000` framing with `B = 0x76`: the count appears twice at `+0x76`
and `+0x78` (equal in 114/114 records), the element-size word `0x0002` sits at `+0x7A`
(114/114), and the elements start at `+0x80`. The size law is exact:

```
size = 0x80 + 2·count         114 / 114
```

| count | records | size |
|---|---|---|
| 0 | 110 | 128 |
| 1 | 1 | 130 |
| 2 | 2 | 132 |
| 10 | 1 | 148 |

`[OBSERVED]` — the 114 `0x0008` records of `p98/x` (95 in `CLRCHK.JSP`, 14 in
`CHEKLIST.JSP`, 3 in `INFOSHET.JSP`, 1 each in `MSPUB.PUB`/`ZMSPUB.PUB`). Every one of the
15 non-zero elements resolves to a live chunk id, and **all 15 name another `0x0008`
record**; 5 are siblings of the owning record (same parent), the other 10 belong to a
different parent of the same tree. `[OBSERVED]`

So `0x0008` is a **shape-list node**: its trailer enumerates further `0x0008` records.
`tools/validate.py` enforces `shape8_tail` (`B`, the count pair, the element size and
`size = 0x80 + 2·count`). `[OBSERVED]`

## 6.5 Refuted prior art

Two widely repeated libmspub offsets do **not** hold for this family:

| Claim | Measurement |
|---|---|
| "fill type at `+0x2A`" | `+0x2A` is a per-type constant (`0xFF` for `0x0000`/`0x0003`, `0x00` for `0x0001`, absent for `0x0007`) |
| "line flags at `+0x41`" | no shape-record reader touches `+0x40`/`+0x41`, and the `u16` at `+0x40` is not four insets |

`[OBSERVED]` The second row is now measurable two ways.

* **No reader.** The offset census covers every function that dereferences the chunk-table
  idiom (chunk-data pointer at `table + 8 + 0x10·id`): 422 of the 3 825 decompiled
  functions of MSPUB.EXE 95 and 549 of the 4 252 of MSPUB.EXE 97. It contains **no** read
  of `+0x40` or `+0x41` from a chunk record. Every claimed "inset/quad" access is itself a
  read of the shape record, so the absence is decisive. `[OBSERVED]`
* **Not four values.** The `u16` at `+0x40` takes `0x39`, `0`, `0x78`, `0x64`, `0xC9`,
  `0x48`, `0x120`, `0x168`, `0x90`, `0xD8` … depending on marker and document — a size or
  an ordinal, not a 2-bit quad. `[OBSERVED]`

The positive result — which offsets *do* carry the pen and the frame descriptor — is in
§6.7.

## 6.6 Shared fields

`+0x20` is a one-byte **selector**, not a type discriminator and not a boolean. Over the
22 354 records of markers `0x0000`–`0x0007` it takes `0` (10 361), `1` (3 854) and `2`
(7 180) — 21 395 records — the range `0x80`–`0xAB` in 626, and one of 333 other values in
the remainder. `0x00417684` (`FUN_00417684`) consumes it as an index into the colour-object
cache: `1` selects the object built from the colour at `+0x1C`, `2` the one built from
`+0x18`, any other value is used as the cache index itself, and the range `0x80`–`0xAB`
makes the function return 0 ("no object"). `[OBSERVED, binary]` The name is therefore
*colour/object selector*; the previous revision's "text-present byte" is refuted — the
`!= 0` test at `0x004177C3` is a "this record has an explicit colour object" test, and
`0x0040DFBF`'s `0x80`/`0xAB` window is the no-object range, not a value outside the corpus
(626 records carry a value in it). §6.7.7 gives the block.

`+0x22` is *not* a shared enum: it is the line-width code (§6.7.1). The earlier revision of
this chapter grouped it with `+0x20` because both take small values, but the decoder below
shows that the `0x81`/`0x1E` members of the set are width encodings, not flags.

## 6.7 Draw-time field map

This section lists every offset a shape record shares with the rendering code, with the
MSPUB.EXE 95 VA that reads it. All VAs are in `notes/p95/decomp`; the Publisher 97 binary
reads the same offsets at the corresponding VAs (e.g. the draw dispatcher is
`0x0045140D`). `[OBSERVED]`

| Off | Width | Field | Read at (95 VA) |
|---|---|---|---|
| `+0x16` | u16 | **flag word** — bit 0 shadow, bits 3/4 frame pair (§6.7.5, §6.7.6) | `0x004177C3`, `0x004051D9`, `0x004675F8`, `0x004AFE67` |
| `+0x18` | u32 | **colour reference A** (`0` = none) | `0x0041762A`, `0x004271FA` |
| `+0x1C` | u32 | **colour reference B** (`0`/`1` = none) | `0x0041762A`, `0x004271FA` |
| `+0x20` | u8 | colour/object selector (§6.6) | `0x0041762A`, `0x00417684`, `0x004177C3` |
| `+0x21` | u8 | pen style byte — `0x00` in 21 842 / 21 925, else `0x1E`/`0x1F` | `0x0042253E` |
| `+0x22` | u8 | line-width code | `0x0042253E`, `0x004B0C67`, `0x004675F8` |
| `+0x23` | u32 | **line colour reference** | `0x0042253E`, `0x004AFE67` |
| `+0x29` | i16 | frame border style (`0` = none); `0x0004`: first inset | `0x00418211`, `0x004675F8`, `0x00405740` |
| `+0x2B` | u16 | frame flags (bit 2 selects the inset axis) | `0x00418211`, `0x004675F8` |
| `+0x2D` | i32 | frame inset pair (`i32`, `i32`); `0x0004`: insets 2 and 3 | `0x00418211`, `0x004675F8`, `0x00405740` |
| `+0x35` | i32 | fourth inset — read only for `0x0004` (§6.7.8) | `0x00405740` |
| `+0x2E` | u32 | second colour reference (0x0005 only) | — (see §6.7.4) |
| `+0x34` | u32 | copy of `+0x23` (0x0005 only) | — (see §6.7.4) |
| `+0x39` | u16 | dash/arrow style, bit 1 = start/end swap | `0x0042253E`, `0x004B0C67` |
| `+0x3A` | u32 | copy of `+0x2E` (0x0005 only) | — (see §6.7.4) |
| `+0x4C` | u16 | frame pen style (0x0000/0x0001) | `0x00417540` |
| `+0x4E` | u32 | frame pen colour (0x0000/0x0001) | `0x00417540` `[INFERENCE]` |
| `+0x70` | u32 | **text colour reference** (0x0002/0x0003) | `0x0042FB8B`, `0x0041DCF8`, `0x004177C3` |

### 6.7.1 The pen: `+0x21` … `+0x27`

The six bytes from `+0x21` are a pen descriptor `{u16 style, u32 colour}`: `+0x21` is
the style byte (`0x00` in 21 842 of 21 925 records, `0x1E` in 80, `0x1F` in 3), `+0x22` is
the width code, and `+0x23` is the colour reference. The line
drawer at VA `0x0042253E` splits the descriptor as `dword@+0x21` + `word@+0x25` (the same
six bytes) when it hands it to the pen setup, and, for the shadow copy (§6.7.5), recolours
the line at VA `0x004AFE67` by overwriting `+0x23` and restoring the six bytes afterwards.
`[OBSERVED]`

**Width code (`+0x22`).** VA `0x00405875` maps it to EMU; `0x319C` = 12 700 EMU = 1 pt and
`0xC67` = 3 175 EMU = 1/4 pt:

| `+0x22` | Width |
|---|---|
| `0x00`, `0xFF` | 0 (no line) |
| `0x01` … `0x7F` | `n` pt |
| `0x81` … `0xFE` | `(k mod 3 + 1)/4` pt + `k div 3` pt, `k = n − 0x81` |

So `0x81`–`0x83` are ¼, ½, ¾ pt and `0x84`–`0x86` are 1¼, 1½, 1¾ pt. The corpus uses
`0x00`–`0x0F`, `0x12`, `0x14`, `0x18`, `0x1E`, `0x21`, `0x24`, `0x28`, `0x30`, `0x32` and
`0x81` — integer point widths from 1 to 50 plus one quarter-point value. `[OBSERVED,
binary]`

**Colour (`+0x23`).** A 32-bit colour reference in **every** shape record of the
Publisher 95/97 family: 21 925 / 21 925 records of markers `0x0000`–`0x0007` over the
four corpora, counting only records whose `B` byte is the 95/97 value (the Publisher 98
layout has `B + 8`). `[OBSERVED]` The decoder is §6.7.2.

**Text colour (`+0x70`).** For the two markers whose fixed part reaches `+0x70`
(`0x0002`/`0x0003`, base 126) the `u32` at `+0x70` is either `0xFFFFFFFF` ("no text
colour") or a valid colour reference: 3 633 / 3 633 records. VA `0x0042FB8B` tests it
against `-1` and VA `0x004177C3` decodes it with the same switch. `[OBSERVED]`

### 6.7.2 Colour-reference domains

Colour references in shape records are the same encoding as everywhere else (chapter 09
§9.1). The Publisher 95 decoder is VA `0x00418364`; it switches on `ref >> 29`:

| Top 3 bits | Range of high byte | Domain | Result |
|---|---|---|---|
| `0b000` | `0x00`–`0x1F` | palette index | `palette[ref & 0xFFFF]`, index `< 0x38` |
| `0b001` | `0x20`–`0x3F` | literal RGB | `ref & 0x00FFFFFF` (BGR `COLORREF`) |
| `0b010` | `0x40`–`0x5F` | derived A | `0x00508BFB(ref)` |
| `0b100` | `0x80`–`0x9F` | derived B | `0x00508A9E(ref)` |
| `0b011`, `0b101`, `0b110`, `0b111` | — | not written by the 95/97 writer | falls through |
| `0xFFFFFFFF` | — | no colour | `0xFFFFFFFF` |

`[OBSERVED, binary]` — `tools/palette.py::decode_colorref` takes the same `>> 5` split of
the high byte and decodes three of the domains outright:

| Reference | Domain | `decode_colorref` |
|---|---|---|
| `0x0000000C` | `0b000`, index 12 | `(0, 0, 128)` from the 56-entry table |
| `0x20E3E3E3` | `0b001`, RGB `E3E3E3` | `(227, 227, 227)` |
| `0xA0000000` | `0b101` automatic | `(215, 183, 115)` = `0x4737B` |
| `0x40000001` | `0b010` derived A | `None` — needs the derivation helper |
| `0x81A3001F` | `0b100` derived B | `None` — needs the derivation helper |

So a reader that uses `palette.decode_colorref` must special-case the two derived domains
itself. The `+0x23` corpus splits 19 886 palette / 397 RGB / 1 642 derived-B references
(21 925 total), so a reader must preserve `None` rather than treat it as "no colour".
`[OBSERVED]`

### 6.7.3 The frame descriptor: `+0x29` … `+0x34`

The twelve bytes `+0x29` … `+0x34` are read as `{i16 style@+0x29, u16 flags@+0x2B,
i32 a@+0x2D, i32 b@+0x31}`. VA `0x004675F8` branches on `style == 0` (no border: it uses
`a` as an inset and draws a plain rectangle) and on bit 2 of `flags` (which axis the inset
applies to); VA `0x00418211` copies the eight bytes `+0x2D` … `+0x34` as two `i32` and
passes them to the polygon builder as a point. For marker `0x0004` the run is **sixteen**
bytes — `0x00405740` reads a fourth `i32` at `+0x35` and treats all four as insets
(§6.7.8). In `0x0005` this style word is
`0xFFFE` (−2, "no border") in 4 347 / 4 480 records, which is the `0xFF 0xFE` sentinel
noted in earlier revisions of this chapter. `[OBSERVED, binary]`

### 6.7.4 The two colour slots of `0x0005`

`0x0005` (rectangle) carries **four** colour references: `+0x23` (the pen, §6.7.1) and
`+0x2E`, each duplicated at `+0x34` and `+0x3A`. Corpus identity over 1 110 records:
`dword@+0x23 == dword@+0x34` in 1 110 / 1 110, `dword@+0x2E == dword@+0x3A` in
1 105 / 1 110, and `dword@+0x23 == dword@+0x2E` in 1 096 / 1 110 (all four are valid
references in 1 110 / 1 110 each). `[OBSERVED]`

The records where the two slots differ are exactly the ones where a coloured interior is
drawn without a border (`+0x23 = 0`, `+0x2E` set) or with a different border, so the slots
are read as **line colour `+0x23`** and **fill colour `+0x2E`**. `[INFERENCE]` The
duplicates at `+0x34`/`+0x3A` are not read by any located 95/97 code path.

### 6.7.5 The shadow

The shadow is **not a stored field**. It is one flag bit plus two compile-time constants.

| Element | Value | Evidence |
|---|---|---|
| presence | bit 0 of `+0x16` | written at `0x004D02F9` (attribute 0), read at `0x00411776`, `0x004675F8`, `0x004AFE67`, `0x00405740` |
| offset | `+0xDF3E` EMU on **both** axes = 57 150 EMU = 1/16 in = 4.5 pt, down-right | the literal appears in exactly these shadow sites: `0x00405740`, `0x00411776`, `0x004675F8`, `0x004AFE67` |
| colour | 50 % tint toward white of the pen colour `dword@+0x23` | `0x004AFE67` and `0x004675F8`, both via `FUN_00508B3F(c, 1, 50)` |

`[OBSERVED, binary]` The four operations, in prose:

* **Bounds.** `0x00405740` builds the record's rectangle and, when its third argument is
  non-zero and bit 0 of `+0x16` is set, inflates the rectangle by `0xDF3E` on all four
  sides — the selection/redraw bounds include the shadow.
* **Damage.** `0x00411776` adds each object's rectangle to the repaint region; when bit 0
  is set it calls `FUN_00530BDB(region, count, 0xDF3E, 0xDF3E)`, which converts the two
  EMU values to device units and translates the rectangle and every point of the polygon by
  them, and adds a **second** region — the shadow's.
* **Frame.** `0x004675F8` builds the frame's point list twice: the plain list, and a copy
  offset by `(0xDF3E, 0xDF3E)`. The offset copy is filled with the brush built from
  `FUN_00508B3F(decode(dword@+0x23), 1, 50)`.
* **Shape.** `0x004AFE67` is the draw-time shadow of an object: it decodes `dword@+0x23`,
  tints it 50 % toward white, selects that brush, shifts the record's rectangle by
  `(0xDF3E, 0xDF3E)` and draws the record's polygon at the shifted rectangle. For marker
  `0x0004` it instead overwrites `dword@+0x21`/`word@+0x25` with the tinted colour, draws
  the line, and restores the six pen bytes.

The **setter** is the format-apply loop `0x004D02F9`, which walks a format-attribute table
by id: for attribute 0 it clears bit 0 when the attribute entry is absent or its style field
`(u16@entry+2 >> 8) & 0x1C` is not 4, and sets bit 0 otherwise; if bit 0 ends up set while
`+0x20` is still 0 it forces `+0x20 = 1` (an object with a shadow needs an explicit colour
object). That forcing is why the corpus identity *bit 0 ⇒ `+0x20 ≠ 0`* holds in 44/44
records — it is an invariant of the writer, not a coincidence.

`[OBSERVED]` — 44 of 22 354 records of markers `0x0000`–`0x0007` carry bit 0 (32 alone, 6
with `0x0005`, 4 with `0x0801`, 2 with `0x0805`); all 44 have `+0x20 ≠ 0`.

**No shadow value is stored, and no unassigned byte is consumed.** The complete byte set the
shadow path touches is `+0x06`…`+0x12` (rectangle), `+0x16` bit 0 (flag), `+0x20` (tested by
`0x004675F8` to choose the frame path), `+0x21`…`+0x26` (pen), `+0x29`…`+0x38` (frame
descriptor / line insets) and `+0x39` (dash/arrow) — every one of
which is assigned in this section. The colour is *derived*, not stored, so there is no
shadow colour slot to find: a reader that wants the shadow colour must compute
`tint50(decode_colorref(u32@+0x23))` and offset the rectangle by `(57 150, 57 150)` EMU.
`[OBSERVED, binary]`

The Publisher 97 binary carries the same mechanism at the corresponding VAs: `0x004CDC65`
(tint + offset copy, `FUN_005283CC(c, 1, 50)`), `0x0042ACAD` (frame shadow polygon),
`0x004B2885`/`0x004B28FD` (shadow damage region), `0x0046E413` (bounds inflation by
`0xDF3E`). `[OBSERVED, binary]`

### 6.7.6 The `+0x16` flag word

`+0x16` is a **bit field**, not a 16-member enum. The 17 values the corpus contains are the
combinations of eight independent bits. The bits are not all of one kind: 1, 5 and 6 are
runtime-only and never reach the file; 0, 3 and 4 are written by the Publisher 95 format
code; 8–11 appear in the file but have no writer in the Publisher 95 binary; 12 and 13 are
read by the 97/98 binaries and never set in this corpus.

| Bit | Mask | Records | Written at | Read at | Meaning |
|---|---|---|---|---|---|
| 0 | `0x0001` | 44 | `0x004D02F9` | `0x00411776`, `0x004675F8`, `0x004AFE67`, `0x00405740` | **shadow present** (§6.7.5) |
| 1 | `0x0002` | 0 | `0x004ADAD0`, `0x00438D7C`, `0x0044B740` | `0x00405C74`, `0x004280ED`, `0x004238CD`, `0x00439041`, `0x0042FAC5` | transient in-memory state |
| 2 | `0x0004` | 1 570 | `0x00416C82` | — none | bookkeeping copied from bit 1 |
| 3 | `0x0008` | 88 | `0x004D02F9` | `0x004177C3`, `0x004051D9`, `0x0040739B`, `0x00416AFB` | frame pair, with bit 4 |
| 4 | `0x0010` | 91 | `0x004D02F9` | same four | frame pair, with bit 3 |
| 5 | `0x0020` | 0 | — | `0x00420CAE`, `0x0046729D`, `0x004F269A` | outline source: smoothed polygon |
| 6 | `0x0040` | 0 | — | `0x004F269A`, `0x004F2554`, `0x004675F8` | outline is a **closed** point loop |
| 7 | `0x0080` | 0 | — | — | unused |
| 8 | `0x0100` | 394 | — | — none | only ever set together with bit 9 (394/394) |
| 9 | `0x0200` | 486 | — | `0x005A2901`, `0x00571C62` (98) | group-child bit (§ below) |
| 10 | `0x0400` | 2 | — | `0x0044041F` (97) | pen colour taken from `+0x23` |
| 11 | `0x0800` | 289 | `0x004217A7`, `0x0042453B` | `0x004217A7`, `0x0042453B`, `0x0042D6A8` (97) | group-child bit (§ below) |
| 12 | `0x1000` | 0 | — | `0x00480E84`, `0x00483EB6` (98) | dialog option: the second of a two-way choice |
| 13 | `0x2000` | 0 | — | `0x0045140D` (97), `0x004F5E26` (98) | the width bytes are **point counts**, not width codes |

`[OBSERVED]` — counts over 22 354 records of markers `0x0000`–`0x0007` in the four corpora.
"Written at" names the VA that stores the bit into a **chunk record** (not into the
0x60-byte property struct, which carries its own, unrelated `+0x16` word).

**Bit 1 is not persisted.** It is 0 in all 22 354 records. It is a transient in-memory flag:
`0x004ADAD0` sets it (`| 2`) around a call to `0x0044739B` and then restores the previous
value, `0x00405C74` is a one-line getter for it, the click handler `0x004280ED` tests it
before selecting, the walkers `0x004238CD`/`0x00439041`/`0x0042FAC5` act only on records
that carry it, and the paste path `0x00438D7C` clears it (`& 0xFFFD`) on the copy. It exists
only between load and save.

**Bit 2 has no reader and no setter.** A full scan of the three decompiled executables —
MSPUB.EXE 95 (3 825 functions), MSPUB.EXE 97 (4 252), MSPUB.EXE 98 (5 360) — finds no read
of mask `0x0004` (byte or word form, including the `& 6`/`& 0xC`/`& 0x1C` combinations) on a
chunk record, and no store that *sets* it: the only stores that touch bits 0–2 are the
`bit 2 := bit 1` sync at `0x00416C82` (95) and its 98 twins `0x00492A72`/`0x00502369`, which
write `flags & 0xFFFB | (flags & 2) << 1`. The other modules were checked and contain no
reference to the flag word at all: PUBDLG.DLL 95 (57 functions), PUBOLE32.DLL 95 (207,
`C:\pwrk\decomp-ole95`), MSPUBW32.DLL 95 (608, `C:\pwrk\wiz95` — only five functions touch
any `+0x16` and all five are rectangle/metafile arithmetic) and QS98.DLL (2 103,
`notes/p98q/decomp_quill`). `[OBSERVED]`

What the writer does is therefore the whole story: the sync routine walks the children of
the current selection and copies bit 1 into bit 2; bit 1's only setter, `0x004ADAD0`, sets
it around a call to `0x0044739B` and restores the previous value. Bit 2 is thus a snapshot
of a transient flag taken by an object-modifying command (`0x00416CD7`, `0x004E4CD4`,
`0x004A7C28`, `0x004C5650`), serialised by the writer and consumed by nobody.
`[INFERENCE]` for the name, `[OBSERVED]` for the code.

**Bits 3 and 4 are a pair.** The writer is `0x004D02F9` case 1 (format attribute id 1): it
computes one boolean `x` (the attribute entry exists and its style field
`(u16@entry+2 >> 8) & 0x1C` equals 4), then executes `bit 3 := x` and `bit 4 := x` — the same
value twice, which is why the corpus identity *bit 3 ⇒ bit 4* holds 88/88. They occur only
on markers `0x0002`/`0x0003` (88 and 91 records; the 3 bit-4-only records are Publisher 95
marker-3 records written before the pair was synchronised).

The reader switch, in `0x004177C3` (and identically in 97 at `0x0045140D`):

| Case label | Action |
|---|---|
| `marker == 6` | draw with `0x004675F8` (the frame renderer) |
| `marker ∈ {2, 3}` **and** bit 3 **and** bit 4 | same call, `0x004675F8` |
| `marker ∈ {2, 3}`, either bit clear | fall through to the ordinary polygon/text path |

and in the predicate `0x004051D9` the same case list returns **0** ("this record has no
frame border"), i.e. the pair is what makes a marker-2/3 record answer "I am a frame".
`0x0040739B` dispatches those records to the frame hit-test `0x004731EA`, `0x004AFE67`
draws their shadow through the same frame path, and `0x00416AFB` uses bit 3 alone to send
them to the marker-6 property conversion (`0x004797CD`). `[OBSERVED]` for the writer, the
case labels and the actions; `[INFERENCE]` for the reading "the record is a framed picture
rather than a plain polygon".

**Bits 5 and 6 are read but never written.** Bit 6 is the *closed loop* flag of the outline
smoother: `0x004F269A` computes the point count as `n − (bit 6 ? 1 : 0)` and, when bit 6 is
set, seeds the walk with point 0 as the predecessor of point 0; `0x004F2554` uses the same
flag to decide whether the neighbour of the last point is the first; `0x004675F8` branches
on it to pick the frame outline. Bit 5 selects the outline source: `0x00420CAE` takes the
record's counted tail (`u16@(B + chunk)`, §6.4) when bit 5 is clear and the smoothed
outline when it is set. No store sets either bit in MSPUB.EXE 95/97/98, and no corpus record
carries them (0/22 354), so both branches are unreachable in this family: the code is
generic, the versions never select it. `[OBSERVED]` for the switches and the absence; a
reader that sees either bit set should honour it as documented here.

**Bits 8–13 are *interpretation* flags for the record's own values.** Each one is consumed by
a switch that chooses between "read the byte as an index into a table" and "read the byte as
a literal", which is what makes them provable rather than correlated:

* **Bit 13** (`0x2000`) — `0x0045140D` (97) and `0x004F5E26` (98) both branch
  `if ((flags & 0x2000) == 0) width = table(byte@+0x2B) else width = byte@+0x2B * 0x319C`,
  and `0x319C` = 12 700 EMU = 1 pt. The 98 site repeats the same two-way branch for all four
  of its width bytes (`+0x2A`, `+0x35`, `+0x3B`, `+0x41`). So bit 13 means "these bytes are
  point counts, not width codes". Never set in the corpus.
* **Bit 10** (`0x0400`) — `0x0044041F` (97) branches `if ((flags & 0x400) == 0) colour =
  palette[0] else colour = decode(dword@+0x23)`, and the 98 dialog initialiser `0x00483EB6`
  branches the same way on `flags >> 10 & 1` to decide whether to copy `dword@+0x2B` into
  the dialog's colour slot. So bit 10 means "the pen colour comes from the record" rather
  than from the default. Set in 2 records, both `0x0005` in `SCHCLUB.PUB`.
* **Bit 12** (`0x1000`) — `0x00483EB6` builds a radio-button id as
  `(flags & 0x1000) >> 12 | 0x197A` and passes it to `CheckRadioButton(hDlg, 0x197A,
  0x197B, …)`: the bit is the *second* of a two-way choice in the fill/line dialog, and
  `0x00480E84` reads the same bit to pick a rendering mode. Never set in the corpus.

**Bits 9 and 11 are group-child bits.** They are 100 % confined to records whose parent is
a `0x000F` group: bit 9 in **486/486** records, bit 11 in **289/289**. They are the only
bits of the word that the Publisher 97/98 binaries read on a chunk record:
`0x004217A7` and `0x0042453B` clear bit 11 (`& 0xF7FF`) on the destination of a duplicate
and re-set it (`+0x17 |= 8`) only when the re-link through `0x004B555B` fails; `0x0042D6A8`
calls `FUN_004B5512` on the record when bit 11 is set; the 98 binary's `0x005A2901` returns
1 early for a bit-9 record and `0x00571C62` saves the bit into a work structure. Bit 8 is
never set without bit 9 (394/394) and occurs only in the Publisher 98 corpus on marker
`0x0005` (the `0x0300` value). `[OBSERVED]` for the identities and the VAs. No located
switch reads either bit as a value — the 97/98 sites only test presence and copy it — so
what the bits *select* is not established, and the Publisher 95 binary reads neither of
them. A reader must preserve them.

### 6.7.7 The colour pair `+0x18` / `+0x1C` and the selector `+0x20`

Three adjacent fields form one block: a colour reference at `+0x18`, a second at `+0x1C`,
and a selector byte at `+0x20`. `0x0041762A` is the whole reader — it loads the three and
calls `FUN_00417684(HDC, +0x20, u32@+0x18, u32@+0x1C, 0)`, which decodes both references
through the colour switch (`0x00418364`), sets the text colour (`0x00408140`), sets the
background colour (`0x0040CC46`), sets `BkMode` to transparent, and selects the cached
colour object chosen by `+0x20` (§6.6). `0x004177C3` calls it immediately before drawing
the record's text, and `0x004271FA` and `0x004B0525` use the same triple. `[OBSERVED,
binary]`

The writer is the format-apply loop `0x004D02F9` case 2, which calls
`FUN_004CFC4B(entry, record + 0x18, …)`; that function fills three sub-fields: `+0x18` from
the first sub-entry (0 when absent), `+0x1C` from the second (forced to **1** when absent),
and the byte at `+0x20` from the third. `[OBSERVED, binary]`

Corpus identity, 21 925 / 21 925 records of markers `0x0000`–`0x0007` whose `B` byte is the
95/97 value: `u32@+0x18` is either `0` or a value the colour switch accepts (7 001 non-zero,
14 924 zero), and `u32@+0x1C` is `0`, `1` or such a value (20 810 are `1`). No record
carries anything else. `tools/validate.py` enforces this as `shape_colour_pair`.
`[OBSERVED]`

The names — *text colour* and *text background colour* — are `[INFERENCE]` from the
`SetTextColor`/`SetBkColor` pair the reader performs; the offsets and the domains are
`[OBSERVED]`. This block is the real "fill/colour" trio that libmspub's `+0x2A` claim was
looking for (§6.5).

### 6.7.8 The marker-`0x0004` inset quad: `+0x29` … `+0x38`

`0x00405740` reads **four** `i32` from `+0x29`, `+0x2D`, `+0x31`, `+0x35` and passes them to
`0x00405A1A`, which treats them as `(left, top, right, bottom)` *insets* of the rectangle
(`left -= a`, `top -= b`, `right += c`, `bottom += d`, each clamped). The chapter's
12-byte frame descriptor (§6.7.3) therefore has a fourth dword, and for `0x0004` — a line —
the whole 16-byte run is the line's half-width inset quad: the insets are the line width
projected on each axis. `[OBSERVED, binary]`

Corpus identity over the 2 785 `0x0004` records: `top + bottom` equals the width decoded
from `+0x22` (§6.7.1) in 1 467 records (e.g. width code `0x01` = 12 700 EMU → `6 350 + 6 350`
in 976 records, `0x04` → `25 400 + 25 400` in 205, `0x81` → `1 587 + 1 588` in 62), and
`left + right` equals it in a further 434; the 45° records show the projection factor
(4 490 = 6 350 · cos 45°). The 848 records whose insets are all zero are lines whose
hit-test rectangle is the geometric box itself. `[OBSERVED]`

### 6.7.9 What is *not* in the record

There is no shadow colour, no shadow offset, no fill-type byte at `+0x2A` and no line-flag
quad at `+0x40`. Every byte the draw, hit-test and shadow paths consume is listed in the
table at the head of §6.7. A reader must preserve every other byte of the record.
`[OBSERVED]`

## 6.8 Validation

`tools/validate.py` checks, over all 493 documents:

| Check | Result |
|---|---|
| `record_length_byte`: `B` matches the per-marker constant | 0 violations |
| `record_min_size`: `size ≥ fixed base` | 0 violations |
| `shape_bbox_ordered`: `l ≤ r`, `t ≤ b` | 0 violations |
| `shape_bbox_magnitude`: \|coordinate\| < 400 in | 0 violations |
| `shape_colour_ref`: `u32@+0x23` decodes under the colour switch | 0 violations (21 925 records) |
| `shape_colour_pair`: `u32@+0x18` is `0` or decodes; `u32@+0x1C` is `0`, `1` or decodes | 0 violations (21 925 records) |
| `shape_text_colour`: `u32@+0x70` is a reference or `0xFFFFFFFF` | 0 violations (3 633 records) |
| `shape8_tail`: `0x0008` count pair, element size 2, `size = 0x80 + 2·count` | 0 violations (114 records) |

The three colour checks are gated on the Publisher 95/97 length byte (§6.3): a record
whose `B` is one of 92/96/116/116/59/62/53/41 has the 95/97 field layout at `+0x23`. The
Publisher 98 layout (`B + 8`) is rejected by the gate rather than by a second offset table,
because the Publisher 98 corpus contains five documents and the shifted offset is not yet
proven. `shape8_tail` is not gated: `0x0008` exists only in the Publisher 98 corpus.
`[OBSERVED]`

## 6.9 Open

* **The per-document constant `A` for `0x0002`/`0x0003`** — re-scoped. The storage is known
  (chapter 02 §2.5.1) and the value set is now measured over every version:

  | Corpus | `A(0x02)` | documents |
  |---|---|---|
  | `p95/x` | `0x8C` 1, `0x90` 64, `0x98` 15, `0x9C` 50 | 130 |
  | `p97/x` | `0x9C` 59, `0xA4` 49 | 108 |
  | `p97deluxe/x` | `0x9C` 165, `0xA4` 81, both 4 | 250 |
  | `p98/x` | `A(0x03)` = `0xBE` | 5 |

  `[OBSERVED]` The value is **not** a function of any single byte: an exhaustive scan of
  all 574 header bytes (`0x00`–`0x23D`) and all 117 DOCUMENT-chunk bytes (`0x00`–`0x74`)
  over the 130 Publisher 95 documents, plus every pair of DOCUMENT bytes and every byte of
  every chunk type that occurs exactly once in ≥ 120 documents, finds **only the header
  cells `0x36`/`0x40` themselves** as perfect predictors (i.e. the cache, not a source).
  The cache cells are exact: the `u16` at header `+0x36` equals `(B<<8) | A` of the
  `0x0002` records and the `u16` at `+0x40` equals `(B<<8) | A` of the `0x0003` records in
  **488/488** documents — i.e. the low byte of the cache word is the record's `A`, the high
  byte its `B`. So a reader can obtain the expected descriptor without scanning the chunks,
  and a writer that changes one must change both. `[OBSERVED]`
  Seven documents carry two different `A(0x03)` values — `BUSNESGO.PUB`,
  `CATALOG.PUB`, `RESTRM.PUB`, `binder1`–`binder3.pub`, `giftcer2.pub` — and the second
  value always equals `A(0x02) + 2` of a *different* lineage (`binder1.pub`: header cell
  and every `0x0002` say `0xA4`, yet its `0x0003` chunks are split between `0x9E` and
  `0xA6`). So `A` is copied with a pasted polygon and is not recomputed at save.
  `[OBSERVED]`

  Closed as **proven write-only / opaque**: no code path in any shipped module reads the
  value. A full scan of the three decompiled executables — MSPUB.EXE 95 (3 825 functions
  in `C:/pwrk/decomp95`), MSPUB.EXE 97 (4 252 in `notes/p98/decomp97`), MSPUB.EXE 98
  (5 360 in `notes/p98/decomp98`) — finds zero value-uses of the `+0x02` byte of a
  `0x0002`/`0x0003` record (no compare, no branch, no copy-out; the only contact is the
  writer-side store of the template constant), and the two shipped DLLs contain no reader
  either (PUBDLG.DLL 95, 57 functions in `C:/pwrk/dlg95`; PUBOLE32.DLL 95, 207 functions
  in `C:/pwrk/decomp-ole95`). Consequence: a reader MUST take the descriptor from the
  record's own `B` byte and, where the expected `A` is needed, from the header cache
  cells `+0x36`/`+0x40` (exact in 488/488); a writer MUST copy the per-document template
  entry (`0x00593308`, stride `0x36`) into both the record's `+0x02` and the matching
  header cell and preserve the value verbatim — never derive, validate, or normalise it.
  `[OBSERVED, negative]`

* The **identity** of the 8 bytes Publisher 98 inserts — closed. Its *position* was §6.3
  (an insertion in `+0x1C … +0x2A`, not an append; it moves `+0x23`, the pen colour, out
  of the 95/97 position, which is why `shape_colour_ref` is gated on the 95/97 `B`
  byte); its *content* is the §6.3 decomposition (`+0x20 = 0xC0E40000` unset-colour
  sentinel, `+0x24 = 0xC0E40007` same doublet family, `+0x28 … +0x2B` pen block)
  consumed by the 98 readers at VAs `0x0042AF42`/`0x00429A08` with widths through
  `0x004547F1`. No finer field split is claimed — the run's interior 32-bit boundaries
  are proven opaque (byte-packed body, §6.3). `[OBSERVED, binary]`
