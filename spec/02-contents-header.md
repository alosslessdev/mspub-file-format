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
| 0x06 | u16 | `writer_os_version` | `0x0004` in 120 files, `0x3303` in 8 — the low word of the writer's `GetVersion()` (§2.3) | §2.3 |
| 0x08 | u32 | `declared_length` | `== len(Contents)` in 128/128 | 128/128 |
| 0x0C | u16 | `header_tag` | `125` (0x007D) in 128/128 P95 files; **version-dependent** — see §2.2.1 | gate: value must be in the loader's accepted set |
| 0x0E | u16 | `document_chunk_id` | id of the DOCUMENT (0x15) chunk, **493/493** | §2.4 |
| 0x10 | u16 | `saved_page_id` | id of the 4th page in the document page order in 487/493; `0` in all 5 P98 documents | §2.4 |
| 0x12 | u32 | `text_section_offset` | `574` (0x0000023E) in all Publisher 95 files; 640 in 97, 894 in 98 — points at the `0x002EF0DE` text store (chapter 13 §13.14) | 493/493 |
| 0x16 | u32 | `directory_offset` | offset of the chunk directory | 128/128, §3 |
| 0x1A | u32 | `post_header_offset` | `34` (0x00000022) in 493/493 — the writer's cursor just past the 34-byte header; written but never read (§2.4.1) | 493/493 |
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
* The **validation gate** does not read `+0x06`, `+0x0E`, `+0x10`, `+0x1A`, `+0x1E` or
  `+0x20`: the 0x22-byte read is followed by checks on `+0x00`, `+0x04`, `+0x08` and
  `+0x0C` only. `+0x0E` and `+0x10` are consumed *after* the gate by the directory load
  and the first-open selection (§2.4); `+0x12`/`+0x16` are offsets used by the text and
  directory paths. [OBSERVED, binary]

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

## 2.3 `+0x06` — the writer's Windows version, not a format word

| Value | `GetVersion()` low word decodes to | Files |
|---|---|---|
| `0x0004` | 4.0 | 120 |
| `0x3303` | 3.51 | 8: `MSPUB.PUB`, `BIZTRIP.PUB`, `BRBLLOON.PUB`, `CONGRATS.PUB`, `MRBLBRDR.PUB`, `PERYARD2.PUB`, `SAILBOAT.PUB`, `STILLIFE.PUB` |

`u32 @0x04` is therefore `0x0004012C` in 120 files and `0x3303012C` in 8 files — the low half is
0x012C (300) in **both**, so the format version is identical; only the word at `+0x06` differs.
(An earlier note in `notes/EVIDENCE.md` reported `0x33025F2C`; that value does not occur in any
corpus file — the correct pair is 0x3303 / 0x012C.)

**It is the writer's OS version.** The save routine builds the 0x22-byte header in a stack
buffer and stores the *low 16 bits of `GetVersion()`* at `+0x06`: call VA `0x0053649F`, store
`[ebp-0x76]` at VA `0x005364A5`. The same builder writes magic `0xACE8` (VA `0x00536612`),
format 300 (VA `0x0053648C`) and tag 125 (VA `0x00536486`). `GetVersion` packs the major version
in the low byte and the minor version in the high byte of its low word, so the two observed
values decode as **4.0** (`0x0004`) and **3.51** (`0x3303`). `0x3303` is the version reported by
Windows NT 3.51; `0x0004` is reported by both Windows 95 and Windows NT 4.0. [OBSERVED for the
store and the corpus values; INFERENCE for the OS mapping — the binaries do not record the OS
name]

The value is a **producer-environment stamp**, not a document property. No other measured
property separates the eight: over the 128 `.PUB` files they span 34–61 chunks, 5–8 pages,
DOCUMENT `flags` 0x16C0 (1) and 0x16C8 (7), `+0x1E` ∈ {0, 0x100, 0x500}, directory offsets
0x2BC/0xA60/0xC60, `\x01CompObj` lengths 78 (6) and 94 (2), and an identical CFB header
(version 3, sector shift 9/6, minor version 62); every one of those values also occurs among the
120, and seven of the eight share their OLE root timestamp (1995-08-11) with 112 of the 120.
Nothing can be predicted from the stamp and nothing needs to be: all 130 load identically.
[OBSERVED; the OS mapping alone is [INFERENCE]]

## 2.4 `+0x0E` and `+0x10` — cached ids the open path consumes

