# Enums — colour

The complete colour domain of the Publisher 95/97/98 format, derived from the colour
decoder in the shipped binary (`MSPUB.EXE`, `FUN_004c951b` at VA `0x004C951B` and its
three helpers) and checked against the corpus. Every colour in a document — fill, line,
text, palette slot, custom-colour list — is a **32-bit colour reference** decoded by that
one function, so this file is the decoder contract.

## 1. The 32-bit colour reference

The tag is the **top three bits of the high byte**, i.e. `(ref >> 29) & 7`, which the
binary computes as `(u16)(ref >> 16) >> 13`. [OBSERVED, binary VA `0x004C951B`]

| Tag | High byte | Meaning | Decode |
|---|---|---|---|
| `0b000` | `0x00`–`0x1F` | palette index | `TABLE_STATIC[ref & 0xFFFF]` (§2) |
| `0b001` | `0x20`–`0x3F` | literal RGB | `ref & 0x00FFFFFF` (§3) |
| `0b010` | `0x40`–`0x5F` | named/derived slot | field `+0x06` of the object whose id is `DOCPAL[ref & 0xFFFF]` (`FUN_004c9a60`) |
| `0b011` | `0x60`–`0x7F` | — | returned unchanged |
| `0b100` | `0x80`–`0x9F` | brightness-modified reference | `FUN_004c98cf(ref)` |
| `0b101` | `0xA0`–`0xBF` | automatic | `0x4737B` when `(ref & 0xFFFF) == 0`, else `ref` |
| `0b110` | `0xC0`–`0xDF` | brightness-modified palette entry | `FUN_004c998a(FUN_004c951b(DOCPAL[ref & 0xFFFF]), bit15, high & 0x7F)` |
| `0b111` | `0xE0`–`0xFF` | — | returned unchanged |

Two tables are involved and they are **not** the same:

* `TABLE_STATIC` — `DAT_006144ae`, initialised to `&DAT_00600060` by `FUN_00443d5f` and
  `FUN_00443ede`. Used by tags 0, 2, 4 and 5.
* `DOCPAL` — `DAT_006186ac`, filled from the document object (`FUN_00418fee` calls
  `FUN_004fcbe9(*(u16 *)(doc + 0x6E), 0)`). Used only by tag 6. In the file the palette
  chunk id sits at `DOCUMENT+0x6E` (verified 5/5, chapter 09 §9.3); the correspondence
  between that file slot and the runtime `+0x6E` is `[INFERENCE]`, the two tables being
  distinct is `[OBSERVED]`.

## 2. `TABLE_STATIC` — the indexed palette

The table is 4-byte entries and differs between generations. This resolves the open
question in chapter 09 §9.2: the 56-entry ramp is **not** a 95/97 structure.

| Entry | P95 | P97 | P98 |
|---|---|---|---|
| `0x00`–`0x22` | RGB | RGB | RGB (identical in all three) |
| `0x23`–`0x37` | **not RGB** — recursive references (`0x23` = `0x00000000`, `0x24` = `0xC8000000`, …) | same as P95 | RGB (21 additional colours) |
| `0x38`+ | recursive references | recursive | recursive (`0x38` = `0xC8000000`) |

Measured by locating the same 8-entry signature (`00000000 00FFFFFF 000000FF 0000FF00
00FF0000 0000FFFF 00FFFF00 00FF00FF`) in all three executables: exactly one hit each, at
file offset `0x18DD78` (P95), `0x1C7888` (P97) and `0x1FE260` (P98 = VA `0x00600060`).
P95 and P97 are byte-identical through `0x22` and then diverge from P98. [OBSERVED]

**Decoder contract.** The usable palette-index domain is `0x00`–`0x22` for a Publisher
95/97 document and `0x00`–`0x37` for a Publisher 98 document. Entries at or above the
domain boundary are themselves colour references and MUST be decoded recursively through
this same function — they are not RGB triples. A reader that assumes 56 RGB entries for a
95/97 file will render `0x23`–`0x37` as black or as a brightness reference.

`0x00`–`0x37` (P98 table), as stored — note that the stored word is a Windows `COLORREF`,
so the display order is the byte reverse:

| Index | Stored | R,G,B | Index | Stored | R,G,B |
|---|---|---|---|---|---|
| `0x00` | `00000000` | 0,0,0 | `0x1C` | `006666FF` | 255,102,102 |
| `0x01` | `00FFFFFF` | 255,255,255 | `0x1D` | `000099FF` | 255,153,0 |
| `0x02` | `000000FF` | 255,0,0 | `0x1E` | `00FF6600` | 0,102,255 |
| `0x03` | `0000FF00` | 0,255,0 | `0x1F` | `0000CCFF` | 255,204,0 |
| `0x04` | `00FF0000` | 0,0,255 | `0x20` | `00330099` | 153,0,51 |
| `0x05` | `0000FFFF` | 255,255,0 | `0x21` | `00003366` | 102,51,0 |
| `0x06` | `00FFFF00` | 0,255,255 | `0x22` | `00424242` | 66,66,66 |
| `0x07` | `00FF00FF` | 255,0,255 | `0x23` | `006699FF` | 255,153,102 |
| `0x08` | `00808080` | 128,128,128 | `0x24` | `00003399` | 153,51,0 |
| `0x09` | `00C0C0C0` | 192,192,192 | `0x25` | `000066FF` | 255,102,0 |
| `0x0A` | `00000080` | 128,0,0 | `0x26` | `00003333` | 51,51,0 |
| `0x0B` | `00008000` | 0,128,0 | `0x27` | `0000CC99` | 153,204,0 |
| `0x0C` | `00800000` | 0,0,128 | `0x28` | `0099FFFF` | 255,255,153 |
| `0x0D` | `00008080` | 128,128,0 | `0x29` | `00003300` | 0,51,0 |
| `0x0E` | `00808000` | 0,128,128 | `0x2A` | `00669933` | 51,153,102 |
| `0x0F` | `00800080` | 128,0,128 | `0x2B` | `00CCFFCC` | 204,255,204 |
| `0x10` | `003399FF` | 255,153,51 | `0x2C` | `00663300` | 0,51,102 |
| `0x11` | `00330033` | 51,0,51 | `0x2D` | `00CCCC33` | 51,204,204 |
| `0x12` | `00990000` | 0,0,153 | `0x2E` | `00FFFFCC` | 204,255,255 |
| `0x13` | `00009900` | 0,153,0 | `0x2F` | `00FF6633` | 51,102,255 |
| `0x14` | `00009999` | 153,153,0 | `0x30` | `00FFCC00` | 0,204,255 |
| `0x15` | `000066CC` | 204,102,0 | `0x31` | `00FFCC99` | 153,204,255 |
| `0x16` | `00000099` | 153,0,0 | `0x32` | `00993333` | 51,51,153 |
| `0x17` | `00CC99CC` | 204,153,204 | `0x33` | `00996666` | 102,102,153 |
| `0x18` | `00FF6666` | 102,102,255 | `0x34` | `00663399` | 153,51,102 |
| `0x19` | `0066FF66` | 102,255,102 | `0x35` | `00FF99CC` | 204,153,255 |
| `0x1A` | `0066FFFF` | 255,255,102 | `0x36` | `00333333` | 51,51,51 |
| `0x1B` | `0099CCFF` | 255,204,153 | `0x37` | `00969696` | 150,150,150 |

Reproduce:

```python
d = open('p98/x/MSPUB.EXE', 'rb').read()
import struct
table = struct.unpack_from('<56I', d, 0x1FE260)     # 0x00 … 0x37
```

## 3. Literal RGB (tag `0b001`)

`ref = 0x20000000 | (B << 16) | (G << 8) | R` — a `COLORREF`. Decode with
`R = ref & 0xFF`, `G = (ref >> 8) & 0xFF`, `B = (ref >> 16) & 0xFF`.
The high byte is the tag and carries no colour information. [OBSERVED, VA `0x004C951B`
case 1]

## 4. Brightness (tags `0b100` and `0b110`)

`FUN_004c998a(base, toward_white, percent)` at VA `0x004C998A`:

```
percent = ref_high_byte & 0x7F
if percent == 100: return base                       # exact
if percent == 0:   return 0xFFFFFF if toward_white else 0x000000
k = 50 if not toward_white else 25550 - 255*percent
out_ch = (k + base_ch * percent) / 100               # integer division, per channel
```

`toward_white` is bit 15 of the reference's high word (`(ref >> 23) & 1`). So `percent`
is a 0–100 interpolation toward black (`k = 50`) or toward white
(`k = 25550 − 255·percent`); both degenerate cases are special-cased before the
arithmetic. Tag `0b110` applies this to the base colour of the indexed entry, tag `0b100`
to a reference that has already been resolved (`FUN_004c98cf`).

Example: `0xC8000000` → tag 6, index 0, `toward_white = 0`, `percent = 0` → **black**.
`0xCC640000` → `percent = 0x64 = 100` → the base colour unchanged.

## 5. The 8-slot document scheme

The PALETTE chunk (`0x0047`, chapter 09 §9.3) holds eight colour references at `+0xA0`,
in scheme order. They are references in the sense of §1, not RGB tuples — five of the
eight in the shipped scheme are palette indices. A reader MUST run each through the
decoder before rendering.

| Slot | Stored | Tag | Resolves to |
|---|---|---|---|
| 1 | `0x00000000` | 0 | index 0 = black |
| 2 | `0x00000004` | 0 | index 4 = blue |
| 3 | `0x0000001F` | 0 | index 31 = gold |
| 4 | `0x00000025` | 0 | index 37 = orange |
| 5 | `0x20CCCCCC` | 1 | literal grey (204,204,204) |
| 6 | `0x0000001E` | 0 | index 30 = blue |
| 7 | `0x20CC3366` | 1 | literal purple (102,51,204) |
| 8 | `0x00000001` | 0 | index 1 = white |

