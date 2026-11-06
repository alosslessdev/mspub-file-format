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
| `0x0008` | shape variant | 114 | `0x76` (118) | **128** | `+2k` (130, 132) and 148 observed |
| `0x0016` | document-level record, **not a shape** | 488 | `0x10` (16) / `0x12` (18) | 16 (P95, +1 P97 file), 18 (P97) | — |

`[OBSERVED]` — instance counts are the sum over `p95/x` (130 docs), `p97/x` (108),
`p97deluxe/x` (250) and `p98/x` (5).

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
insertion in the `+0x1C … +0x2A` region. `[OBSERVED]` for the four markers compared;
`[UNKNOWN]` the exact field — the inserted run in the Publisher 98 samples is
`00 E4 C0 07 00 E4 C0 00 00`, whose `E4 C0 00 00` component reads like a colour value and
suggests the 98 record gained explicit colour fields.

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
at `+0x74`/`+0x76`, elements of 8 bytes starting at `+0x78` (95/97). `0x0001` uses
14-byte elements (split into two runs by `u16@+0x4A` and `u16@+0x50`, which sum to the
count in 735/737 chunks). `0x0000` carries `+2k` with a duplicate pair `u16@+0x5C ==
u16@+0x5E == k` and an element size word `0x0002` at `+0x60`; its elements are **chunk ids
of sibling records** — 746/746 resolve to an existing id, 656/746 to a sibling. `0x0008`
appears only in the Publisher 98 corpus; its fixed base is 128 and the observed sizes are
128, 130, 132 and 148, but the tail framing there is `[UNKNOWN]` (see §6.9).

A parser must derive the element count from the duplicate pair and verify
`size == base + count · elem`. `[OBSERVED]` for every marker in the table.

## 6.5 Refuted prior art

Two widely repeated libmspub offsets do **not** hold for this family:

| Claim | Measurement |
|---|---|
| "fill type at `+0x2A`" | `+0x2A` is a per-type constant (`0xFF` for `0x0000`/`0x0003`, `0x00` for `0x0001`, absent for `0x0007`) |
| "line flags at `+0x41`" | `+0x41` is the high byte of the `u16` at `+0x40`, one of four inset/quad values |

`[OBSERVED]` — neither field carries fill/line information. Fill and line properties are
still `[UNKNOWN]` for these markers; the discriminating experiment is a controlled edit in
Publisher 95 (set a unique fill colour, save, diff every byte of the record).

## 6.6 Shared enums

`+0x20` and `+0x22` take the same small value sets under three different markers, so they
are **not** type discriminators: `+0x20` ∈ {0,1,2} and `+0x22` ∈ {0,1,2,4,8,12,0x1E,0x81}
in the Publisher 95 corpus. Their meaning is `[UNKNOWN]`; a reader must preserve them.

## 6.7 Per-byte field maps

The full per-byte value distribution for `0x0000`, `0x0001`, `0x0003` and `0x0007` is
recorded in `notes/p95/slices/shapeA.md` §4 (computed over the Publisher 95 corpus). The
records are dominated by a repeating pattern of `0x00` with a `0xFF 0xFE` sentinel around
`+0x29` and small enums at the positions above; every byte not described in this chapter is
`[UNKNOWN]` and must be preserved verbatim when rewriting a document.

## 6.8 Validation

`tools/validate.py` checks, over all 493 documents:

| Check | Result |
|---|---|
| `record_length_byte`: `B` matches the per-marker constant | 0 violations |
| `record_min_size`: `size ≥ fixed base` | 0 violations |
| `shape_bbox_ordered`: `l ≤ r`, `t ≤ b` | 0 violations |
| `shape_bbox_magnitude`: \|coordinate\| < 400 in | 0 violations |

## 6.9 Open

* Fill, line, shadow and text-link fields inside the record — `[UNKNOWN]`, with the
  controlled-edit experiment above.
* The per-document constant `A` for `0x0002`/`0x0003` — `[UNKNOWN]`, but its storage is now
  known: the `(A,B)` pair of every basic shape class is cached in the `Contents` header block
  (chapter 02 §2.5.1: cells at `0x26`, `0x2E`, `0x36`, `0x40`, `0x4A`, `0x52`, `0x5A`, `0x62`
  hold the pairs for marker `0x00`…`0x07`). `A(0x03) = A(0x02) + 2` in every file, and the four
  observed pairs (`0x8C/0x8E`, `0x90/0x92`, `0x98/0x9A`, `0x9C/0x9E`) are the four header
  variants. What *document setting* selects the value is still open.
* The **identity** of the 8 bytes Publisher 98 inserts. Its *position* is now known (§6.3):
  an insertion in `+0x1C … +0x2A`, not an append. Experiment: decode the inserted run
  `00 E4 C0 07 00 E4 C0 00 00` against a document with a known fill/line colour.
* The `0x0008` tail framing — `[UNKNOWN]`; sizes 128/130/132/148 and the base 128 are
  measured, the count pair is not located.
* Meaning of the `+0x16`/`+0x17` small enum shared by `0x0000`/`0x0003`/`0x0007`.
