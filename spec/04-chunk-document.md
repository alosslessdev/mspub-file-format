# 04 — DOCUMENT chunk (`typeMarker 0x0015`)

Exactly one DOCUMENT chunk per file, always directory record 0, always with `parentId = 0x00FE`.

## 4.1 Size

```
size == 0x74 + 2 * (Npages − 1)          (128/128 exact)
```

where `Npages` is the number of PAGE (`0x14`) chunks in the file. Corpus sizes therefore
124 (5 pages) ×87, 126 (6) ×27, 128 (7) ×1, 130 (8) ×12, 138 (12) ×1. The chunk has no other
variable part and no padding. [OBSERVED]

## 4.2 Layout

Chunk-relative offsets. All values are little-endian. `count` = "distinct values over 128
files".

| Offset | Width | Field | Values / meaning |
|---|---|---|---|
| 0x00 | u16 | `typeMarker` | `0x0015`, 128/128 |
| 0x02 | u16 | `descriptor` | `0x6A78` (bytes `78 6A`) in 128/128 — the per-type descriptor pair (chapter 02 §2.5), [UNKNOWN] semantics |
| 0x04 | u16 | `listChunkId` | id of the `0x29` chunk, 128/128 |
| 0x06 | u16 | `defaultsChunkId` | id of the `0x28` chunk, 128/128 |
| 0x08 | u16 | `firstPageId` | id of the first PAGE chunk, 128/128; it is always the lowest-offset PAGE [OBSERVED] |
| 0x0A | u16 | `flags0A` | 9 distinct: `0x0210` ×98, `0x0000` ×7, `0x0610` ×6, `0x0616` ×6, `0x1210` ×5, `0x0010` ×3, `0x0212`, `0x0216`, `0x021E` — [UNKNOWN], behaves like a flags word (see §4.6) |
| 0x0C | u16 | reserved | `0` ×128 |
| 0x0E | u16 | `documentChunkId` | the DOCUMENT chunk's own id (equals `Contents` header `+0x0E`), 128/128 |
| 0x10 | u16 | `viewPageId` | always the 4th entry (index 3) of the document page order, 128/128 — §4.5 |
| 0x12 | u16 | `const574` | `574` (0x023E) ×128 — same constant as `Contents` header `+0x12` |
| 0x14 | u32 | `pageWidth` | publication page width in **EMU** (914400 per inch) |
| 0x18 | u32 | `pageHeight` | publication page height in EMU |
| 0x1C | i32 | `originX` | signed X of the publication page inside the physical sheet; 0 in 118/128 files |
| 0x20 | i32 | `originY` | signed Y; 0 in 118/128 files |
| 0x24 | u16 | `flags24` | `1` ×115, `0` ×10, `5` ×3 |
| 0x26 | u32 | `paperWidth` | physical sheet width in EMU; `0` when the publication exceeds any sheet (7 files) |
| 0x2A | u32 | `paperHeight` | physical sheet height in EMU; `0` in the same 7 files |
| 0x2E | u16 | `printPaperCode` | 6 distinct: `1` ×99, `0` ×10, `7` ×9, `4` ×6, `14` ×3, `2` ×1 — [UNKNOWN] |
| 0x30 | u16 | `printOrientCode` | 4 distinct: `5` ×82, `6` ×36, `4` ×4, `0` ×6 — [UNKNOWN] |
| 0x32 | u16 | varying | `0` ×127, `1` ×1 |
| 0x34 | u16 | reserved | `0` ×128 |
| 0x36 | u16 | varying | 7 distinct (`30` ×90, `40` ×6, `34` ×5, `26` ×2, `0` ×23, `33`, `35`) — [UNKNOWN] |
| 0x38 | u16 | varying | `34` ×105, `0` ×10, `0xFFFF` ×13 |
| 0x3A | u16 | varying | `0` ×115, `0xFFFF` ×13 |
| 0x3C | u16 | `defaultTabOrSpacing` | `720` ×125, `360`, `432`, `1296` — [UNKNOWN]; 720 = 0.5 in in twips |
| 0x3E | u16 | varying | `30` ×127, `10` ×1 |
| 0x40 | u16 | reserved | `0` ×128 |
| 0x42 | u16 | reserved | `0` ×128 |
| 0x44 | u16 | varying | `0` ×114, else small ids/codes (308, 281, 304 …) |
| 0x46 | u16 ×14 | `globalChunkIds[14]` | ids of the document's singleton chunks, one slot per type — §4.3 |
| 0x62 | u16 | reserved (zero) | `0` ×128; terminates the 14-slot table |
| 0x64 | u16 | `count64` | 0…27, 20 distinct — [UNKNOWN] |
| 0x66 | u16 | reserved (zero) | `0` ×128 |
| 0x68 | u16 | `styleChunkId` | id of the `0x39` chunk, 128/128 |
| 0x6A | u16 | `lastPageIndex` | `Npages − 1`, 128/128 |
| 0x6C | u16 | `lastPageIndex2` | equals `+0x6A`, 128/128 |
| 0x6E | u16 | const | `2` ×128 |
| 0x70 | u16 | reserved | `0` ×128 |
| 0x72 | u16 | reserved | `0` ×128 |
| 0x74 | u16[Npages−1] | `pageIds` | ids of pages 2…N in document order |

## 4.3 `globalChunkIds` — the 14 pointer slots at `+0x46`

Each slot always points at the same chunk *type*; several slots are optional and hold `0` when
the document has no such chunk. Verified over 128/128 files:

| Slot | Referenced type | Slot present in |
|---|---|---|
| `+0x46` | `0x23` | 128/128 |
| `+0x48` | `0x31` (logo/style gallery) | 128/128 |
| `+0x4A` | `0x1E` (font table) | 128/128 |
| `+0x4C` | `0x1F` | 128/128 |
| `+0x4E` | `0x16` | 128/128 |
| `+0x50` | `0x2A` | 128/128 |
| `+0x52` | `0x2B` | 30/128 (0 otherwise) |
| `+0x54` | `0x26` | 128/128 |
| `+0x56` | `0x31` (2nd gallery) | 128/128 |
| `+0x58` | `0x31` (3rd gallery) | 128/128 |
| `+0x5A` | `0x34` | 68/128 |
| `+0x5C` | `0x35` | 74/128 |
| `+0x5E` | `0x37` | 16/128 |
| `+0x60` | `0x38` | 15/128 |

The remaining singleton types (`0x1A`, `0x1C`, `0x22`, `0x27`, `0x2D`, `0x2E`, `0x39`) are
reached through other pointers (`+0x68` for `0x39`) or are not referenced from the DOCUMENT
record at all. [OBSERVED]

## 4.4 Page list

`+0x08` holds page 1; `+0x74` holds pages 2…N in ascending chunk-offset order. The union is
exactly the set of PAGE chunk ids in 128/128 files, with no duplicate and no missing page, and
the order equals the chunk-offset order. [OBSERVED]

Note the consequence for a validator: the number of pages can be recovered *twice*, from the
PAGE chunk count and from `(size − 0x74)/2 + 1`; both must agree.

## 4.5 `viewPageId` (`+0x10`)

On 128/128 files this is the *fourth* entry of the document page order (index 3). Because every
corpus document has at least five pages, the slot always exists. Its role (current view page?
a reserved page slot?) is [UNKNOWN]; the experiment is to change the current page in Publisher,
save, and re-read. [OBSERVED for the value identity]

## 4.6 Geometry fields and units

`+0x14` / `+0x18` are EMU. Confirmed arithmetically: 7772400 × 10058400 = 8.5 × 11 in (53
files), 10058400 × 7772400 = 11 × 8.5 in (22), 3886200 × 5029200 = 4.25 × 5.5 in (6),
5029200 × 7315200 = 5.5 × 8 in (5), 15544800² = 17 × 17 in (4), 18288000² = 20 × 20 in (3);
every observed pair is a clean physical size at 914400 EMU per inch. [OBSERVED]

`+0x26` / `+0x2A` hold the *physical sheet* size and differ from the publication size exactly
when the publication is printed many-up or tiled:

| File | publication | sheet | `+0x1C` / `+0x20` |
|---|---|---|---|
| `PAGEWIZ/CATALOG.PUB` | 5.5 × 8.5 in | 8.5 × 11 in | −0.469 / −1.162 in |
| `PAGEWIZ/BRCATALG.PUB` | 8.5 × 11 in | 8.5 × 11 in | −6.375 / −1.344 in |
| `PAGEWIZ/TRVLBROC.PUB` | 4.25 × 11 in | 8.5 × 11 in | +4.264 / +10.560 in |
| `PAGEWIZ/BANKBROC.PUB` | 14 × 8.5 in | 8.5 × 14 in | +0.021 / 0 |
| `PAGEWIZ/AUDIOLBL.PUB` | 3.5 × 1.66 in | 8.5 × 11 in | 3.5 in / 0 |

118 of 128 files have `+0x1C = +0x20 = 0` and `paperWidth/Height` equal (or 0) — i.e. the
common case is a one-page-per-sheet document. The ten exceptions are the multi-up / tiled
layouts. `originX/originY` are therefore the publication page's position within the sheet.
[OBSERVED for the values; INFERENCE for the "position within sheet" reading — it explains the
sign changes and the multi-up files, but no single formula reproduces all ten]

Seven files have `paperWidth = paperHeight = 0`: these are publications larger than any
physical sheet (banners/posters), where the sheet size is not defined. [OBSERVED]

## 4.7 `+0x0A`

Nine values, all with a `0x_10`/`0x_12`/`0x_16`/`0x_1E` low byte and a `0x00`/`0x02`/`0x06`/`0x12`
high byte. It correlates with neither page count nor page size (e.g. `0x0610` appears on 8-page
documents only, but `0x0210` also appears on 8-page documents). Recorded as a flags word;
[UNKNOWN]. [OBSERVED]

## 4.8 Validation predicates

```
u16@+0x00 == 0x0015
u16@+0x02 == 0x6A78
typeof(by_id(u16@+0x04)) == 0x29 ; typeof(by_id(u16@+0x06)) == 0x28
typeof(by_id(u16@+0x08)) == 0x14 ; typeof(by_id(u16@+0x68)) == 0x39
u16@+0x0E == document chunk id == Contents header u16@+0x0E
u16@+0x12 == 574 ; u16@+0x1A-header == 34 (see chapter 02)
size == 0x74 + 2*(Npages-1)
u16@+0x6A == u16@+0x6C == Npages-1 ; u16@+0x6E == 2 ; u16@+0x62 == u16@+0x66 == 0
u16@+0x70 == u16@+0x72 == 0
pageWidth != 0 and pageHeight != 0
every id in the 14 slots resolves or is 0, and its chunk type matches the table in §4.3
pageIds[] resolves to distinct PAGE ids and page order == ascending chunk offset
```
