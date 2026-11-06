# 02 — `Contents` header

The `Contents` stream begins with a fixed header. Publisher 95 reads exactly the first **0x22
(34) bytes** when opening a document, validates them, and only then parses the chunk directory.

**Binary evidence.** `MSPUB.EXE` VA `0x0045F6B3` is the open/validate function. It rejects a
stream shorter than 0x22 bytes (error 0xE), reads 0x22 bytes into a stack buffer, then applies
the checks summarised in §2.2 (error 0xE for bad magic or a declared length larger than the
stream, error 0xF for an unsupported version). The same function stores the document chunk id
into the in-memory document record and calls the directory loader `FUN_0045E06A` (VA
`0x0045E06A`) with the field at `+0x16` and the address of the `+0x0E` field.

## 2.1 Field table

All values measured over the 128-file corpus (`p95/x/**/*.PUB`). [OBSERVED unless noted]

| Offset | Width | Name | Value / meaning | Evidence |
|---|---|---|---|---|
| 0x00 | u16 | `magic` | `0xACE8` (bytes `e8 ac`) in 128/128 | 128/128 |
| 0x02 | u16 | `version_magic` | `0x0022` in 128/128 (byte 0x22, byte 0x00) | 128/128 |
| 0x04 | u16 | `format_version` | `300` (0x012C) in 128/128; loader also accepts 200 and 710 | gate 0x0045F6B3 |
| 0x06 | u16 | `writer_stamp` | `0x0004` in 120 files, `0x3303` in 8 | §2.3 |
| 0x08 | u32 | `declared_length` | `== len(Contents)` in 128/128 | 128/128 |
| 0x0C | u16 | `header_tag` | `125` (0x007D) in 128/128 P95 files; **version-dependent** — see §2.2.1 | gate: value must be in the loader's accepted set |
| 0x0E | u16 | `document_chunk_id` | id of the DOCUMENT (0x15) chunk, 128/128 | §2.4 |
| 0x10 | u16 | `page_4_id` | id of the 4th page in the document page order, 128/128 | §2.4 |
| 0x12 | u32 | `const_574` | `574` (0x0000023E) in 128/128 | 128/128 |
| 0x16 | u32 | `directory_offset` | offset of the chunk directory | 128/128, §3 |
| 0x1A | u32 | `const_34` | `34` (0x00000022) in 128/128 — equals the size of the header the loader reads | 128/128 |
| 0x1E | u16 | `flags_1e` | `0x0500` ×8, `0x0100` ×87, `0x0300` ×16, `0x0000` ×17 | 128/128 |
| 0x20 | u16 | `flags_20` | `0x0500` in 128/128 | 128/128 |
| 0x22 | u16 | descriptor | `0x003A` in 128/128 | 128/128 |
| 0x24 | u16 | descriptor | `0x0006` in 128/128 | 128/128 |
| 0x26 | u16 | mirror of shape A/B | `(A<<8)\|B` of type 0x00 chunks | §2.5 |
| 0x28 | u16 | descriptor | `0x0009` in 128/128 | 128/128 |
| 0x2A | u16 | descriptor | `0x0002` in 128/128 | 128/128 |
| 0x2C | u32 | descriptor | `0` in 128/128 | 128/128 |
| 0x2E | u16 | mirror of shape A/B | `(A<<8)\|B` of type 0x01 chunks — always `0x6060` | §2.5 |
| 0x30 | u16 | descriptor | `0x0001` in 128/128 | 128/128 |
| 0x32 | u16 | descriptor | `0x000E` in 128/128 | 128/128 |
| 0x34 | u16 | descriptor | `0` in 128/128 | 128/128 |
| 0x36 | u16 | mirror of image A/B | `(A<<8)\|B` of type 0x02 chunks; B always 0x74, A ∈ {0x8C,0x90,0x98,0x9C} | §2.5 |
| 0x38 | u16 | descriptor | `0x0001` in 128/128 | 128/128 |
| 0x3A | u16 | descriptor | `0x0008` in 128/128 | 128/128 |
| 0x3C | u16 | descriptor | `0x016A` in 128/128 | 128/128 |
| 0x3E | u16 | descriptor | `0` in 128/128 | 128/128 |
| 0x40 | u16 | descriptor | `0` in 128/128 | 128/128 |