Both are ids the writer caches and the open path resolves; neither is validated. Measured over
all 493 documents:

| Field | Identity | P95 | P97 | P97 deluxe | P98 |
|---|---|---|---|---|---|
| `+0x0E` | id of the DOCUMENT (`0x0015`) chunk | 130/130 | 108/108 | 250/250 | 5/5 |
| `+0x10` | entry at index **3** (4th page) of the page order | 130/130 | 108/108 | 249/250 | 0/5 |
| `+0x10` | `0` | — | — | — | 5/5 |

The page order is the DOCUMENT's page list: first page at DOCUMENT `+0x08`, the rest in the array
that follows. The version suffix shifts that array: `+0x74` for the P95 layout, `+0x92` for the
P97 layout (+30 bytes) and `+0xBC` for the P98 layout (+72). A P95-format document stored in a
97-era corpus (`p97/x/INFLNTLB.PUB`) keeps `+0x74`. Every document in all four corpora has at
least five pages, so index 3 always exists. [OBSERVED]

The single exception is `p97deluxe/x/PageWiz/aexhbroc.pub`: its page order is
`0x117, 0x108, 0x109, 0x10A, 0x16D, 0x10B` and `+0x10` holds `0x16D` — index 4. That is exactly
what a *cached* pointer does when a page is inserted after the field was written, and the field
is not recomputed on save. In Publisher 98 the writer leaves the word at `0`.

**What the open path does with them** (MSPUB.EXE P95, VA `0x0045F6B3`):

1. It reads the 0x22-byte header into a stack buffer (call VA `0x0045F797`). `+0x0E` and
   `+0x10` are adjacent words of that buffer.
2. It calls the directory loader with the directory offset (`+0x16`) and the *address* of the
   `+0x0E` word (call VA `0x0045F897`). At the end of the load the loader replaces the cached
   word with the result of the id-translation routine at VA `0x0044A942` and stores it back
   into the buffer (call VA `0x0049D1B8`, store VA `0x0049D1C0`). The open path then uses the
   translated value as the document chunk id: it clears bit 6 of that slot's status word
   (VA `0x0045F8D4`) and marks the slot in use (call VA `0x0045F8E7` → VA `0x0041D0C7`).
3. `+0x10` is read from the same buffer and passed through the same translation routine
   (call VA `0x0045F8A4`). On the first-open path it is then used to **select an object**: if
   the id is above `0xFF`, VA `0x00405984` returns its ordinal among its parent's children and
   VA `0x004415CD` activates that ordinal; then VA `0x00401A5B` sets bit 11 (the selection bit)
   on the object's status word. Values ≤ `0xFF` take the no-selection path.
   [OBSERVED for the data flow; INFERENCE that bit 11 means "selected"]

