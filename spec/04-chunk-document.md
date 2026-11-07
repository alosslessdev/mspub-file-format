# 04 — DOCUMENT chunk (`typeMarker 0x0015`)

Exactly one DOCUMENT chunk per file, always directory record 0, always with a sentinel
`parentId`: `0x00FE` in the 128 `.PUB` documents, `0x00FF` in the two `.JSP` publications
(chapter 03 §3.4).

## 4.1 Size

```
size == 0x74 + 2 * (Npages − 1)          (128/128 exact)
```

where `Npages` is the number of PAGE (`0x14`) chunks in the file. Corpus sizes therefore
124 (5 pages) ×87, 126 (6) ×27, 128 (7) ×1, 130 (8) ×12, 138 (12) ×1. The chunk has no other
variable part and no padding. [OBSERVED]

**Version scope.** This rule is exact for the 128 Publisher 95 documents. Publisher 97 appends
30 bytes and Publisher 98 appends 72 bytes after the same variable tail, so the general form is
`size == 0x74 + 2*(Npages-1) + R` with `R = 0 | 30 | 72` for 95 | 97 | 98 (measured over all 484
corpora documents: p95 0×128, p97 30×105 + 0×1, p97deluxe 30×248, p98 72×2). For Publisher 98 the
page count must include page slots of type `0x41` as well as `0x14`. The appended region is
partially mapped in chapter 18 and is the remaining open item for 97/98. [OBSERVED]

## 4.2 Layout

Chunk-relative offsets. All values are little-endian. `count` = "distinct values over 128
files".

| Offset | Width | Field | Values / meaning |
|---|---|---|---|
| 0x00 | u16 | `typeMarker` | `0x0015`, 128/128 |
| 0x02 | u16 | `descriptor` | `0x6A78` (bytes `78 6A`) in 128/128 — the per-marker stamp: byte `A = 0x78` and byte `B = 0x6A` are entry `0x15` of the 54-byte per-marker record template at VA `0x00593308`, copied verbatim by the record constructor (§4.11); never compared, only used as a layout split point |
| 0x04 | u16 | `listChunkId` | id of the `0x29` chunk, 128/128 |
| 0x06 | u16 | `defaultsChunkId` | id of the `0x28` chunk, 128/128 |
| 0x08 | u16 | `firstPageId` | id of the first PAGE chunk, 128/128; it is always the lowest-offset PAGE [OBSERVED] |
| 0x0A | u16 | `flags0A` | 9 distinct: `0x0210` ×98, `0x0000` ×7, `0x0610` ×6, `0x0616` ×6, `0x1210` ×5, `0x0010` ×3, `0x0212`, `0x0216`, `0x021E` — a flags word, bits mapped in §4.7 |
| 0x0C | u16 | reserved | `0` ×128 |
| 0x0E | u16 | `idBase` | `1` ×128 (`1` in all 493 files) — a fixed id-space bias, **not** the chunk's own id (that lives only in `Contents` header `+0x0E`), §4.9 |
| 0x10 | u16 | `viewScaleCode` | `0` ×127, `3` ×1 (`1` occurs in one of the two `.JSP` files) — a view-scale selector, **not** the saved page (that is `Contents` header `+0x10`), §4.5 |
| 0x12 | u16 | `coordinateSystem` | 5 distinct here: `0` ×115, `3` ×6, `1` ×4, `6` ×2, `5` ×1; 8 distinct over all 493 files (`8` ×35, `4` ×7, `7` ×1 added) — the publication layout, enumerated in §4.10. Not the `574` of `Contents` header `+0x12` |
| 0x14 | u32 | `pageWidth` | publication page width in **EMU** (914400 per inch) |
| 0x18 | u32 | `pageHeight` | publication page height in EMU |
| 0x1C | i32 | `originX` | signed X of the publication page inside the physical sheet; 0 in 118/128 files |
| 0x20 | i32 | `originY` | signed Y; 0 in 118/128 files |
| 0x24 | u16 | `flags24` | `1` ×115, `0` ×10, `5` ×3 |
| 0x26 | u32 | `paperWidth` | physical sheet width in EMU; `0` when the publication exceeds any sheet (7 files) |
| 0x2A | u32 | `paperHeight` | physical sheet height in EMU; `0` in the same 7 files |
| 0x2E | u16 | `printPaperCode` | 6 distinct: `1` ×99, `0` ×10, `7` ×9, `4` ×6, `14` ×3, `2` ×1 — never read by the application, §4.9.2 |
| 0x30 | u16 | `printOrientCode` | 4 distinct: `5` ×82, `6` ×36, `0` ×6, `4` ×4 (`13` and `14` also occur in the 97/98 corpora) — never read, §4.9.2 |
| 0x32 | u16 | varying | `0` ×127, `1` ×1 |
| 0x34 | u16 | reserved | `0` ×128 |
| 0x36 | u16 | varying | 7 distinct (`30` ×90, `0` ×23, `40` ×6, `34` ×5, `26` ×2, `33`, `35`) — never read, §4.9.2 |
| 0x38 | u16 | varying | `34` ×105, `0` ×10, `0xFFFF` ×13 |
| 0x3A | u16 | varying | `0` ×115, `0xFFFF` ×13 |
| 0x3C | u16 | `defaultTabTwips` | default tab interval in **twips**: `720` (0.5 in) ×125, `432`, `1296`, `360` (720 in 484 of the 493 files) — read by the line layout, §4.9.1 |
| 0x3E | u16 | varying | `30` ×127, `10` ×1 |
| 0x40 | u16 | reserved | `0` ×128 |
| 0x42 | u16 | reserved | `0` ×128 |
| 0x44 | u16 | varying | `0` ×114, else small ids/codes (308, 281, 304 …) |
| 0x46 | u16 ×14 | `globalChunkIds[14]` | ids of the document's singleton chunks, one slot per type — §4.3 |
| 0x62 | u16 | reserved (zero) | `0` ×128; terminates the 14-slot table |
| 0x64 | u16 | `publicationType` | 20 distinct, 0…27 (0…34 over all 493 files). A selector consumed by three switches, §4.9.3 |
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