The layout ends at 0x41; the first chunk of every corpus file starts at or after 0x41E
(`p95/x/MSPUB.PUB`: first chunk at 0x041E), so nothing between 0x22 and the first chunk is
chunk data.

## 2.2 Loader acceptance rules

From VA `0x0045F6B3` [OBSERVED, binary]:

| Rule | Condition | Result |
|---|---|---|
| 1 | stream length < 0x22 | error 0xE |
| 2 | `magic` ∉ {0xACE8, 0xACE7} | error 0xE |
| 3 | `declared_length` > actual stream length | error 0xE |
| 4 | `magic` == 0xACE7 and `format_version` == 0x02C6 | legacy-ACE7 path (sets the "legacy file" global) |
| 5 | `format_version` == 200 | legacy-200 path, requires `header_tag` == 0x02C0 else error 0xF |
| 6 | otherwise | requires `format_version` == 300 **and** `header_tag` in the build's accepted set (§2.2.1): P95 `{125}`, P97 `{125,136}`, P98 `{125,136,616}`; else error 0xF |

Consequences:

* `0xACE7` is a *legacy* magic (older Publisher). No corpus file uses it; every document is
  `0xACE8` / version 300, with the tag of its writer generation (§2.2.1). [OBSERVED]
* `0x02C6` (710) and `200` are the legacy format versions the Publisher 95 binary still accepts.
  [OBSERVED in the loader, unexercised by the corpus]
* The loader does **not** inspect `+0x06`, `+0x0E`, `+0x10`, `+0x12`, `+0x1A`, `+0x1E` or `+0x20`.
  [OBSERVED]

## 2.2.1 `header_tag` is version-scoped, not fixed

Rule 6 above is the **Publisher 95** binary's rule. The tag is not a format constant: each
generation writes a different value and each generation's loader accepts a different set.
Measured over all 493 documents (the `.JSP` publications included) and corroborated in the three
executables: [OBSERVED]

| Corpus | `header_tag` | Files | Loader acceptance |
|---|---|---|---|
| P95 (`p95/x`) | `125` (`0x007D`) | 130/130 | P95 `0x0045F6B3`: `125` only |
| P97 (`p97/x`) | `136` (`0x0088`) | 107/108; the remaining file is a P95-format document writing `125` | P97 `0x00416A83`: `125` or `136` |
| P97 deluxe | `136` | 250/250 | " |
| P98 (`p98/x`) | `616` (`0x0268`) | 5/5 | P98 `0x004FA80A`: `125`, `136` or `616` |

Consequences for a reader:

* A file whose tag is `136` or `616` is **not** corrupt and is not a legacy file; it is a
  97 or 98 document. Rejecting anything but `125` rejects 363 of the 493 documents.
* The accepted set grows monotonically across generations, which is how one binary can open
  older documents — so the tag is a *writer generation* discriminator, like the `+0x06`
  stamp (§2.3) and the chunk descriptor pairs (§2.5).
* The earlier statement in this chapter that the tag is `125` "required when version == 300"
  describes only the Publisher 95 build. [Correction, measured 487/487]

## 2.3 The `+0x06` stamp and its two populations

| Value | Files |
|---|---|
| `0x0004` | 120 |
| `0x3303` | 8: `MSPUB.PUB`, `BIZTRIP.PUB`, `BRBLLOON.PUB`, `CONGRATS.PUB`, `MRBLBRDR.PUB`, `PERYARD2.PUB`, `SAILBOAT.PUB`, `STILLIFE.PUB` |

`u32 @0x04` is therefore `0x0004012C` in 120 files and `0x3303012C` in 8 files — note the low
half is 0x012C (300) in **both**, so the *format version is identical*; only the word at `+0x06`
differs. (An earlier note in `notes/EVIDENCE.md` reported `0x33025F2C`; that value does not occur
in any corpus file — the correct pair is 0x3303 / 0x012C.)

