# 11 — Document-level records: fonts, logo/design, border art, print setup

Most of a document's non-geometric data lives in **singleton records**: one chunk per
document (or a small fixed number), referenced by id from the DOCUMENT chunk. This
chapter documents their framing, size rules and the payloads that are understood.

All rules below were re-measured over the Publisher 95 corpus (130 documents) and, where
stated, over the whole 493-document corpus. Counts are stated per rule.

## 11.1 DOCUMENT slot map

The DOCUMENT chunk (`0x0015`) holds the ids of its singletons at fixed offsets. `0` means
the record is absent. Every non-zero value resolves to a chunk of the stated type
(130/130 per slot). [OBSERVED]

| Offset | Marker | Record | Present |
|---|---|---|---|
| `+0x04` | `0x0029` | print setup (DEVMODE/DEVNAMES) | 130/130 |
| `+0x06` | `0x0028` | paper/print parameter block | 130/130 |
| `+0x08` | `0x0014` | first page | 130/130 |
| `+0x46` | `0x0023` | fixed 4-slot table | 130/130 |
| `+0x48` | `0x0031` | design/object set #1 | 130/130 |
| `+0x4A` | `0x001E` | **font table** | 130/130 |
| `+0x4C` | `0x001F` | **line/border-art style table** | 130/130 |
| `+0x4E` | `0x0016` | story container | 130/130 |
| `+0x50` | `0x002A` | font-substitution table | 130/130 |
| `+0x52` | `0x002B` | document name list | 30/130 |
| `+0x54` | `0x0026` | paragraph-style names | 130/130 |
| `+0x56` | `0x0031` | design/object set #2 | 130/130 |
| `+0x58` | `0x0031` | design/object set #3 | 130/130 |
| `+0x5A` | `0x0034` | 14-byte sub-table | 70/130 |
| `+0x5C` | `0x0035` | DLL binding record | 74/130 |
| `+0x5E` | `0x0037` | colour list, 6-byte elements | 16/130 |
| `+0x60` | `0x0038` | colour list, 10-byte elements | 15/130 |
| `+0x68` | `0x0039` | 48-byte document record | 130/130 |

The three `0x0031` slots always name distinct chunks.

## 11.2 Story container `0x0016`

```
+0x00 u16 0x0016
+0x02 u8  0x1A              A
+0x03 u8  0x10              B
+0x04 u16 styleId           a style id, NOT a chunk id
+0x06 u16 0
+0x08 u16 id of the 0x001A chunk
+0x0A u16 id of the 0x001C chunk
+0x0C u16 id of the 0x002E chunk
+0x0E u16 id of the 0x002D chunk
```

Fixed 16 bytes (130/130). Slot order is `1A, 1C, 2E, 2D` — not ascending marker order.
`+0x04` resolves to a live chunk in only 8 documents, so it must not be resolved as an
id. [OBSERVED for the layout; INFERENCE for the style-id reading]

## 11.3 Container header

`0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x002A`, `0x002B`, `0x0032`, `0x0034`, `0x0037`,
`0x0038` (and `0x001A`/`0x001C` with a per-type element size) share one header:

```
+0x00 u16 marker
+0x02 u8  A           structural landmark (see 11.9)
+0x03 u8  B           constant per type
+0x04 u16 nEntries
+0x06 u16 nEntries    duplicate
+0x08 u16 endOffset   == size - 0x0E      (offset-table flavour)
        u16 elementSize                   (fixed-element flavour)
+0x0A u16 format      0 / 1 / 5
+0x0C u16 0xFFFF      sentinel
+0x0E ...             offsets relative to chunk+0x0E (0xFFFF = empty), then payload
```

Two flavours:

* **Offset table** — element `k` runs from `chunk+0x0E+off[k]` to the next offset (or to
  `size`). Used by `0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x002A`, `0x002B`, `0x0032`.
* **Fixed element** — payload is `n × elementSize` bytes at `+0x0E`, so
  `size == 0x0E + elementSize·n`. Used by `0x0037` (6), `0x0038` (10), `0x001A` (14),
  `0x001C`/`0x002D`/`0x002E` (8).

**Publisher 97 widens the offset entries from `u16` to `u32`** and doubles the `A` byte
accordingly (e.g. `0x001F`: `A` 0x04 → 0x08). A reader must key the container parse on the
chunk's own `A` byte, not on the marker alone. [OBSERVED]

## 11.4 Size rules

`n` is `u16@+0x04` unless stated. Every rule is exact over the stated population.

| Marker | Rule | Result |
|---|---|---|
| `0x0016` | `size == 16` | 130/130 |
| `0x001A` | `size == 26 + 14·n` | 130/130 |
| `0x001C` | `size == 26 + 8·n` | 130/130 |
| `0x002D` | `size == 26 + 8·n` | 130/130 |
| `0x002E` | `size == 26` | 130/130 |
| `0x001E` | `u16@+0x08 == size − 0x0E` (n at `+0x04` duplicated at `+0x06`) | 130/130 |
| `0x001F` | same | 130/130 |
| `0x0023` | same | 130/130 |
| `0x0026` | same | 130/130 |
| `0x002A` | same | 130/130 |
| `0x002B` | same | 30/30 |
| `0x0032` | same | 390/390 |
| `0x0028` | `size == 26 + 5·u16@+0x10` | 130/130 |
| `0x0029` | `u16@+0x30 == size − 54` | 130/130 |
| `0x0031` | `size == 30 + 8·u16@+0x08` | 390/390 |
| `0x0034` | `size == 46 + 14·u16@+0x24` | 70/70 |
| `0x0035` | `size == 200` | 74/74 |
| `0x0036` | `size == 112` | 1/1 |
| `0x0037` | `size == 14 + 6·n` | 16/16 |
| `0x0038` | `size == 14 + 10·n` | 15/15 |
| `0x0039` | `size == 48` (95/97), 56 (98) | 488/488, 5/5 |
| `0x0027` | `size == 42` | 14/14 |

