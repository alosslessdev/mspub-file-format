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
variants are `[UNKNOWN]`: the gallery instances carry a zero geometry quad at `+0x06`, so
no field can be derived from the corpus.

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
at `+0x74`/`+0x76`, elements of 8 bytes starting at `+0x78` (95/97). `0x0001` uses a
**contiguous** array of 14-byte elements from `+0x6A` with `N = (size − 106)/14`
(§6.4.1); two `u16` at `+0x4A` and `+0x50` partition that array into two runs and sum to
`N` in 735/737 chunks. `0x0000` carries `+2k` with a duplicate pair `u16@+0x5C ==
u16@+0x5E == k` and an element size word `0x0002` at `+0x60`; its elements are **chunk ids
of sibling records** — 746/746 resolve to an existing id, 656/746 to a sibling.
`0x0008` appears only in the Publisher 98 corpus; its fixed base is 128 and its trailer is
the same counted form as `0x0000` — duplicate count at `+0x76`/`+0x78`, element size word
`0x0002` at `+0x7A`, elements from `+0x80` (§6.4.2).

### 6.4.1 The `0x0001` 14-byte tail elements

The tail is contiguous from `+0x6A` (`size = 106 + 14·N`, 2 618 records in 259 chunks of the
493-document corpus). Each record is `{u32 a, u32 b, u32 c, u16 d}`: [OBSERVED]

| Field | Measurement | Reading |
|---|---|---|
| `a` `+0x00` | ascending horizontal positions in EMU; resets to a smaller value 259 times | tab-stop x `[INFERENCE]` |
| `b` `+0x04` | 529/2 618 (20.2 %) are exact multiples of 12 700 EMU (1 pt); quotients are plausible point sizes (9, 10, 11, 12, 13, 14, 15, 18, 30 … 54) | line height / font metric in EMU `[INFERENCE]` |
| `c` `+0x08` | equals `a − previous_a` within 2 EMU in 2 041/2 618 (78.0 %); exceptions are records after a reset and frames with absolute stops | width from the previous stop `[INFERENCE]`, not guaranteed |
| `d` `+0x0C` | `0xFFFF` ×2 174, `0` ×333, `1` ×59, `3` ×36, `2` ×12, `6` ×4 | run terminator plus style index `[INFERENCE]` |

The nine stops of the price-list table (chapter 10 §10.3) are the first run of records with
`d = 0xFFFF`, and their `c` values reproduce the inter-stop widths exactly.

A parser must derive the element count from the duplicate pair and verify
`size == base + count · elem`. `[OBSERVED]` for every marker in the table.

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

## 6.6 Shared enums

`+0x20` takes the same small value set {0, 1, 2} under every marker, so it is **not** a type
discriminator. At MSPUB.EXE 95 VA `0x004177C3` it is tested `!= 0` and gates the text
drawing of the record, and VA `0x0040DFBF` tests it against `0x80`/`0xAB` (values outside the
corpus); it is the **text-present byte**. `[OBSERVED]` for the value set (21 925 records of
markers `0x0000`–`0x0007`); `[INFERENCE]` for the name.

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
| `+0x16` | u16 | text/group flags (bits 0, 3, 4) | `0x004177C3` |
| `+0x20` | u8 | text-present byte | `0x004177C3`, `0x0040DFBF` |
| `+0x21` | u8 | pen style byte — `0x00` in 21 842 / 21 925, else `0x1E`/`0x1F` | `0x0042253E` |
| `+0x22` | u8 | line-width code | `0x0042253E`, `0x004B0C67`, `0x004675F8` |
| `+0x23` | u32 | **line colour reference** | `0x0042253E`, `0x004AFE67` |
| `+0x29` | i16 | frame border style (`0` = none) | `0x00418211`, `0x004675F8` |
| `+0x2B` | u16 | frame flags (bit 2 selects the inset axis) | `0x00418211`, `0x004675F8` |
| `+0x2D` | 8 | frame inset pair (`i32`, `i32`) | `0x00418211`, `0x004675F8` |
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
six bytes) when it hands it to the pen setup, and recolours the line for the text-link path
at VA `0x004AFE67` by overwriting `+0x23` and restoring the six bytes afterwards.
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
passes them to the polygon builder as a point. In `0x0005` this style word is
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