The writer path sets this word from `GetVersion()` (`MSPUB.EXE` VA `0x00535FCC`, the
"new document" initialiser, stores `(short)GetVersion()` into the header word at +0x06 before
serialising the 0x22-byte header). `0x3303` is therefore a **producer-environment stamp**, not a
format discriminator: the eight files were written on a different Windows configuration than the
other 120. [INFERENCE — the store of `GetVersion()` is observed; the exact mapping from a
reported Windows version to `0x3303` is not reproduced.]

The eight files are otherwise ordinary: same version 300, same tag 125, same structure, and they
load normally. [OBSERVED]

## 2.4 `+0x0E` and `+0x10`

* `+0x0E` equals the id of the DOCUMENT (0x0015) chunk in **130/130** P95 documents. The loader
  passes the *address* of this field to the directory loader (`FUN_0045E06A`), which writes a
  recomputed value back — so this is the "current document block id" slot maintained across
  load/save. Immediately after loading, the open function calls `FUN_0041D0C7(docId, 1)`
  (VA `0x0041D0C7`), which sets the low two bits of that chunk's in-memory `flags` word — the
  document is marked as in use. [OBSERVED]
* `+0x10` is a PAGE id: it equals the entry at index **3** (the 4th page) of the document's page
  order (first page from DOCUMENT `+0x08`, the rest from the DOCUMENT `+0x74` array) in
  **130/130** P95 documents, **108/108** Publisher 97 documents and **249/250** Publisher 97
  deluxe documents. Because the page order has at least five entries in every P95 document,
  index 3 always exists. In Publisher 98 the field is `0` in all 5 documents (the record moved).
  [OBSERVED] Its *role* (current view page? the page shown when the file opens?) is [UNKNOWN];
  the discriminating experiment is to change the current page in Publisher, save, and re-read
  `+0x10`. The one P97-deluxe exception is a document whose page order changed after the field
  was written, which is consistent with "cached pointer, not recomputed on save".

## 2.5 The fixed block `0x22…0x23D`

Between the 34-byte header and the text store there is a **540-byte block** that is not a chunk:
it has no directory record, no type marker and no length field, and it always starts at the same
absolute offset. The constant `574` at header `+0x12` is exactly its end (`0x23E`), and the
constant `34` at `+0x1A` is exactly its start, so the pair of constants defines the block.

Across the 130 P95 documents **537 of its 540 bytes are identical**; exactly three bytes vary
[OBSERVED]:

| byte(s) | values (files) | note |
|---|---|---|
| `0x36`/`0x37` | `0x7490` ×64, `0x749C` ×50, `0x7498` ×15, `0x748C` ×1 | low byte varies, high byte always `0x74` |
| `0x40`/`0x41` | `0x7492`, `0x749E`, `0x749A`, `0x748E` (same grouping) | always **the 0x36 value + 2** |
| `0x15A` | `0x66` ×129, `0x88` ×1 | single outlier (`CHEKLIST.JSP` variant) |

There are therefore exactly **four** whole-block variants over the P95 corpus, and they differ
only in that one 16-bit cell written twice. The block is *version-specific*: Publisher 97 has
two variants of its own (50/58 files each) and Publisher 98 has one; only `INFLNTLB.PUB` — a
Publisher 95-format document shipped on the Publisher 97 CD — shares a P95 variant.

Complete dump (`p95/x/MSPUB.PUB`, variant `0x749C`; the only bytes that can differ are marked
`*`):

