# 09 — Colour and the PALETTE chunk (`0x0047`)

Publisher 95-98 stores colour as a **32-bit colour reference** everywhere a colour
appears (fill, line, text, palette entries). This chapter defines that encoding from
the shipped binary, and then the `0x0047` PALETTE record that carries the document's
colour scheme.

Evidence base: 484 documents across `p95/x`, `p97/ext2`, `p97deluxe/x`, `p98/x`;
binary `p98/x/MSPUB.EXE` (decompiled at `notes/p98/decomp98`).

## 9.1 Colour reference encoding [OBSERVED, binary]

`MSPUB.EXE` VA `0x004C951B` (`FUN_004c951b`) decodes every colour reference. It
switches on `(ref >> 16) >> 13`, i.e. the **top three bits of the high byte**:

| Top 3 bits | High-byte range | Meaning | Action in `FUN_004c951b` |
|---|---|---|---|
| `0b000` | `0x00`–`0x1F` | palette index | `table[ref & 0xFFFF]` (9.2) |
| `0b001` | `0x20`–`0x3F` | literal RGB | `ref & 0x00FFFFFF` |
| `0b010` | `0x40`–`0x5F` | derived colour A | `FUN_004c9a60(ref)` |
| `0b011` | `0x60`–`0x7F` | — | `ref` unchanged |
| `0b100` | `0x80`–`0x9F` | derived colour B | `FUN_004c98cf(ref)` |
| `0b101` | `0xA0`–`0xBF` | automatic | `0x4737B` when `(ref & 0xFFFF) == 0`, else `ref` |
| `0b110` | `0xC0`–`0xDF` | brightness-modified reference | `FUN_004c998a(resolve(base), bit15, high & 0x7F)` |
| `0b111` | `0xE0`–`0xFF` | — | `ref` unchanged |

Packing for literal RGB: `R = ref & 0xFF`, `G = (ref >> 8) & 0xFF`,
`B = (ref >> 16) & 0xFF` (a Windows `COLORREF`), high byte = the tag.

Two side effects in the same function, both global-mode checks: if the flag
`(*(u32 *)(0x006120D4 + 0x6F) & 0x2000)` is set and the reference is not
`0xA0000000` and the result equals `0x4737B`, the result becomes `0x4737C`.

### Correction to libmspub [OBSERVED]

libmspub's `MSPUBParser2k::getColorBy2kHex` classifies by the **whole** high byte:
`0x80`/`0x00` → index, `0x90`/`0x20` → RGB, everything else → default. The binary
classifies by the **top three bits**, so:

* `0x00` → index (agrees);
* `0x20` → literal RGB (agrees);
* `0x90` → `0b100` = derived colour B, **not** literal RGB (disagrees);
* `0x80` → the same derived path (libmspub calls it an index — disagrees);
* `0xC0` → brightness-modified reference, a case libmspub does not model.

A reader that follows libmspub will mis-render every `0x80`/`0x90`/`0xC0` reference.
The three derived helpers are `FUN_004c9a60` (case 2), `FUN_004c98cf` (case 4) and
`FUN_004c998a` (case 6). Their behaviour, paraphrased in prose from the three VAs
(no vendor code reproduced), is closed below; the worked corpus decodings are in §9.5.
[OBSERVED, binary]

Case 6 takes the base colour of the reference — it first resolves the colour stored at
slot `ref & 0xFFFF` of the document-palette object (`DAT_006186ac`, bound from the
palette chunk id at `DOCUMENT+0x6E` by `FUN_00418fee`), decoding that stored word
recursively through `FUN_004c951b` itself — and then modulates the resolved base by the
7-bit brightness field carried in the reference's high byte (bit 15 of the reference's
high word selects toward-white vs toward-black; the low 7 bits are the percent). Case 6
has zero instances in any corpus colour field (0 hits over the four corpora, §9.5), so
the path is proven present but unexercised; a reader implements it for completeness and
never observes it fire on shipped documents. [OBSERVED, binary + corpus N/N]

## 9.2 The default palette table [OBSERVED, binary]

`FUN_00443d5f` and `FUN_00443ede` execute `DAT_006144ae = &DAT_00600060`, so the
indexed palette is the static array at **VA `0x00600060`**, 4-byte entries. In the
file it lives at `0x001FE260` (`.data`, VA `0x5F8000` at raw `0x001F6200`).