## 4.5 `+0x10` — the measurement-unit code, not the saved page

`0` in 127 of the 128 Publisher 95 templates (`3` in `PAGEWIZ/MODERN.PUB`), `0` in 105/108
Publisher 97, 194/250 Publisher 97 Deluxe and 4/5 Publisher 98 documents. The nonzero
values over all 493 files are `1` in six files (the `WCOMPCLS`/`WCOMPJAZ`/`WCOMPMOD`
greeting-card companions in `p97/x` and `p97deluxe/x/PageWiz`) and `3` in two
(`PAGEWIZ/MODERN.PUB`, `p98/x/CLRCHK.JSP`); no corpus document uses a value above `3`.
It is **not** the saved page: that value is `Contents` header `+0x10` (chapter 02 §2.4), which
is the fourth entry of the page order in 487/493 files and is what the open path consumes.
The word is the ruler/display measurement unit. The converter is VA `0x00411587`, whose
divisor table VA `0x00411667` maps the code to EMU per unit — `0`/`0xD` → `0xDF3E0`
(914400, one inch), `1` → `360000` (914400/2.54, one centimetre), `2` → `0x25350`
(152400 = 914400/6, one pica), `3`/`4`/`5`/`0xE` → `0x319C` (12700 = 914400/72, one
point), `8` → `0x27B` (635 = 914400/1440, one twip) — so `0` = inches, `1` = centimetres,
`3` = points. Every quotient is exact, the same arithmetic that fixes the EMU size rule
in §4.6. The ruler builder VA `0x00439F58` switches on the same word (`0` inches, `1`
centimetres, `2`/`3` picas-or-points, with `10`/`0xB` as its zoom-shifted variants of
`0`/`1`), and the page-setup path VA `0x004DC160` passes the word as the unit argument
when it formats page-size extrema. The two view sites behave accordingly: VA `0x0043F1AB`
turns the word into a scale divisor — `16` for `0`, `8` for `1`, `10` otherwise — and
multiplies it into a view ratio, and VA `0x00428CFB` formats the same word for display
(ruler-label multiplier `6` for code `2`, `1` otherwise). [OBSERVED: the divisor table, the
ruler switch and both view VAs are in MSPUB.EXE 95; the inch/cm/point names are the only
readings consistent with the exact EMU quotients]

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

## 4.7 `flags0A` — the document flags word at `+0x0A`