```
       0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
022   3a 00 06 00 5e 5c 09 00 02 00 00 00 60 60 01 00
032   0e 00 00 00*9c*74 01 00 08 00 6a 01 00 00*9e*74
042   01 00 08 00 6a 01 00 00 3b 3b 00 00 00 00 00 00
052   3e 3e 00 00 00 00 00 00 39 35 00 00 00 00 00 00
062   29 29 00 00 00 00 00 00 00 00 00 00 00 00 00 00
072   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
082   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
092   00 00 00 00 00 00 00 00 1a 1a 19 00 04 00 18 00
0a2   00 00 18 18 19 00 02 00 00 00 00 00 00 00 00 00
0b2   00 00 04 04 01 00 00 00 00 00 04 04 02 00 00 00
0c2   00 00 04 04 03 00 00 00 00 00 1a 1a 19 00 02 00
0d2   04 00 06 00 00 00 78 6a 19 00 02 00 04 00 06 00
0e2   08 00 44 00 46 00 48 00 4a 00 4c 00 4e 00 50 00
0f2   52 00 54 00 56 00 58 00 5a 00 5c 00 5e 00 60 00
102   62 00 68 00 00 00 1a 10 00 00 00 00 08 00 0a 00
112   0e 00 10 00 12 00 0c 00 14 00 00 00 00 00 00 00
122   00 00 00 00 04 04 02 00 08 00 00 00 04 04 02 00
132   10 00 00 00 04 04 0a 00 0a 00 00 00 04 04 1a 00
142   02 00 00 00 04 04 02 00 04 00 00 00 04 04 02 00
152   02 00 00 00 08 04 03 00*66 00 00 00 04 04 03 00
162   00 00 00 00 04 04 03 00 00 00 00 00 00 08 00 00
172   00 00 00 00 00 08 00 00 00 00 00 00 04 04 03 00
182   00 00 00 00 76 00 01 00 80 00 00 00 36 00 01 00
192   40 00 00 00 04 04 43 00 32 00 00 00 16 16 04 00
1a2   00 00 04 01 00 00 10 10 01 00 05 00 00 00 2c 2c
1b2   a3 00 00 00 10 00 00 00 04 04 03 00 00 00 00 00
1c2   04 04 03 00 00 00 00 00 18 18 01 00 06 00 00 00
1d2   04 04 02 00 04 00 00 00 04 04 02 00 05 00 00 00
1e2   08 08 02 00 04 00 06 00 00 00 04 04 03 00 00 00
1f2   00 00 08 08 02 00 04 00 06 00 00 00 04 04 03 00
202   00 00 00 00 04 04 04 00 00 00 00 00 24 24 01 00
212   0e 00 00 00 c8 c8 08 00 00 00 00 00 70 70 00 00
222   0e 00 00 00 04 04 01 00 06 00 00 00 04 04 01 00
232   0a 00 00 00 4c 30 00 00 00 00 00 00 de f0 2e 00
```

(`*` marks the only variable bytes; `0x23E` is not part of the block — it is the text store's
signature `0xF0DE` followed by its own 46-byte sub-header.)

### 2.5.1 Structure: the shape-class descriptor table

The block opens with a **table of the `(A, B)` descriptor pairs of the eight basic shape
classes**, in marker order, one cell per type [OBSERVED: 130/130 files, 130/130 cell checks]:

| block cell | cell bytes | type | `(A,B)` of every chunk of that type | varies per file? |
|---|---|---|---|---|
| `0x26` | `5e 5c` | `0x0000` | (0x5E, 0x5C) | no |
| `0x2E` | `60 60` | `0x0001` | (0x60, 0x60) | no |
| `0x36` | `9c 74` | `0x0002` | (0xA?, 0x74), A ∈ {0x8C, 0x90, 0x98, 0x9C} | **yes** |
| `0x40` | `9e 74` | `0x0003` | (0xA?+2, 0x74), A ∈ {0x8E, 0x92, 0x9A, 0x9E} | **yes** |
| `0x4A` | `3b 3b` | `0x0004` | (0x3B, 0x3B) | no |
| `0x52` | `3e 3e` | `0x0005` | (0x3E, 0x3E) | no |
| `0x5A` | `39 35` | `0x0006` | (0x39, 0x35) | no |
| `0x62` | `29 29` | `0x0007` | (0x29, 0x29) | no |

Each cell is the little-endian `u16` `B<<8 | A`, i.e. the two bytes that every chunk of that
marker carries at `+2/+3`. The table is written at save time from the document's own chunks, so
it is a *cache of a per-document constant*, and it is the reason the pair at chunk `+2/+3` was
long mistaken for a length: it is a per-type, per-document descriptor, not a size.