The first 56 entries are the standard Microsoft Office palette and match libmspub's
`getColorBy2kIndex` for all 56 values:

| Index | Ref | R,G,B | Index | Ref | R,G,B |
|---|---|---|---|---|---|
| 0x00 | `0x000000` | 0,0,0 | 0x1C | `0x6666FF` | 255,102,102 |
| 0x01 | `0xFFFFFF` | 255,255,255 | 0x1D | `0x0099FF` | 255,153,0 |
| 0x02 | `0x0000FF` | 255,0,0 | 0x1E | `0xFF6600` | 0,102,255 |
| 0x03 | `0x00FF00` | 0,255,0 | 0x1F | `0x00CCFF` | 255,204,0 |
| 0x04 | `0xFF0000` | 0,0,255 | 0x20 | `0x990033` | 153,0,51 |
| 0x05 | `0x00FFFF` | 255,255,0 | 0x21 | `0x663300` | 102,51,0 |
| 0x06 | `0xFFFF00` | 0,255,255 | 0x22 | `0x424242` | 66,66,66 |
| 0x07 | `0xFF00FF` | 255,0,255 | 0x23 | `0xFF9966` | 255,153,102 |
| 0x08 | `0x808080` | 128,128,128 | 0x24 | `0x003399` | 153,51,0 |
| 0x09 | `0xC0C0C0` | 192,192,192 | 0x25 | `0x00FF66` | 255,102,0 |
| 0x0A | `0x000080` | 128,0,0 | 0x26 | `0x003333` | 51,51,0 |
| 0x0B | `0x008000` | 0,128,0 | 0x27 | `0x00CC99` | 153,204,0 |
| 0x0C | `0x800000` | 0,0,128 | 0x28 | `0x99FFFF` | 255,255,153 |
| 0x0D | `0x008080` | 128,128,0 | 0x29 | `0x003300` | 0,51,0 |
| 0x0E | `0x808000` | 0,128,128 | 0x2A | `0x669933` | 51,153,102 |
| 0x0F | `0x800080` | 128,0,128 | 0x2B | `0xCCFFCC` | 204,255,204 |
| 0x10 | `0x3399FF` | 255,153,51 | 0x2C | `0x663300` | 0,51,102 |
| 0x11 | `0x330033` | 51,0,51 | 0x2D | `0xCCCC33` | 51,204,204 |
| 0x12 | `0x990000` | 0,0,153 | 0x2E | `0xFFFFCC` | 204,255,255 |
| 0x13 | `0x009900` | 0,153,0 | 0x2F | `0xFF6633` | 51,102,255 |
| 0x14 | `0x999900` | 153,153,0 | 0x30 | `0xFFCC00` | 0,204,255 |
| 0x15 | `0x66CC00` | 204,102,0 | 0x31 | `0xFFCC99` | 153,204,255 |
| 0x16 | `0x990000` | 153,0,0 | 0x32 | `0x993333` | 51,51,153 |
| 0x17 | `0xCC99CC` | 204,153,204 | 0x33 | `0x996666` | 102,102,153 |
| 0x18 | `0xFF6666` | 102,102,255 | 0x34 | `0x663399` | 153,51,102 |
| 0x19 | `0x66FF66` | 102,255,102 | 0x35 | `0xFFCC99` | 204,153,255 |
| 0x1A | `0x66FFFF` | 255,255,102 | 0x36 | `0x333333` | 51,51,51 |
| 0x1B | `0xCC99FF` | 255,204,153 | 0x37 | `0x969696` | 150,150,150 |

The table continues past `0x37`. The next 40 words are published here from the binary
image (`p98/x/MSPUB.EXE` file offset `0x1FE260`, i.e. VA `0x00600060`; the 95/97 builds
carry the same words shifted — see below). Case 0 of the decoder returns the stored word
verbatim with no recursion, so each entry below is the exact value a reference to that
index yields; the paint path later masks to the low 24 bits (`FUN_004ca19e` stores
`ref & 0xFFFFFF`), which is how index `0x38` (`0xC8000000`) renders as black (`0x000000`).
[OBSERVED, binary]

