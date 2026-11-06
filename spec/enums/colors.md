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
`RR GG BB 20 flag`. This is **not** the 32-bit reference form: it is a bare RGB triple in
`R,G,B` order plus a literal-RGB tag byte and a flag. The flag takes
{0, 1, 2, 8, 9, 0x18} over the corpus; its meaning is `[UNKNOWN]`. `0x0038` would carry
10-byte elements but no shipped document populates one. [OBSERVED]

## 7. Open

| Item | Status | Experiment |
|---|---|---|
| Tag `0b010` (`FUN_004c9a60`) — field `+0x06` of the referenced object | `[UNKNOWN]` beyond the call shape | needs a document that uses a named scheme slot |
| Flag byte of the `0x0037` element | `[UNKNOWN]` | author a custom colour and diff |
| `0x4737B` / `0x4737C` (tag 5 "automatic") | `[UNKNOWN]` — a sentinel the renderer maps to the system window colour | trace the paint path |
| Entries above the index domain (`0x23`+ in 95/97, `0x38`+ in 98) | recursive references, semantics of the tint entries `[UNKNOWN]` | needs a document that references them |