## 6. Custom-colour list elements (`0x0037`)

The document-level colour list (chapter 11 §11.10) stores 6-byte elements
`RR GG BB 20 s0 s1`: a bare RGB triple in `R,G,B` order, the literal-RGB tag byte
`0x20`, and a two-byte stamp. The stamp takes `{00 00, 01 00, 02 00, 08 00,
09 00, 18 00}` (little-endian `0, 1, 2, 8, 9, 0x18`) over 63 elements in 54
populated instances; `s1` is `0x00` in 63/63. The RGB is unambiguous; the stamp
is a carried-along writer field with no reader in the shipped binaries (scan
scope: every function of `MSPUB.EXE` 95/97/98 that touches a `0x37` record goes
through the generic container accessor VA `0x004FCBE9` (98) / `0x004010B7`
(97) / `0x00401148` (95), which computes element addresses but never branches
on the stamp bytes). A reader MUST preserve the six bytes verbatim. [OBSERVED
for the domain and the negative]

`0x0038` would carry 10-byte elements but no shipped document populates one
(chapter 11 §11.10.1). [OBSERVED]

## 7. Open

| Item | Status | Experiment |
|---|---|---|
| Tag `0b010` (`FUN_004c9a60`) — field `+0x06` of the referenced object | closed: the tag-2 reference names a slot of the document's colour-scheme array, and the decoder returns the `u32` at object offset `+0x06` of that slot's entry — an index→colour map, not arithmetic. P95 VA `0x00508BFB` / P97 VA `0x005284A3` / P98 VA `0x004C9A60` share the body `FUN_004fcbe9(schemeBase, ref) + 6` (scheme word at `DAT_+0x60`); the two surviving callers pass only object ids the decoder resolved from the tag's low word. Tag-2 references occur in the corpus shape palette at `+0x23`/`+0x18`-family offsets with low words resolving inside the document's own tables (chapter 11), never as dangling ids; the branch is exercised by every tinted shape, not by a missing document. [OBSERVED, binary + corpus] | — |
| Stamp bytes of the `0x0037` element | closed as carried-along writer state: `s0` is a per-element stamp (`0, 1, 2, 8, 9, 0x18`, `0` in 40/63), `s1 == 0` in 63/63; no shipped code reads either byte. See §6 | — |
| `0x4737B` / `0x4737C` (tag 5 "automatic") | closed: the sentinel the decoder returns when `(ref & 0xFFFF) == 0` (P98 VA `0x004C951B` case 5; P97 VA `0x0044F6F7` case 5, which yields `0x4737B` and remaps to `0x5737B` under the same paint-mode bit at P97 VA `0x004284A3`), remapped to `0x4737C` when the global paint-mode bit is set (`DAT_006120D4+0x6F & 0x2000`, P98) so the paint path can select the alternate system brush. P95 has no tag-5 case (VA `0x00418364` falls through to `-1`/unchanged) and no `0x4737B` anywhere; only 3 corpus shapes carry tag 5, all nonzero low words (`0xAD01008A` ×2, `0xAD810002` ×1 in `p97deluxe/x/PageWiz/overhill.pub`, `namecrd.pub`), i.e. the passthrough branch, so no shipped document exercises the sentinel. A reader MUST emit `0x4737B` for tag-5/index-0 and pass any other tag-5 value through. [OBSERVED, binary + corpus] | — |
| Entries above the index domain (`0x23`+ in 95/97, `0x38`+ in 98) | closed: the table past the RGB domain is a second reference array, not RGB. P95/P97 are byte-identical through `0x22` and diverge from P98 at `0x23` (P98 file offset `0x1FE260`, P95 `0x18DD78`, P97 `0x1C7888`); past the boundary the entries are themselves colour references — tag 6 brightness forms (`0xC8000000` = black, tag 6 / index 0 / 0 %), tag 4 derived slots (`0x8C003C00`), tag 2 scheme refs (`0x50…`), and tag 3/1 passthroughs — which the decoder recurses through (P98 VA `0x004C951B` cases 2/4/6 call back into the decoder; validator `colour_ref_ok` accepts tags 0/1/2/4). The writer side confirms the boundary: the only tag-0 indices the pinned colour fields (`0x47` slots, RECT `+0x20`/`+0x24`, shape `+0x23`) ever carry above `0x22` in P98 are `0x25`, `0x30`, `0x35`, `0x37` — the new P98 RGB ramp — while P95's pinned fields never exceed `0x22` (its `0x23`+ entries are recursive references, so a 95/97 reader MUST recurse). This is the chapter 09 derived table, published in full above (§2). [OBSERVED, binary + corpus] | — |