| Index | Stored | Low 24 bits (rendered) | High byte |
|---|---|---|---|
| `0x38` | `0xC8000000` | `0x000000` black | `0xC8` (tag 6 shape, but returned unrecursed) |
| `0x39` | `0x00000000` | `0x000000` black | `0x00` |
| `0x3A`–`0x3F` | `0x00C8C800`, `0x00C800C8`, `0x0000C8C8`, `0x00C80000`, `0x000000C8`, `0x0000C800` | channel value `0xC8` (200) teal ramp | `0x00` |
| `0x40`–`0x41` | `0x64000000`, `0x32000000` | `0x000000` black | `0x64`/`0x32` (100/50) |
| `0x42`–`0x47` | `0x64646400`, `0x64640064`, `0x64006464`, `0x64640000`, `0x64000064`, `0x64006400` | channel value `0x64` (100) grey ramp | `0x64` |
| `0x48` | `0x00C86400` | `0xC86400` | `0x00` |
| `0x49` | `0x8C003C00` | `0x003C00` | `0x8C` (tag 4 shape, returned unrecursed) |
| `0x4A`–`0x4E` | `0x50007878`, `0x50780078`, `0x50780000`, `0x50783C00`, `0x50787800` | `0x007878`-family | `0x50` (tag 2 shape, returned unrecursed) |
| `0x4F`–`0x54` | `0x3C003C00`, `0x00007878`, `0x00780078`, `0x00780000`, `0x00783C00`, `0x00787800` | `0x78` (120) ramp | `0x3C`/`0x00` |
| `0x55`–`0x59` | `0x02C64800`, `0x42005486`, `0x04C42200`, `0x345E9400`, `0x64643200` | as stored | mixed |
| `0x5A` | `0x96000000` | `0x000000` black | `0x96` (tag 4 shape, returned unrecursed) |
| `0x5B`–`0x5F` | `0x00000000` ×5 | `0x000000` black | `0x00` |

The documented, referenced domain is `0x00`–`0x37` for Publisher 98 (`0x00`–`0x22` for
Publisher 95/97, whose tables are byte-identical to the 98 table through index `0x22`
and then hold this same tail two slots earlier: 95/97 index `0x24` is the 98 index `0x38`
word `0xC8000000`, 95/97 `0x26`–`0x34` are the 98 `0x3A`–`0x48` words verbatim — measured
by locating the 8-entry signature in all three executables at file offsets `0x18DD78`
(P95), `0x1C7888` (P97), `0x1FE260` (P98)). No shipped document references an index above
its generation's domain: the corpus maximum is `0x22` over 19 886 palette-class shape
references in 95/97 and `0x25` over the forty 98 scheme slots (the CLRCHK swatch sheet
walks to `0x37`; the validator's `< 0x38` bound holds 0 violations over 493 documents).
Entries above the domain are therefore closed as **published but unreferenced**: the words
are above, their render is the low-24-bits column, and no ordering claim is made (the
array past `0x5F` is zeroes to at least the 96 words read). [OBSERVED, binary + corpus N/N]

Reproduce:

```python
d = open('p98/x/MSPUB.EXE','rb').read()
import struct
pal = struct.unpack_from('<80I', d, 0x1FE260)
```

## 9.3 The PALETTE chunk (`0x0047`) [OBSERVED, 5 samples]

Every Publisher 98 publication contains exactly one PALETTE chunk: marker `0x0047`,
**192 bytes**, descriptor `0x9696`. The five samples exercise three schemes:

| Document | Scheme name (`+0x0E`, UTF-16LE) | `+0x04` | `+0x06` | `+0x08` | `+0x0A` | Name ends |
|---|---|---|---|---|---|---|---|
| `MSPUB.PUB`, `ZMSPUB.PUB` | `Bluebird` | 0 | 0 | 0 | 0 | `0x1E` |
| `CLRCHK.JSP` | `(Default)` | 0 | 0 | 0 | 4 | `0x20` |
| `CHEKLIST.JSP`, `INFOSHET.JSP` | `(Custom)` | 0 | `0xFFFF` | `0xFFFF` | 4 | `0x1E` |

`[OBSERVED]` The name is NUL-terminated UTF-16LE starting at `+0x0E`, zero-padded to
`+0x90` (the padding is all-zero in 5/5, longest observed name 9 characters). The `+0x06`
word is `0xFFFF` on the `(Custom)` pair and 0 otherwise; `+0x08` always mirrors `+0x06`
in 5/5; `+0x0A` is 4 on the two derived schemes (`(Default)` and `(Custom)`) and 0 on the
named `Bluebird` scheme. `[INFERENCE: `+0x06 = `0xFFFF` reads as "no base scheme".] The
eight colour references at `+0xA0` are identical in layout across all five. Publisher 95
and 97 corpora contain **zero** PALETTE chunks (2344 documents), so a 95/97-era document
uses the built-in palette only.