The application reads this word as `*(u16 *)(document + 0x0A)` (and its high byte as
`+0x0B`). Six bits have an identified meaning; the rest are never tested.

| Bit | Mask | Meaning | Evidence (MSPUB.EXE 95) |
|---|---|---|---|
| 2 | `0x0004` | **Ignore Background** state for the spread | View menu item `0x54` is labelled from the string table at VA `0x0046DE64` indexed by `FUN_00405724` (VA `0x00405724`), which returns `(flags & 4) == 0`; toggled by VA `0x004D6C02`; suppresses the partner page's background in VA `0x0043C259` |
| 4 | `0x0010` | **Show Boundaries and Guides** | View menu item `0x57` label taken from the table at VA `0x0046DE95` with index `(flags & 0x10) >> 4` — entries are `"Show &Boundaries and Guides"` / `"Hide &Boundaries and Guides"` (VA `0x0043851F`) |
| 10 | `0x0400` | **Two-Page Spread** | View menu item `0x51` label from the table at VA `0x0046DE3E` with index `(flags & 0x400) == 0` — entries `"Single Pag&e"` / `"Two-Pag&e Spread"` (VA `0x0043851F`); VA `0x0045BEF0` iterates page *pairs* only when the bit is set; VA `0x00435BE4` maps the current page to its spread partner |
| 11 | `0x0800` | **no kerning cap** — the text run's kerning-pair limit becomes 32000 instead of `u16@+0x3E` | VAs `0x0040BFA6` and `0x00435FD7`: `uVar = 32000; if ((flags_hi & 8) == 0) uVar = *(u16 *)(document + 0x3E);` |
| 8 | `0x0100` | transient "document is being re-flowed" latch | set at VA `0x0045F38A` (`|= 1` on byte `+0x0B`), cleared with `& 0xFEFF` at VAs `0x0045F38A`, `0x0053496D`; never present in the corpus |
| 12 | `0x1000` | render-path gate (Publisher 97+; residue in 95) | read by VA `0x004E788E` (97) / `0x00453909` (98), which selects between two page-render paths on the bit; written from the page-setup dialog by VA `0x004B8B44` and copied document→page record by VA `0x0042D7B8`; Publisher 95 has no reader or writer — its five `0x1210` files carry the bit as forward residue |

Bits 0, 1, 3 and 9 have no reader in any shipped build: the exhaustive line-level scan
of every `document + 0x0A` word access finds only the masks `2`, `4`, `8`, `0x10` and
`0x400` tested (95: 3 293 functions; 97: 4 252; 98: 5 360), and the decimal/hex offset
enumeration of all three document pointers shows no access to any other bit. Bit 1 is
set by VA `0x004D6C02` but never tested back; bit 3 is copied into the save record by
VA `0x0053496D` (`(word & 0xFFFF0008) >> 3`, i.e. the bit is preserved across the save
dialog, never branched on). All four bits are therefore proven write-only/pass-through
over the full scan scope, and every observed value stays a subset of `0x161E`. Bit 12
(`0x1000`) is different: Publisher 95 neither reads nor writes it, but Publisher 97
reads it in VA `0x004E788E` (Publisher 98 VA `0x00453909`, same shape) — the
open/render gate that selects between two page-render paths according to the bit, also
propagated document→page record by VA `0x0042D7B8` and set from the page-setup dialog by
VA `0x004B8B44`. Five Publisher 95 files carry it (`0x1210` in `PAGEWIZ/BRCATALG.PUB`,
`CLINEAR.PUB`, `ELINEAR.PUB`, `POSTER.PUB`, `VLINEAR.PUB`) as forward residue the 95
build never interprets; the 97/98 builds do. [OBSERVED for the masks, the dialog
writer and both gate VAs; the write-only finding for bits 0/1/3/9 is a closed negative
over all three executables]

Bit 10 is the bit that turns a document into a two-page-spread publication, and it is the
same bit that `VA 0x0045BEF0` keeps in step with `coordinateSystem == 2` (§4.10).

## 4.8 Validation predicates