Consequently `+0x10` is the *page the document opens on* (the saved view/selection)
**[INFERENCE from the activation path]**, recorded
as a raw id at save time (the save routine uses the current-view global `DAT_00588550` when it
passes a validity test — call VA `0x00536533`, read VA `0x00536540` — otherwise element 2 of
the document's id list, VA `0x00536B54`), and resolved through the id map at open time. The
Publisher 97 open function does the same (VA `0x00416A83`; translation call VA `0x0042C59D`).

Neither field is validated: a stale or bogus id is passed through the translator unchanged and
then used as a table index / selection id. A reader must therefore treat `+0x0E` as a hint that
the DOCUMENT id exists and `+0x10` as a hint that the cached page still exists.

## 2.4.1 `+0x1A` — a save-time bookmark the loader never reads

`+0x1A` is `34` in 493/493 documents, but it is not a constant the code compares against or
uses as a loop bound. It is the writer's **file cursor just after the 34-byte header**: the save
routine writes the header at offset 0, advances the cursor by 0x22, and stores the cursor at
`+0x1A` (VA `0x0053650D`). It then writes the fixed block from that cursor and stores the block's
end at `+0x12` (574 in P95; VA `0x0053655D`). [OBSERVED]

In the Publisher 95 decompilation no code reads a header field at `+0x1A`: the loader's 0x22-byte
read length is an immediate, the open function's header-buffer accesses stop at `+0x16`, and the
directory loader receives `+0x16` and `+0x0E` only. The word is a writer bookmark ("the fixed
block starts here"), not a validation constant. A reader MAY require it to equal 0x22 as a
corpus invariant, but must derive offsets from `+0x12` and `+0x16`, never from `+0x1A`.
[OBSERVED, whole-binary decompilation]

## 2.5 The fixed block `0x22…0x23D`

Between the 34-byte header and the text store there is a **540-byte block** that is not a chunk:
it has no directory record, no type marker and no length field, and it always starts at the same
absolute offset. The text-section offset at header `+0x12` is exactly its end (`0x23E` in
Publisher 95), and the bookmark `34` at `+0x1A` (§2.4.1) is exactly its start, so the pair defines the
block. (Publisher 97/98 extend the header block itself, so the text section starts at 640 / 894
there; `+0x12` follows it in every generation.)

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
it is a copy of a **per-build, per-marker template** entry, and it is the reason the pair at
chunk `+2/+3` was long mistaken for a length: it is a descriptor pair, not a size. The template
table is at VA `0x00593308` with stride `0x36` (entry `0x00` = `5E 5C`, `0x01` = `60 60`,
`0x02` = `9C 74`, `0x03` = `9E 74`, `0x15` = `78 6A` in the Publisher 95 build; the 97 and 98
builds differ), and the header constructor at VA `0x00407E46` copies the entry into the record.
No reader compares the pair — it is write-only (chapter 04 §4.11).

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

`+0x20` is `0x0500` in all 130 P95 files (128 `.PUB` + 2 `.JSP`). `+0x1E` takes four values
(128 `.PUB`: 8 / 87 / 16 / 17; both `.JSP` carry `0x0500`):

| `+0x1E` | Files |
|---|---|
| `0x0500` | 10 |
| `0x0100` | 87 |
| `0x0300` | 16 |
| `0x0000` | 17 |

**Both words are write-only residue: no code path in `MSPUB.EXE` 95 ever reads them.** The
`0x0400` bit is part of the constant the builder assigns, not a state the application tracks.

* **Where the value comes from.** The header builder (VA `0x00535FCC`) stores the literal
  `0x0500` in `+0x20` unconditionally. For `+0x1E` it has two branches: when the freshly built
  document chunk's `+0x6A` word is `0`, it stores the same literal `0x0500` (VA `0x00535FCC`,
  store to the header copy at frame `+0x1E`); otherwise it copies two bytes out of a 34-byte
  record that VA `0x00444DB5` reads from the stream named by that word — the record's bytes
  `0x1E`/`0x1F` become the low/high byte of `+0x1E`. In other words the word is *inherited*
  from the document the new file was built from and never computed: `0x0100`, `0x0300` and
  `0x0000` are simply what the source header carried.
* **Why nothing reads it.** The open/validate function VA `0x0045F6B3` reads the 34-byte header
  into a stack buffer at VA `0x0045F797` and consumes only `+0x00` (magic `0xACE8`/`0xACE7`),
  `+0x04` (format version), `+0x08` (declared length), `+0x0C` (tag `0x7D`), `+0x0E` (document
  chunk id), `+0x10`, `+0x12`, `+0x14`, `+0x16`. The only callee that receives the whole buffer,
  VA `0x00523797`, reads just `+0x04`, `+0x0C`, `+0x0E` and `+0x1A`. The buffer is a stack local,
  so no other function can see it. Scan scope: all 3 825 functions of `MSPUB.EXE` 95, plus the
  `PUBOLE32.DLL` container layer that performs the stream I/O — the only stores to these two
  words are the builder's.

So the four observed values are an artefact of the source document, and the fixed `0x0400` part
is part of the builder's literal, not a flag the reader acts on. This retracts the earlier
"modified by the user after creation" reading.

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
0x12    3e 02 00 00     text-section offset 574 = 0x23E
0x16    bc 02 00 00     directory offset 700
0x1a    22 00 00 00     post-header bookmark 34 (§2.4.1)
0x1e    00 05           flags 0x0500
0x20    00 05           flags 0x0500
0x22    3a 00 06 00 5e 5c 09 00 02 00 00 00 60 60 01 00
0x32    0e 00 00 00 9c 74 01 00 08 00 6a 01 00 00 9e 74
```

The cell at `0x36` reads `0x749C` here, i.e. the descriptor pair (`0x9C`, `0x74`) of this
document's `0x0002` IMAGE chunks; the cell at `0x40` is the same pair with the first byte
incremented by 2. Both are per-file values, not constants (§2.5.1).