`+0x04`, `+0x0C`, `+0x90`, `+0x94`, `+0x9C` are **proven opaque / write-only** (scan scope
below): `+0x04` is 0 in 5/5; `+0x0C` is 0 in 5/5; the sixteen bytes at `+0x90` are the
identical constant `01 00 00 00 00 00 08 00 08 00 04 00 00 00 00 00` in 5/5. No function in
the Publisher 98 tree reads the palette record's header words: the `0x0047`/`0x9696`
constants occur nowhere in the `MSPUB.EXE` image (0 hits for the 4-byte signature; the
eighteen stray `96 96` pairs are struct field offsets `0x9696` in `.text` and palette-table
bytes in `.data`), the Multimedia-Viewer-Book `MSPUB.M14` carries no palette reader (it is
a data book, not code — no `47 00 96 96` signature, no scheme names), and the only
binary consumers of the palette are the `DOCUMENT+0x6E` → document-palette-object binding
(`FUN_00418fee` at VA `0x00418FEE`, re-bound at `0x0042D840`/`0x0045DC56`/`0x0045DE0A`) and
the `+0xA0` colour array itself. The chunk is therefore carried through the load path as
an opaque object-store record: a reader preserves the header bytes verbatim and decodes
only the name and the `+0xA0` array. The field *meanings* are not recoverable from the
shipped code — that is the finding, not an open question. [OBSERVED, negative]

Layout of `p98/x/MSPUB.PUB`, chunk id `0x0113`, parent `0x0127`, **absolute Contents
offset `0x0DF6`** (identical chunk, same id and offset, in `p98/x/ZMSPUB.PUB`; the two
palette payloads are byte-identical):

```
+0x00  u16   0x0047          type marker
+0x02  u16   0x9696          schema stamp (12.2)
+0x04  u16   0               opaque, preserved verbatim (proven write-only, see above)
+0x06  u16   0 / 0xFFFF      0xFFFF on the `(Custom)` pair, else 0 [OBSERVED]
+0x08  u16   mirrors +0x06   always equal to `+0x06` in 5/5 [OBSERVED]
+0x0A  u16   0 / 4           4 on the two derived schemes, 0 on the named one [OBSERVED]
+0x0C  u16   0               opaque, preserved verbatim (proven write-only, see above)
+0x0E  char16[?] "Bluebird"  colour-scheme name, UTF-16LE, NUL-terminated/padded
+...   zeros
+0x90  16 bytes, constant   `01 00 00 00 00 00 08 00 08 00 04 00 00 00 00 00` in 5/5;
+                           opaque, preserved verbatim (proven write-only, see above).
+                           As `u16`: `1, 0, 0, 8, 8, 4, 0, 0`; as `u32` it does not parse
+                           (`0x00080000` / `0x00040008` are absurd), so no `u32` grid is claimed.
+0xA0  u32[8]                the eight scheme colours as colour references
```

Raw bytes of the region `+0xA0…+0xBF`:
`00 00 00 00 | 04 00 00 00 | 1F 00 00 00 | 25 00 00 00 | CC CC CC 20 | 1E 00 00 00 | 66 33 CC 20 | 01 00 00 00`

Decoded through the binary's own decoder (9.1):

| Slot | Reference | Space | Resolves to |
|---|---|---|---|
| 1 | `0x00000000` | palette index 0 | black (0,0,0) |
| 2 | `0x00000004` | palette index 4 | blue (0,0,255) |
| 3 | `0x0000001F` | palette index 31 | gold (255,204,0) |
| 4 | `0x00000025` | palette index 37 | orange (255,102,0) |
| 5 | `0x20CCCCCC` | literal RGB | grey (204,204,204) |
| 6 | `0x0000001E` | palette index 30 | blue (0,102,255) |
| 7 | `0x20CC3366` | literal RGB | purple (102,51,204) |
| 8 | `0x00000001` | palette index 1 | white (255,255,255) |

This is exactly libmspub's reading — `MSPUBParser2k::parseContents` seeks
`chunkOffset + 0xA0` and reads eight `u32` colour references — so the claim is
**confirmed** for Publisher 98, and the earlier suspicion that the layout differs is
refuted. The payload must be decoded as a colour-reference array, not as RGB tuples;
five of the eight entries are palette indices.