```
u16@+0x00 == 0x0015
u16@+0x02 == 0x6A78           (P95; P97 0x889E, P98 0xB2D2 — a build constant, §4.11)
typeof(by_id(u16@+0x04)) == 0x29 ; typeof(by_id(u16@+0x06)) == 0x28
typeof(by_id(u16@+0x08)) == 0x14 ; typeof(by_id(u16@+0x68)) == 0x39
u16@+0x0E == 1 ; u16@Contents+0x0E == document chunk id (see chapter 02)
u16@+0x0C == 0 ; u16@+0x12 in {0,1,3,4,5,6,7,8} ; u16@+0x0A & ~0x161E == 0
u16@+0x3C in {360,432,720,1296} ; u16@+0x1A-Contents == 34 (see chapter 02)
size == 0x74 + 2*(Npages-1)
u16@+0x6A == u16@+0x6C == Npages-1 ; u16@+0x6E == 2 ; u16@+0x62 == u16@+0x66 == 0
u16@+0x70 == u16@+0x72 == 0
pageWidth != 0 and pageHeight != 0
every id in the 14 slots resolves or is 0, and its chunk type matches the table in §4.3
pageIds[] resolves to distinct PAGE ids and page order == ascending chunk offset
```

## 4.9 Fields with no reader — the print/settings residue

The DOCUMENT chunk is loaded into one contiguous block and `DAT_00587AA8` (Publisher 95),
`DAT_005D27C8` (97) and `DAT_00613920` (98) are the locked pointers to it, so
`*(u16 *)(document + N)` in the decompilation *is* `u16@N` of the on-disk record. A full scan
of all three executables — every access to the document pointer, to a local derived from it,
and to the inline form `*(int *)((u32)DAT_005878A0 * 0x10 + 8 + DAT_00585A74) + N` — yields
the complete read/write map below.

| Offset | Read | Written | Meaning |
|---|---|---|---|
| `+0x2E` | **never** | **never** | print paper-size code (`dmPaperSize`), a stale copy of `0x0029+0x50` frozen at file-creation time |
| `+0x30` | **never** | **never** | second print-setup word, same provenance; proven not to be `dmPaperLength` (§4.9.2) |
| `+0x36` | **never** | **never** | unknown small code, same |
| `+0x3C` | `0x00409F85` | `0x00557A69` | default tab interval (§4.9.1) |
| `+0x64` | `0x004BF85F`, `0x004C6C37`, `0x00561D04` | — | publication type selector (§4.9.3) |

Scan scope for the negatives — every Publisher module on the CD, 15 072 decompiled
functions: `MSPUB.EXE` 95 (3 825), 97 (4 252) and 98 (5 360); `PUBDLG.DLL` (57),
`MSPUBW32.DLL` (608), `PUB3STP.DLL` (227), `MSPUBQ32.DLL` (54), `COMPLINC.DLL` (185),
`PUBOLE32.DLL` (207) and `PUB4STP.DLL` (297). The scan covers every access to each build's
document pointer, to a local derived from it, and to the inline chunk-table form, plus
one-hop callees that receive the pointer as an argument. Only the three `MSPUB.EXE` builds
parse the DOCUMENT chunk at all; the DLLs contain no reference to it (`+0x4E` and `+0x2E`
never occur as document offsets, and none of them mentions the `0xACE8` stream magic).
The three never-read words are therefore pure
residue: they arrive with the file and leave with it, and no UI or layout path branches on
them. Their correlation with the print setup chunk is only historical — `0x0029+0x50`
(`dmPaperSize`) equals `+0x2E` in 103/130 Publisher 95 files, but no code copies either into
the other. [OBSERVED]

`+0x0A` and `+0x6A` are the exception to "memory equals file": `+0x0A` carries transient bits
(§4.7) and `+0x6A` is re-used as a runtime chunk-id cache (`VA 0x00535FCC` writes the Contents
stream id there after a save), which is why the in-memory `+0x6A` is an id while the on-disk
word is `Npages − 1`.

### 4.9.1 `+0x3C` is the default tab interval

* **Reader.** VA `0x00409F85` (text re-layout) loads the word into the layout context
  (`context + 0x11F`). VA `0x0040923B` consumes it as the tab advance:

  ```
  step = scale(*(int *)(context + 0x11F), 1440);        // 0x5A0 = twips per inch
  if (step == 0) step = 1;
  next = ((x + 1 + used) / step + 1) * step - used;     // next multiple of the interval
  ```

  `VA 0x00471BEE` is the scaling helper and the `1440` argument fixes the unit as twips.
  The corpus values are all round fractions of an inch — 360 = 0.25 in, 432 = 0.3 in,
  720 = 0.5 in, 1296 = 0.9 in. [OBSERVED for the code path; the "default tab stop" name is
  the only reading consistent with a next-multiple advance]

