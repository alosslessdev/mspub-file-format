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
+0x03  u8   B                writer-side fixed record length
+0x04  u16  rotation         1/100 degree, counter-clockwise
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

Rotation is a `u16` in **1/100 degree**, counter-clockwise. 25 non-zero instances occur in
the Publisher 95 corpus with values 100…3460, i.e. 1.00°…34.60°; across all corpora the
maximum observed is 3598. libmspub's model (tenths of a degree, `360 − v/10`) is wrong for
this family.

## 6.3 Marker table

| Marker | Class | Instances | Fixed base | Optional tail |
|---|---|---|---|---|
| `0x0000` | free-form shape | 5 086 | 102 | grows to 104/106/108 |
| `0x0001` | free-form shape (variant) | 752 | 106 | 14-byte elements |
| `0x0002` | image-bearing shape | 1 016 | 126 (95/97), 150 (98) | 8-byte elements at `+0x74` |
| `0x0003` | polygon shape | 2 627 | 126 (95/97), 150 (98) | 8-byte elements |
| `0x0004` | line | 2 785 | 59 (95/97), 67 (98) | — |
| `0x0005` | rectangle | 4 879 | 62 (95/97), 70 (98) | — |
| `0x0006` | embedded-object shape | 4 050 | 53 (95/97), 61 (98) | — |
| `0x0007` | smallest shape record | 1 159 | 41 (95/97), 49 (98) | — |
| `0x0008` | shape variant | 114 | 41 | Publisher 98 sample only |
| `0x0016` | document-level record, **not a shape** | 493 | 16 | — |

The Publisher 98 writer appends **8 bytes** to every shape record (24 to the
image-bearing `0x0002`/`0x0003`). All four geometry fields stay at the same offsets; the
extra bytes are at the end of the fixed part or in the tail — see the open items.

`0x0016` is a 16-byte per-document record holding the ids of four document-level chunks
(`0x001A`, `0x001C`, `0x002E`, `0x002D`) in fixed slot order, verified 128/128 in the
Publisher 95 corpus. It is not a shape and must not be transformed.

## 6.4 Counted tail

For `0x0002`/`0x0003` the tail is a counted array: `u16 count` and a duplicate `u16 count`
at `+0x74`/`+0x76`, elements of 8 bytes starting at `+0x78` (95/97). `0x0001` uses
14-byte elements. A parser must derive the element count from the duplicate pair and
verify `size == base + count · elem`.

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
* The per-document constant `A` for `0x0003` (four values: `0x8E`, `0x92`, `0x9A`, `0x9E`) —
  `[UNKNOWN]`; it varies with a document-level setting, not with the shape.
* Where exactly Publisher 98 inserts the 8 extra bytes.
* Meaning of the `+0x16`/`+0x17` small enum shared by `0x0000`/`0x0003`/`0x0007`.
