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
`FUN_004c998a` (case 6); their arithmetic is `[UNKNOWN]` beyond the shape of the
call (case 6 = take the base colour of the reference, then modulate by the 7-bit
brightness field).

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

The table continues past `0x37`; those entries are themselves colour references in
other spaces (index 56 is `0xC8000000`, which selects the case-6 brightness path,
not a literal colour; indices 58–63 are 200-based tints, 64–71 are 100-based tints,
and the array continues to at least index 79). A reader MUST recurse on table entries
whose high byte is non-zero. The documented, referenced domain is `0x00`–`0x37`;
higher indices are `[UNKNOWN]` in order (the array is not terminated by an obvious
sentinel).

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
|---|---|---|---|---|---|---|
| `MSPUB.PUB`, `ZMSPUB.PUB` | `Bluebird` | 0 | 0 | 0 | 0 | `0x1E` |
| `CLRCHK.JSP` | `(Default)` | 0 | 0 | 0 | 4 | `0x20` |
| `CHEKLIST.JSP`, `INFOSHET.JSP` | `(Custom)` | 0 | `0xFFFF` | `0xFFFF` | 4 | `0x1E` |

`[OBSERVED]` The name is NUL-terminated UTF-16LE starting at `+0x0E`, zero-padded to
`+0x90` (the padding is all-zero in 5/5, longest observed name 9 characters). The two
`0xFFFF` words at `+0x06`/`+0x08` distinguish the "(Custom)" scheme from a named or
"(Default)" one `[INFERENCE: they read as "no base scheme"]; `+0x0A` is 4 on the two
"derived" schemes and 0 on the named one. The four `u32` slots at `+0x90…+0x9F` and the
eight colour references at `+0xA0` are identical in layout across all five. Publisher 95 and
97 corpora contain **zero** PALETTE chunks (2344 documents), so a 95/97-era document
uses the built-in palette only.

Layout of `p98/x/MSPUB.PUB`, chunk id `0x0113`, parent `0x0127`, **absolute Contents
offset `0x0DF6`** (identical chunk, same id and offset, in `p98/x/ZMSPUB.PUB`; the two
palette payloads are byte-identical):

```
+0x00  u16   0x0047          type marker
+0x02  u16   0x9696          schema stamp (12.2)
+0x04  u32   0               [UNKNOWN] always 0 in both samples
+0x08  u32   0               [UNKNOWN]
+0x0C  u16   0               [UNKNOWN]
+0x0E  char16[?] "Bluebird"  colour-scheme name, UTF-16LE, NUL-terminated/padded
+...   zeros
+0x90  u32   1               [UNKNOWN]
+0x94  u16   0               [UNKNOWN]
+0x96  u16   8               colour count
+0x98  u16   8               [INFERENCE] capacity / allocated count
+0x9A  u16   4               [INFERENCE] element size in bytes
+0x9C  u32   0               [INFERENCE] array offset relative to +0xA0
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
  the whole document, not per page.
* Whether the writer ever rewrites the chunk after creation is `[UNKNOWN]` — both
  shipped samples are the same scheme ("Bluebird"), so no immutability rule can be
  measured. The chunk's presence only in the `0x22`-magic 98 output and absence
  from 95/97 suggests it was introduced with the 98 design-set feature.

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
`0x04737B` becomes `0x04737C` (the "automatic" colour, §9.1).

**Derived spaces (tags `0x40`–`0x5F`, `0x80`–`0x9F`).** `FUN_004C98CF` maps the reference
through `FUN_004C9A60`, which looks the low word up in a table reached from
`DAT_00613920 + 0x60` and takes the `u32` at `+6` of the entry — an index→colour map, not
arithmetic. It then applies the brightness stage to the result.

**Not yet decoded.** The contents of that derived-space table (an index→RGB map) and the
exact bit packing the three call sites use for the brightness pair. Both are reachable from
the same three VAs; a decoded sample (one document using a theme/tint colour) would settle
them.

## 9.6 Open

* `+0x04`/`+0x08`/`+0x0C`/`+0x90`/`+0x94`/`+0x9C` — **[UNKNOWN]**; both samples are
  identical, so no differential is possible. Experiment: save a document in
  Publisher 98 with a renamed scheme and with modified colours, then diff; or find
  the reader in the binary (the palette parser is not in `MSPUB.EXE` — it is
  presumably inside `MSPUB.M14`, chapter 12 §12.8 and `notes/p98/slices/m14.md`).
* Scheme-name field — **closed**: UTF-16LE, NUL-terminated, starts `+0x0E`, zero-padded up
  to `+0x90`; longest observed 9 characters, so the field is 0x82 bytes wide.
* Derived-space table contents (index→RGB map reached from `DAT_00613920 + 0x60`) — the
  arithmetic around it is documented in §9.5; the table itself is `[UNKNOWN]`.