* **Writer.** VA `0x00557A69` copies `u16@settings+0x40` into `document+0x3C` when the two
  differ, marks the document dirty (`VA 0x00401A5B`) and re-lays the text of the chunk at
  `document+0x4E`. Publisher 98 writes the same field at `VA 0x0056CA1A`. [OBSERVED]

* **Refuted alternative.** The first column stop of the `0x0001` 14-byte tail (chapter 06
  §6.4.1) is an *absolute x in EMU*, not a tab interval: across the 141 tail-bearing
  Publisher 95/97 chunks with `A > 0`, `a[0] − left` takes 68 distinct values and never
  equals 457 200 EMU (= 720 twips). So the value is not derivable from table geometry.

### 4.9.2 `+0x2E`, `+0x30`, `+0x36` are never interpreted

No function in any of the three executables reads or writes these words: the complete
offset enumeration of every document-pointer access (`DAT_00587AA8` in 95,
`DAT_005D27C8` in 97, `DAT_00613920` in 98) contains no decimal `46`/`48` and no
`0x2E`/`0x30`, and neither does the inline chunk-table form. The DLLs never touch the
DOCUMENT chunk at all (scan scope in §4.9). The three words are therefore pure residue:
they arrive with the file and leave with it, and no UI or layout path branches on them.

Their provenance is the creating application's print setup, frozen at file-creation time.
`+0x2E` is the `dmPaperSize` paper code: it takes `{0,1,2,4,7,14}` over 493 files
(`1` letter, `2` letter-small, `4` ledger, `7` executive, `14` folio) and equals the live
print-setup record's `0x0029+0x50` (`dmPaperSize`) in 103/130 Publisher 95 files. The 27
mismatches are all staleness in one direction: the `0x0029` record was updated by a later
print-setup edit while the DOCUMENT word kept its creation value — `0x0029+0x50 == 265`
(`DMPAPER_USER` + driver offset, a driver-defined custom size) in 18 of them with
`+0x2E` still `0`/`1`/`7`, `0x0029+0x50 == 15` (quarto) in 2 with `+0x2E == 0`, and one
letter→executive drift (`+0x2E == 1`, `0x0029+0x50 == 7`). [OBSERVED over the 130-file
joint distribution of the two words]

`+0x30` is proven **not** to be `dmPaperLength`. A 16-bit `DEVMODE` `dmPaperLength` is a
length in tenths of a millimetre and is only defined when `dmPaperSize` is custom; the
observed domain is `{0,4,5,6,13,14}` over 493 files — two orders of magnitude too small
(letter would require 2790, the 20-inch banners 5080) — and the eleven files with
`+0x2E == 0` (custom) carry `0`/`4`, not a length. The word agrees with the live record's
`0x0029+0x52` in 68/130 files (equality concentrated on `{5,6}`), so it is the same
creation-frozen print-setup word, but no reader assigns it a role and its value set fits
no `DEVMODE` length member; its meaning beyond "second print-setup residue word" is not
recoverable from the shipped code. [OBSERVED negative with the refutation above]

The print path does not use this pair: the printer block the application really reads is
the one at `+0x2C`…`+0x40` of `DAT_005870E0`, from which VA `0x00457842` copies
`+0x2C`/`+0x2E`/`+0x30`/`+0x3C`/`+0x3E`/`+0x40` into six print-device globals. Nothing
bridges that block and the DOCUMENT word. `+0x36` has no reading at all. [OBSERVED
negative]

### 4.9.3 `+0x64` — publication type selector

Three switches read the word:

| VA | Behaviour |
|---|---|
| `0x004C6C37` | maps each value 3…0x1C onto a distinct index 0…0x16, then selects that item from a 23-item comma-delimited resource string |
| `0x004BF85F` | values 3…8, 10, 12…16, 18…24, 26…28 select the help/navigation topic `"NavCONTNTPS002"`; 11 selects `"NavCONTNT1001"`; the rest fall through to a `coordinateSystem`-based choice |
| `0x00561D04` | values 5, 6, 12, 13, 20, 28 post a repaint of the document window |