## 11.5 Font table `0x001E`

One per document. Entries are `u8 charset`, `u8 pitchFamily`, then the font name
NUL-terminated with **no length byte**; contiguity `off[k+1] == off[k] + 2 + strlen + 1`
holds for 1 575/1 575 entries. 1 575 entries, 144 distinct names in the Publisher 95
corpus. [OBSERVED]

* `charset` ∈ {0x00, 0x01, 0x02, 0xFF} = ANSI / DEFAULT / SYMBOL / family-only.
* `pitchFamily` is a `LOGFONT.lfPitchAndFamily` byte: low 2 bits = pitch, bits 4–6 = family.
  Bits 2–3 and bit 7 vary between documents for the same face and are **not** fields.

## 11.6 Line / border-art style table `0x001F`

One per document. 81 of 130 Publisher 95 documents carry the empty 16-byte form; the rest
carry **named border-art styles** — the document-side representation of "border art" (the
markers `0x0046` BORDER_ART / `0x005C` PALETTE from the 2000+ block model do not exist
here). Names observed include `Basic...Black Dashes`, `Sawtooth`. An entry is
`[u16 optional prefix] + name + binary drawing blob`; the prefix width is not constant
(2 or 4 bytes) and the discriminator is `[UNKNOWN]`. [OBSERVED for the structure]

The shipped border-art library lives *outside* the document, in `PUBBRD/*.BDR` catalogue
files on the CD — a separate format, not part of the `.pub` specification.

## 11.7 Design / object sets `0x0031` and `0x0032`

`0x0031` appears **three times per document**, always children of the DOCUMENT, and each is
the parent of one `0x0032`. `0x0031` size rule: `30 + 8·n` (390/390); `0x0032` uses the
offset-table container with `A = 8`. They are the Design Gallery / logo object sets: the
three slots correspond to the three designs every Publisher 95 template is built on.
[OBSERVED for structure; INFERENCE for the "design set" naming]

## 11.8 Print setup records `0x0028`, `0x0029`, `0x0036`

* `0x0028` — paper/print parameter block. Six fixed application codes
  (`0x14B7, 0x18B7, 0x14A8, 0x14DE, 0x14E0, 0x142A`, i.e. 5303/6327/5288/5342/5344/5162)
  in every document, then `n = (size−26)/5` five-byte records `{u16 code, u16 value, u8 0}`.
  The codes exceed the chunk-id space, so they are application constants, not references.
* `0x0029` — print setup. Four EMU margins at `+0x16`, page width/height at `+0x48`/`+0x4C`
  (equal to the DOCUMENT's, 130/130), DEVMODE `dmPaperSize` at `+0x50`, then device, driver
  and port as NUL-terminated strings whose cumulative ends are the four `u16` at
  `+0x3E…+0x44`. Contains **no timestamps**.
* `0x0036` — a fixed 112-byte print-setup companion, one instance in the entire corpus
  (`CHEKLIST.JSP`), byte-identical across all four CD revisions. Fields `[UNKNOWN]`.

## 11.9 The `A` byte

`A` is a structural landmark, not a length. It equals the byte offset of the record's
primary count field in 15 of 21 container types (`0x001A`/`0x001C`/`0x001F`/`0x0023`/
`0x0026`/`0x002A`/`0x002B`/`0x002D`/`0x002E`/`0x0032`/`0x0037`/`0x0038` → 4; `0x0031` → 8;
`0x0028` → 0x10; `0x0034` → 0x24). Exceptions: `0x001E` (A = 8, count at `+0x04`), `0x002C`
(A = 0x18, counts at `+0x14`), `0x0029` (A = 0x2C, no count), `0x0027` (A = 0x16, a string
offset), `0x0035` (A = 0xC8, the chunk size), `0x0039` (A = 0x4C). [OBSERVED]

## 11.10 Colour lists `0x0037` / `0x0038`

`0x0037` (16 documents) uses 6-byte elements: `RR GG BB 20 flag`. The triple is unambiguous;
the `0x20` tag byte is the literal-RGB tag of chapter 09, and the trailing flag takes
{0,1,2,8,9,0x18}. `[INFERENCE]`: a document-level custom-colour list. `0x0038` (15
documents) declares 10-byte elements, but the corpus contains **no populated instance**, so
its element layout is `[UNKNOWN]`.

## 11.11 Open

| Item | Status | Experiment |
|---|---|---|
| `0x0028` six application codes | `[UNKNOWN]` | look the constants up as a table in `MSPUB.EXE` |
| `0x001F` entry prefix width (2 vs 4) | `[UNKNOWN]` | save a document with one named border style and diff |
| `0x001A` 14-byte element field order | `[UNKNOWN]` | save a document that adds one paragraph |
| `0x0016 +0x04` style id | `[INFERENCE]` | resolve against `0x0026`/`0x001F` entry order |
| `0x0036` fields | `[UNKNOWN]` | single instance; needs a document exercising print setup |
| `0x0038` element layout | `[UNKNOWN]` | author a document that uses the 10-byte colour form |
| `0x0031`/`0x0032` payloads | partially mapped | size rules exact; field semantics open |