### 6.7.5 What is *not* in the record

The remaining `[UNKNOWN]` is the **shadow**: no offset of a shape record is read by a shadow
path in either binary, and no shadow-specific value appears in the corpus (§6.9). A reader
must preserve every byte not listed above. `[OBSERVED]`

## 6.8 Validation

`tools/validate.py` checks, over all 493 documents:

| Check | Result |
|---|---|
| `record_length_byte`: `B` matches the per-marker constant | 0 violations |
| `record_min_size`: `size ≥ fixed base` | 0 violations |
| `shape_bbox_ordered`: `l ≤ r`, `t ≤ b` | 0 violations |
| `shape_bbox_magnitude`: \|coordinate\| < 400 in | 0 violations |
| `shape_colour_ref`: `u32@+0x23` decodes under the colour switch | 0 violations (21 925 records) |
| `shape_text_colour`: `u32@+0x70` is a reference or `0xFFFFFFFF` | 0 violations (3 633 records) |
| `shape8_tail`: `0x0008` count pair, element size 2, `size = 0x80 + 2·count` | 0 violations (114 records) |

The two colour checks are gated on the Publisher 95/97 length byte (§6.3): a record
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
  `[OBSERVED]` Seven documents carry two different `A(0x03)` values — `BUSNESGO.PUB`,
  `CATALOG.PUB`, `RESTRM.PUB`, `binder1`–`binder3.pub`, `giftcer2.pub` — and the second
  value always equals `A(0x02) + 2` of a *different* lineage (`binder1.pub`: header cell
  and every `0x0002` say `0xA4`, yet its `0x0003` chunks are split between `0x9E` and
  `0xA6`). So `A` is copied with a pasted polygon and is not recomputed at save.
  `[OBSERVED]`

  Blocking fact: the save-time state that chooses `A` is not recorded anywhere else in the
  file. The experiment that would settle it: find the producer in the binary by searching
  for the store of `+0x02` while a record is built (the four constants are `0x8C`, `0x90`,
  `0x98`, `0x9C` and `A + 2`), then trace its input. `[UNKNOWN]`

* **Meaning of bits 2 and 4 of the `+0x16` word** — re-scoped. The measured identities are:

  | Identity | Count |
  |---|---|
  | value set has 16 members; `0x0000` in 20 043 / 21 925 | `[OBSERVED]` |
  | bit 0 set ⇒ byte `+0x20` ≠ 0 (text present) | 44 / 44 |
  | bit 9 (`0x200`) set ⇒ parent is a `0x000F` group | 92 / 92 |
  | bit 11 (`0x800`) set ⇒ parent is a `0x000F` group | 289 / 289 |
  | bit 3 set ⇒ bit 4 also set | 88 / 88 |
  | no correlation with rotation: bit 2 set 1 570 times, rotated 90 | — |

  `[OBSERVED]` Bit 6 (`0x40`) is absent from the 95/97 corpus and is read by VA
  `0x004F2554`/`0x004F269A` as "wrap text around the outline"; Publisher 98 sets `0x300`
  in `0x0005`. Blocking fact: what sets bit 2 (1 570 instances) and bit 4 (91 instances,
  35 of them rotated). Experiment: the shape-property UI writes the word back through VA
  `0x00416AFB`, so a breakpoint on that store names the toggle. `[UNKNOWN]`

* **Shadow.** No shape-record offset is read by a shadow path in either binary, and the
  corpus has no shadow-specific value; the two colour slots of `0x0005` are fill and line
  (§6.7.4), not shadow. Blocking fact: whether Publisher 95 stores shadows at all in this
  record family. Experiment: apply a shadow to a rectangle in Publisher 95, save, diff the
  `0x0005` record against the same rectangle without a shadow. `[UNKNOWN]`

* The **identity** of the 8 bytes Publisher 98 inserts. Its *position* is now known (§6.3):
  an insertion in `+0x1C … +0x2A`, not an append; it moves `+0x23` (the pen colour) out of
  the 95/97 position, which is why `shape_colour_ref` is gated on the 95/97 `B` byte.
  Experiment: decode the inserted run `00 E4 C0 07 00 E4 C0 00 00` against a document with
  a known fill/line colour.