The corpus domain is 0…34 (0…26 in Publisher 95). The value tracks the publication type: all
35 label publications (`coordinateSystem == 8`) carry `+0x64 == 15`, and `15` is exactly the
index that the Publisher 97 layout table maps to `8` (§4.10). The remaining values are not
individually named. [OBSERVED for the consumers and the identity; the "publication type" name
is `[INFERENCE]`]

## 4.10 `coordinateSystem` (`+0x12`)

The word selects how the publication page is laid out on the sheet. The dispatcher is
VA `0x004DB30C`: it takes the page rectangle and rewrites it per value.

| Value | Geometry applied by `0x004DB30C` | Publication type |
|---|---|---|
| `0` | none (base rectangle) | one page printed on each sheet |
| `1` | x extent halved | two pages on each sheet, side by side |
| `2` | y extent halved | two pages on each sheet, stacked — the *two-page spread* view; View menu item `0x51` is enabled only for this value (VA `0x0043851F`) |
| `3` | both extents halved | four pages on each sheet, fold on the left |
| `4` | both extents halved, **and** every consumer swaps the page width/height pair (`0x004053C6`, `0x00430482`, `0x004649EE`, `0x0043C259`, `0x0045A038` use `DAT_0058963C−DAT_00589634` instead of `DAT_00589638−DAT_00589630`) | four pages on each sheet, fold on the top (page rotated 90°) |
| `5` | `FUN_0045AF20(6, rect)` → 5 × 3 in default | index card |
| `6` | `FUN_0045AF20(7, rect)` → 3.5 × 2 in default | business card |
| `7` | `FUN_0045AF20(0xB, rect)` → 60 in per banner unit | banner |
| `8` | none — no `case`, falls to the base rectangle | label (Publisher 97 only) |

Supporting evidence:

* **`0x0045AE4A`** returns the default page size for a layout code: code 6 → `0x45C360 ×
  0x29DBA0` (5 × 3 in in EMU), 7 → `0x30D590 × 0x1BE7C0` (3.5 × 2 in), 8 → 18 × 24 in,
  9 → 24 × 36 in, 11…13 → `(code−10) × 0x3452880` = 60/120/180 in tall.
* **Layout table.** VA `0x0045AE3C` reads `u32@0x0058EFB8 + code*4`; the 16 entries are
  `0,1,2,3,4,0,5,6,0,0,0,7,7,7,7,0`. Publisher 97's equivalent (`VA 0x0040AAA0`, table at
  `0x005BC0E8`) has the same 16 entries except index 15, which is `8` — the label type that
  Publisher 97 added. VA `0x0045BEF0` (95) and VA `0x0040A988` (97) write the result into
  `document+0x12`.
* **Banner.** VA `0x00430B56` sets the maximum page extent to `0x0D2295E0` for value 7 and
  `0x02B9A1C0` otherwise; VAs `0x0043A234`, `0x0048A0CB`, `0x004C781E`, `0x004D4709` raise the
  zoom floor from 71 % to 68 % for value 7.
* **`0x004DB5D4`** maps the value to a grid division count: 4 for 1/3/4, 2 for 2, 1 otherwise.
* **Page setup.** VA `0x0045A038` reads the word and, for every value except `5` and `6`, feeds
  the page rectangle through `0x004DB30C` and stores the result back into `document+0x14/+0x18`.
  The two card types are excluded because their page size is not derived from the sheet.
* **Device setup.** VA `0x0044325E` passes the word to `0x00430B56` every time the view's device
  context changes, so the banner page limit is re-applied per DC.
* **Corpus.** 8 never occurs in the 130 Publisher 95 documents; all 35 occurrences are
  Publisher 97 documents whose file names and page sizes are labels (`DSKLABL2.PUB` 2.75 ×
  2.75 in, `B7160.PUB` 2.5 × 1.5 in, …). Value 2 never occurs in the corpus at all — the
  dispatcher handles it, no shipped document uses it. [OBSERVED]

## 4.11 The descriptor pair at `+0x02` (closed)

