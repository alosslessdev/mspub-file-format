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
| 0x0C | u16 | `header_tag` | `125` (0x007D) in 128/128 | gate: required when version == 300 |
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
| 6 | otherwise | requires `format_version` == 300 **and** `header_tag` == 0x007D, else error 0xF |

Consequences:

* `0xACE7` is a *legacy* magic (older Publisher). No Publisher 95 corpus file uses it; the corpus
  is entirely `0xACE8` / version 300 / tag 125. [OBSERVED]
* `0x02C6` (710) and `200` are the legacy format versions the Publisher 95 binary still accepts.
  [OBSERVED in the loader, unexercised by the corpus]
* The loader does **not** inspect `+0x06`, `+0x0E`, `+0x10`, `+0x12`, `+0x1A`, `+0x1E` or `+0x20`.
  [OBSERVED]

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

* `+0x0E` equals the id of the DOCUMENT chunk in all 128 files. The loader passes the *address*
  of this field to the directory loader (`FUN_0045E06A`), which writes a recomputed value back —
  so this is the "current document block id" slot maintained across load/save. [OBSERVED]
* `+0x10` is a PAGE id. Over 128/128 files it is exactly the entry at index 3 (the **4th page**)
  of the document's page order (first page from DOCUMENT +0x08, remaining pages from the
  DOCUMENT +0x74 array). Because the page order carries exactly five entries in every corpus
  file, index 3 always exists. [OBSERVED] Its *role* (current view page? a reserved page slot?)
  is [UNKNOWN]; the discriminating experiment is to change the current page in Publisher, save,
  and re-read `+0x10`.

## 2.5 The descriptor area `0x22…0x41`

Every word in this area is constant across the corpus except `0x36`. The three words at
`0x26`, `0x2E` and `0x36` are **exact mirrors of the two-byte per-chunk-type pair stored at
chunk offset +2/+3** (see chapter 04):

| Header word | Chunk type | Chunk bytes +2/+3 | Match |
|---|---|---|---|
| `0x26` | 0x00 | (`0x5E`,`0x5C`) = 94, 92 | 128/128 |
| `0x2E` | 0x01 | (`0x60`,`0x60`) = 96, 96 | 128/128 |
| `0x36` | 0x02 | (A, `0x74`) with A ∈ {140,144,152,156} = `0x8C/0x90/0x98/0x9C` | 128/128 |

This proves two things:

1. The pair at chunk +2/+3 is a **per-document, per-type constant**, recorded in the header at
   save time — not a per-chunk length and not an offset.
2. The values differ per chunk type, so they encode a type-specific property (most plausibly the
   size of the fixed prologue of that chunk type, or a record class). The exact meaning is
   [UNKNOWN]; chapter 04 tabulates the value for every observed type.

The remaining words (`0x22`, `0x24`, `0x28`, `0x2A`, `0x2C`, `0x30`, `0x32`, `0x34`, `0x38`,
`0x3A`, `0x3C`, `0x3E`, `0x40`) never vary in the corpus and there is no binary evidence yet for
their semantics. They are recorded as a fixed descriptor block. [UNKNOWN]

## 2.6 The `+0x1E` / `+0x20` flag words

`+0x20` is `0x0500` in all 128 files. `+0x1E` takes four values:

| `+0x1E` | Files |
|---|---|
| `0x0500` | 8 |
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
0x22    3a 00 06 00 5e 5c 09 00 02 00 00 00 00 00 60 60
0x32    01 00 0e 00 00 00 e9 01 01 00 08 00 6a 01 00 00
```

(`0x36` reads `e9 01` here because MSPUB.PUB's IMAGE chunk uses A = 0xE9 — the value tracks the
document's image record class, not a fixed constant.)