**The four block variants are therefore not noise.** Only types `0x0002` and `0x0003` have a
first descriptor byte that varies between documents, and on every file `A(0x03) = A(0x02) + 2`.
The 4 variants correspond exactly to the 4 observed values of `A(0x02)`:

| `A(0x02)` / `A(0x03)` | documents | cell bytes at `0x36` / `0x40` |
|---|---|---|
| 0x9C / 0x9E | 50 | `9c 74` / `9e 74` |
| 0x90 / 0x92 | 64 | `90 74` / `92 74` |
| 0x98 / 0x9A | 15 | `98 74` / `9a 74` |
| 0x8C / 0x8E | 1 | `8c 74` / `8e 74` |

The remaining `A A` cells further on (`04 04`, `08 08`, `10 10`, `16 16`, `18 18`, `24 24`,
`c8 c8`, `70 70`, …) and the DOCUMENT's own pair `0x6A78` at `0x0D6` follow the same idea for
record classes that are not shape chunks; nothing in the P95 corpus indexes those cells by
offset, and no chunk payload references the block. [INFERENCE]

Two consequences that matter to a reader:

1. Do **not** derive a chunk's extent from anything in this block. It is fixed for a given
   writer build apart from the two shape-class cells.
2. Do **not** treat the block as chunk data: it has no marker, no length and no directory
   record. Its extent is exactly `[0x22, 0x23E)` — the two header constants `34` and `574`.

## 2.5.2 Notes on the earlier reading

Three errors in the previous revision of this chapter are corrected here:

* `0x40` was listed as `0` in every file. It is not: it holds the descriptor pair of type
  `0x0003` and equals `0x749E` when `0x36` holds `0x749C`.
* The block was described as ending at `0x41`. It ends at `0x23E`; `0x22…0x41` is only its
  first quarter.
* `0x36` was described as "type 0x02's pair, A tracks the file". It does — but the second
  cell at `0x40` is a *different type's* pair (`0x0003`), not a copy of the first.

## 2.6 The `+0x1E` / `+0x20` flag words

`+0x20` is `0x0500` in all 130 files. `+0x1E` takes four values:

| `+0x1E` | Files |
|---|---|
| `0x0500` | 10 |
| `0x0100` | 87 |
| `0x0300` | 16 |
| `0x0000` | 17 |

Both are written as the constant `0x0500` by the new-document initialiser (VA `0x00535FCC`),
so `+0x1E` is subsequently *modified* by something the user does in the document. Bit 8 is set
in three of the four values, bit 9 in two; the word therefore behaves like a two-bit state pair
with a fixed `0x0400` part. Semantics [UNKNOWN]; candidate: "document has been modified / has
print settings". The experiment that would close it is a save-after-edit diff.

## 2.7 Worked example

`p95/x/MSPUB.PUB`, `Contents` length 2780 (0x0ADC):

```
offset  bytes           meaning
0x00    e8 ac           magic 0xACE8
0x02    22 00           version magic 0x0022
0x04    2c 01           format version 300
0x06    03 33           writer stamp 0x3303
0x08    dc 0a 00 00     declared length 2780 = len(Contents)
0x0c    7d 00           header tag 125
0x0e    00 01           document chunk id 0x0100 = 256
0x10    0a 01           page-4 id 0x010A = 266
0x12    3e 02 00 00     constant 574
0x16    bc 02 00 00     directory offset 700
0x1a    22 00 00 00     constant 34
0x1e    00 05           flags 0x0500
0x20    00 05           flags 0x0500
0x22    3a 00 06 00 5e 5c 09 00 02 00 00 00 60 60 01 00
0x32    0e 00 00 00 9c 74 01 00 08 00 6a 01 00 00 9e 74
```

The cell at `0x36` reads `0x749C` here, i.e. the descriptor pair (`0x9C`, `0x74`) of this
document's `0x0002` IMAGE chunks; the cell at `0x40` is the same pair with the first byte
incremented by 2. Both are per-file values, not constants (§2.5.1).