Bytes `+0x02`/`+0x03` are **not** a length and are **not** read as a word by any code path.
They are the first two bytes of a static 54-byte-per-marker record template that the
chunk constructor copies into the header. (This code table is a different structure from the
header-block cache of chapter 02 §2.5: the block at `Contents +0x22` is written from the
document's chunks at save time, while the chunk bytes come from this fixed table, so the
two agree but have independent writers.) `[OBSERVED]`

**The template.** `FUN_00401440` (VA `0x00401440`) copies 54 bytes from
`0x00593308 + marker·0x36` into a local descriptor block; the block's fields are

```
+0x00 u8  A             -> chunk +0x02
+0x01 u8  B             -> chunk +0x03
+0x02 u8  alloc flags   (low 3 bits select the size/allocator class, see 0x004307F8)
+0x04 ...               per-family parameters (element size, id-field offsets)
```

Entry `0x15` of the Publisher 95 template is `78 6A 19 00 02 00 04 00 06 00 08 00 44 00
46 00 48 00 4A 00 …`: `A = 0x78`, `B = 0x6A` — the `0x6A78` word every DOCUMENT chunk
carries. The same template supplies every other marker's stamp (`0x14 → 1A 1A`,
`0x01 → 60 60`, `0x16 → 1A 10`, …), which is why chapter 12 §12.2 can list the stamp
per marker and version. The P97 template entry `0x15` is `9E 88` and the P98 one `D2 B2`
(0x889E / 0xB2D2) — the stamp is a *build* constant, not a document property.

**Who writes it.** `FUN_00407E46` (VA `0x00407E46`) is the header constructor: it calls
`FUN_00401440`, then writes `u16@+0x00 = marker`, `u8@+0x02 = A`, `u8@+0x03 = B`. Every
chunk-creating path reaches it through `FUN_004307F8` (VA `0x004307F8`, dispatch on the
entry's `+0x02 & 7`) or through `FUN_0040835C` (VA `0x0040835C`) and `FUN_00418404`
(VA `0x00418404`), both of which call `FUN_00407E46` on the freshly allocated payload.
On load, `FUN_0045FFD4` (VA `0x0045FFD4`) copies the first `B+1` bytes of the chunk from
disk verbatim and reads the remainder starting at offset `A`, so a loaded chunk keeps the
pair it was saved with.

**Who reads it.** Only as offsets, never as an identity:

* `A` is the constructor's internal split point: `FUN_00407D59` (VA `0x00407D59`) returns
  it, `FUN_0040835C`/`FUN_00418404` allocate and zero `A + 10` bytes for the in-memory
  buffer and write the record's secondary header at `payload + A`, `FUN_00444B6E`
  (VA `0x00444B6E`) computes `A − B` as the variable-length part, and the loader
  (`FUN_0045FFD4`) starts its second read at `A`. It is **not** the on-disk extent: the
  buffer carries slack, and the persisted record is `B + 10` bytes plus its elements (for
  the DOCUMENT `B + 10 = 116` while `A + 10 = 130`).
* `B` is the last fixed byte of the on-disk record — the extent that matters:
  `base = B + 10` for every family (chapter 06 §6.1, chapter 12 §12.2), and
  `FUN_00444B6E` reads `u8@+0x03` to bound the header read.
* No site compares `u16@+0x02` against a constant. The only word compared against a
  chunk's `+0x02` anywhere in the four builds is `FUN_005239E5` (VA `0x005239E5`), which
  tests `== 0x2C6` and `< 300` on a *style/font* record's `+0x02` (a version word), not on
  the descriptor.

There is no dispatch on the marker family through the pair: the family dispatch is the
marker at `+0x00` (chapter 17 §17.2) and the allocator class is entry byte `+0x02` of the
*template* (VA `0x004307F8`), never the bytes in the chunk. A reader therefore MUST
preserve `+0x02`/`+0x03` and MUST NOT derive the chunk size from either byte; the size
comes from `B`'s family law only through the tables in chapters 06/12.

Scan scope for the negative: all 15 072 decompiled functions of the nine shipped modules
(the same population as §4.9) were searched for the literal `0x6A78`, for the byte pair
`78 6A`, and for every access to a chunk payload's `+0x02`/`+0x03`; only the constructor
(write), the loader (copy/split) and the offset consumers above touch them. The 54-byte
template has exactly one reader, `FUN_00401440`, called from 19 sites.