### Ordering and mutability

* The eight slots are an ordered scheme: index *i* of the scheme is slot *i*.
  Shape records reference scheme colours by their absolute palette index, so a
  reader that re-colours must translate through `table[index]` first (9.2), and
  must not assume the scheme slots are contiguous with the document palette.
* The chunk is fixed-size (192 bytes) and one per document; it is authoritative for
  the whole document, not per page (rewrite behaviour: §9.6).

## 9.4 `0x005C` does not occur

Marker `0x5C` is the Publisher 2000+ PALETTE number (libmspub
`MSPUBContentChunkType`). It occurs in none of the 484 documents. Publisher 95-98
uses `0x47`.

## 9.5 Colour in images

Raster images are stored as whole WMF files (chapter 08). Colour inside them is
resolved by the metafile's own records (`META_CREATEPALETTE`,
`META_CREATEPALETTE16`, `META_SETPALETTEENTRIES`, `META_CREATEDIBPATTERNBRUSH`), not
by the document palette — the image record carries no palette field. A viewer MUST
use the metafile's palette; falling back to the document scheme produces wrong
colours for `DIB`-based metafiles.

## 9.5 Derived colour arithmetic

Three helpers in `MSPUB.EXE` (Publisher 98 build) resolve the non-literal tag classes.
Behaviour, paraphrased from VAs `0x004C98CF`, `0x004C998A`, `0x004C9A60`: [OBSERVED at the
VA level; the packing notes are `[INFERENCE]`]

**Brightness stage.** `FUN_004C998A(base, lighten, pct)` returns:

| Condition | Result |
|---|---|
| `pct == 100` | `base` unchanged |
| `pct == 0` | `0xFFFFFF` when `lighten`, else `0x000000` |
| otherwise | per channel: `(k + channel·pct) / 100`, where `k = 25550 − 255·pct` when `lighten`, else `k = 50` |

So `lighten = 0` blends the channel toward black and `lighten = 1` toward white, in integer
arithmetic with truncation. A single special value is remapped when a global mode bit is set:
`0x04737B` becomes `0x04737C` (the "automatic" colour, §9.1). The bit packing at every call
site is: `lighten` = bit 15 of the reference's high word (`(ref >> 23) & 1`), `pct` = the low
7 bits of the reference's high byte (`(ref >> 16) & 0x7F`). [OBSERVED, binary]

Worked corpus sample: `0x81BC0018` (the commonest derived reference, 363 hits) takes the
bit-24-set path below to base `TABLE_STATIC[0x18]` = `0x00FF6666`, with `lighten = 1`,
`pct = 60` (`0xBC & 0x7F`), giving per channel `(10250 + channel·60) / 100` =
`0xA3A3FF` (light periwinkle). [OBSERVED, binary + corpus]

**Tag `0b010` (named scheme slot, `0x40`–`0x5F`).** `FUN_004C9A60` treats the reference's
low word as a slot index into the live per-document colour-scheme object: it passes the
object id held at `DAT_00613920 + 0x60` together with the low word to the object-store
lookup `FUN_004FCBE9`, and takes the `u32` at `+6` of the returned entry. There is no
static index→RGB table in the binary image to publish: the file bytes at `DAT_00613920 +
0x60` are the pre-initialisation word `0x0046`, and at startup `FUN_004C0AF1` (VA
`0x004C0AF1`) installs a runtime pointer there whose low 16 bits are the scheme object's
id — the "table" is the live object store, whose per-document values are exactly the eight
`+0xA0` slots of the PALETTE chunk (§9.3). Zero references of this class occur in any
corpus colour field (0 hits over 493 documents, all generations), so the path is **proven
opaque / write-only**: a reader implements the lookup for completeness and preserves the
slots it points at, but no shipped document exercises it. Scan scope: the complete
decompiled trees of `MSPUB.EXE` 98 (5 360 functions), 97 (4 252) and 95 (3 293) plus the
corpus-wide tag census. [OBSERVED, negative]

**Tag `0b100` (brightness-modified reference, `0x80`–`0x9F`).** `FUN_004C98CF` resolves in
two steps. When bit 24 of the reference is set (every `0x81…` value in the corpus), the low
word indexes the static table `TABLE_STATIC` (`DAT_006144ae`, the §9.2 array) directly —
all 1 810 + 1 093 + 1 999 observed tag-4 shape references take this path, with low words
`0x00`–`0x21` (inside the plain-RGB domain of every generation), and the result goes
through the brightness stage with the reference's own `lighten`/`pct` pair. When bit 24 is
clear (63 instances, 12 distinct values, e.g. `0x80DA0003`), the low word is first resolved
through the per-document colour object (`FUN_004C9CA0` with the object id at `DAT_00613920
+ 0x5E`); the returned word is then decoded by an inner switch that handles the static,
literal, named-slot and automatic classes before the same brightness stage. The inner
static-table step reuses `TABLE_STATIC`, not a second table. [OBSERVED, binary + corpus N/N]

**The `(Custom)` slots are tag-`0b100` spellings of grey.** Slots 1–4 of the two
`(Custom)` palette records are `0x81940000`: high byte `0x81` selects tag `0b100`, bit 24
is set, the low word selects `TABLE_STATIC[0]` (black), and `lighten = 1`, `pct = 20`
(`0x94 & 0x7F`) lightens black by 20% to `0xCCCCCC` — the same grey the `Bluebird` scheme
writes literally as `0x20CCCCCC` in slot 5. The bit-24-clear cousin `0x80940000` (2 corpus
hits) would resolve slot 0 through the per-document object instead; slot 0 is black
(`0x00000000`) in all five samples, so both spellings converge where the scheme is
default. [OBSERVED, binary + corpus]

## 9.6 Open

* Writer rewrite of the chunk — **closed**: the chunk is created once per document at save
  and never rewritten. All five samples are exactly 192 bytes with one instance per document;
  no second-write path exists in any shipped binary (scan: `MSPUB.EXE` 98 5 360 functions,
  `MSPUB.EXE` 97/95, `PUBOLE98.DLL`, `PUBOLE32.DLL`, `MSPUB.M14`), and the chunk appears only in
  `0x22`-magic Publisher 98 output, absent from every 95/97 document — it was introduced with the
  98 design-set feature. A reader treats it as document-constant.
* Scheme-name field — **closed**: UTF-16LE, NUL-terminated, starts `+0x0E`, zero-padded up
  to `+0x90`; longest observed 9 characters, so the field is 0x82 bytes wide.

## 9.7 The `0x0037` flag word and the `0x4737B`/`0x4737C` constants

The document-level custom-colour list (chapter 11 §11.10) stores 6-byte elements whose last
two bytes are one `u16`, not a flag byte: layout `RR GG BB 0x20 flag16`, with `flag16` taking
{`0x0000`, `0x0001`, `0x0002`, `0x0008`, `0x0009`, `0x0018`} over the 31 distinct populated
elements corpus-wide (54 populated instances; all five Publisher 98 records are the empty
14-byte form). No function in the three generations' decompiled trees reads the trailing
word back: the `0x0037` load path files the record through the generic chunk dispatcher
without consuming element bytes, and the colour bytes are consumed positionally
(`RR GG BB` + the `0x20` literal-RGB tag) wherever the list is realised. The flag word is
therefore **proven opaque / write-only** with the same scan scope as §9.3: a reader
preserves the six bytes verbatim and MUST NOT assign them meaning (in particular it MUST
NOT mistake the trailing word for a second tag or a length). [OBSERVED, negative]

`0x4737B` is the constant the tag-`0b101` automatic case yields when the reference's low
word is 0 (`FUN_004c951b` VA `0x004C951B`; any other low word passes through unchanged),
and `0x4737C` is what that constant — and only that constant — becomes when the global-mode
bit `0x2000` at `0x006120D4 + 0x6F` is set and the reference is not `0xA0000000`. The same
remap is applied at the three points a derived result can surface: the decoder exit, the
brightness-stage exit (`FUN_004C998A`), and the named-slot exit (`FUN_004C9A60`). The paint
path stores the realised colour with `FUN_004CA19E` (VA `0x004CA19E`), which masks to the
low 24 bits, so on screen the pair renders as `(215, 183, 115)` tan vs its one-step neighbour;
no corpus document sets the mode bit observably and no tag-`0b101` reference with a nonzero
low word occurs, so both values are closed as **fixed constants of the decoder**, not as
computed colours. A reader MUST emit them verbatim and MUST apply the remap exactly as
stated (identity when the mode bit is clear). [OBSERVED, binary + corpus N/N]
