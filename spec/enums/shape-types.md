# Enums — shape and object types

The Publisher 95/97/98 object type is the **`u16` at chunk `+0x00`**. There is no separate
kind byte, no `shapeSpecifier` field, and no single dispatch switch over the marker domain.
This file publishes the closed marker domain, the one compact kind enum the binaries do
contain, and the descriptor bytes that go with each marker.

Evidence: `MSPUB.EXE` of all three generations (P98 decompiled at `notes/p98/decomp98`,
5 361 functions; P97 at `notes/p98/decomp97`, 4 253; P95 at `notes/p95/decomp`), plus the
487-document corpus. Detailed derivation in `notes/p98/slices/shape_enum.md`.

## 1. The marker domain is closed

`0x0000`–`0x0052`, and nothing above `0x0052` in any of the 487 documents. `0x000C` and
`0x000D` occur in no file and are referenced by no switch. [OBSERVED]

## 2. There is no marker dispatch switch

An exhaustive scan of the three decompiled corpora finds no `switch` whose case set spans
`0x00`–`0x52`, and a machine scan of the P98 image finds no indirect-jump table of ≥ 40
entries pointing into `.text` (the only large pointer arrays are C++ vtables, e.g. 146 dwords
at VA `0x005F5F60`). The loader stores the directory `flags` word verbatim and never
branches on the marker.

What exists is a **family of per-module switches**, each claiming the subset of kinds that
module must special-case, all reading
`switch (*(u16 *)(*(u32 *)(handle*0x10 + 8 + table)))`: [OBSERVED, binary]

| Function (P98) | Kinds with an explicit case | Role (from the bodies) |
|---|---|---|
| `0x0045574C` | `00–0B`, `0E`, `0F` | hit-test / bbox intersection; `04`, `06`, `07` have their own sub-routines |
| `0x00454D3F` | `00–03`, `05–08`, `0A`, `0B` | text inset / frame margins, in twips (`0x319C` = 12 700 per point) |
| `0x00454A4A` | `02`, `03`, `04`, `06`, `07` | extent / handle count |
| `0x0044686D` | `00–03`, `08–0A`, `0E` | resource release; `0A` frees three handles |
| `0x00419690` | `02`, `03`, `08`, `0A` | command-enable / UI state |
| `0x00426FA9` | `00–03`, `08`, `0A` | **marker → kind class**, §3 |
| `0x0049847E` | `01–04` | edit probe |
| `0x00537754`, `0x004854A2` | `02–0B` / `03`, `08`, `0A` | post-load fixups |
| `0x004B7D98`, `0x00453F5A` (P97) | `00–07` / `00`, `01`, `06`, `0E`, `0F` | P97 branches |
| `0x004188C8` (P95) | `00`, `01`, `06`, `0E`, `0F` | P95 commit path |

Union of the shape-marker switches: `0x00`–`0x0B`, `0x0E`, `0x0F`. Every marker from `0x10`
up is consumed by the document/page layer, never as a shape.

## 3. The one compact kind enum — `0x00426FA9`

The only place in the three executables where the marker domain collapses to a closed
numeric enum. Its caller (`0x005B5CFD`) uses the result as a drag-source/format selector,
so this is a **drag/insert class**, not the on-disk kind — but it must be reproduced
verbatim by any clone because it decides drag-and-drop behaviour. [OBSERVED, binary]

| Marker | Class |
|---|---|
| `0x0000`, `0x0008` | `0` |
| `0x0001`, `0x000A` | `1` |
| `0x0002` | `4` |
| `0x0003` | `6` |
| every other marker | `5` |

The caller special-cases `2` and `3`, which this function never returns.

## 4. The marker table

`A` = byte at `+0x02`, `B` = byte at `+0x03` (the fixed-part length, chapter 12). Counts are
chunks. [OBSERVED]

| Marker | p95 | p97 | p97dlx | p98 | Modal size | A | B | Class |
|---|---|---|---|---|---|---|---|---|
| `0x0000` | 1092 | 1211 | 2735 | 0 | 102 | 0x5E | 0x5C | free-form shape with polygon tail |
| `0x0001` | 218 | 157 | 360 | 5 | 106 | 0x60 | 0x60 | free-form variant |
| `0x0002` | 248 | 196 | 561 | 5 | 126 / 150 | 0x9C/0xA4 | 0x74 / 0x8C | image-bearing shape (chapter 08) |
| `0x0003` | 617 | 479 | 1520 | 5 | 126 / 150 | 0x9E/0xA6 | 0x74 / 0x8C | polygon shape; may own a `0x22` |
| `0x0004` | 696 | 665 | 1413 | 5 | 59 | 0x3B | 0x3B | line |
| `0x0005` | 1110 | 1062 | 2302 | 399 | 62 | 0x3E | 0x3E | rectangle |
| `0x0006` | 1322 | 867 | 1850 | 5 | 53 | 0x39 | 0x35 | OLE-object shape (chapter 15) |
| `0x0007` | 266 | 190 | 692 | 5 | 41 | 0x29 | 0x29 | smallest shape (ellipse/plain frame) |
| `0x0008` | 0 | 0 | 0 | 114 | 128 | 0x88 | 0x76 | 98-only shape |
| `0x0009` | 0 | 0 | 0 | 5 | 61 | 0x35 | 0x35 | 98-only shape |
| `0x000A` | 0 | 0 | 0 | 7 | 126 | 0x7D | 0x74 | 98-only shape, three handles |
| `0x000B` | 0 | 0 | 0 | 5 | 86 | 0x4E | 0x4E | 98-only shape |
| `0x000F` | 827 | 705 | 1394 | 9 | 38 | 0x18 | 0x18 | group (chapter 07) |
| `0x0014` | 712 | 593 | 1423 | 36 | 36 / 40 | 0x1A / 0x1E | 0x1A / 0x1E | page (chapter 05) |
| `0x0015` | 128 | 106 | 248 | 5 | 154 | — | — | document (chapter 04) |
| `0x0016` | 128 | 106 | 248 | 0 | 18 | 0x1C | 0x12 | document record of four chunk ids |
| `0x001A` | 128 | 106 | 248 | 0 | 54 | — | — | text story |
| `0x001C` | 128 | 106 | 248 | 0 | 34 | — | — | text story companion |
| `0x001E` | 128 | 106 | 248 | 5 | 92 | — | — | font table (chapter 11 §11.5) |
| `0x001F` | 128 | 106 | 248 | 5 | 26 | — | — | line/border-art style table |
| `0x0021` | 129 | 88 | 310 | 0 | varies | — | — | WMF payload (chapter 08) |
| `0x0022` | 489 | 373 | 1272 | 0 | 18 | — | — | `"MO"` + u16 ordinal (chapter 15) |
| `0x0023` | 128 | 106 | 248 | 5 | 50 | — | — | per-document table |
| `0x0026` | 128 | 106 | 248 | 0 | 51 | — | — | paragraph-style names |
| `0x0027` | 14 | 4 | 4 | 0 | 42 | 0x16 | 0x16 | picture object naming a `.wmf` (chapter 08) |
| `0x0028` | 128 | 106 | 248 | 5 | 56 | — | — | paper/print parameter block |
| `0x0029` | 128 | 106 | 248 | 5 | 205 | — | — | print setup |
| `0x002A` | 128 | 106 | 248 | 2 | 26 | — | — | font-substitution table |
| `0x002B` | 30 | 14 | 27 | 0 | 41 | — | — | document name list |
| `0x002C` | 137 | 115 | 275 | 6 | 58 | — | — | page text-frame record |
| `0x002D` | 128 | 106 | 248 | 0 | 26 | — | — | story table |
| `0x002E` | 128 | 106 | 248 | 0 | 26 | — | — | story table |
| `0x002F` | 0 | 4 | 8 | 0 | 38 | — | — | per-document table |
| `0x0031` | 384 | 413 | 991 | 15 | 30 | 0x08 | 0x08 | design/object set (chapter 11 §11.7) |
| `0x0032` | 384 | 318 | 744 | 15 | 26 / 16 | 0x04 | 0x04 | design name table |
| `0x0034` | 68 | 72 | 191 | 2 | 256 | — | — | 14-byte sub-table |
| `0x0035` | 74 | 66 | 166 | 0 | 200 | 0xC8 | 0xC8 | DLL binding record |
| `0x0036` | 0 | 0 | 0 | 1 | 112 | 0x70 | 0x70 | print-setup companion |
| `0x0037` | 16 | 36 | 126 | 5 | 14 / 20 | 0x04 | 0x04 | custom-colour list, 6-byte elements |
| `0x0038` | 15 | 18 | 94 | 0 | 14 | 0x04 | 0x04 | colour list, 10-byte elements (never populated) |
| `0x0039` | 128 | 106 | 248 | 5 | 48 / 56 | 0x4C / 0x58 | 0x30 / 0x38 | 48-byte document record |
| `0x003A` | 0 | 95 | 247 | 0 | 26 | — | — | 97+ record, absent from 95 and 98 |
| `0x003B` | 0 | 4 | 8 | 0 | 26 | — | — | 97+ record |
| `0x003F` | 0 | 13 | 22 | 0 | 180 | 0xB4 | 0xB4 | 97+ record |
| `0x0040` | 0 | 0 | 0 | 4 | 28 | 0x1C | 0x1C | 98-only, `u16 2` at `+0x04`/`+0x06` |
| `0x0041` | 0 | 0 | 0 | 5 | 40 | 0x1E | 0x1E | 98-only **page slot** |
| `0x0043` | 0 | 0 | 0 | 5 | 20 | 0x0A | 0x0A | 98-only, id list |
| `0x0045` | 0 | 0 | 0 | 5 | 8 | 0x38 | 0x08 | 98-only, ids of the `0x4C`/`0x52` pair |
| `0x0047` | 0 | 0 | 0 | 5 | 192 | 0x96 | 0x96 | palette (chapter 09) |
| `0x004C` | 0 | 0 | 0 | 5 | 40 | 0x12 | 0x12 | 98-only table |
| `0x004E` | 0 | 0 | 0 | 2 | 290 | 0x0A | 0x0A | 98-only, text-frame properties |
| `0x004F` | 0 | 0 | 0 | 2 | 306 | 0x0A | 0x0A | 98-only, text-frame properties |
| `0x0050` | 0 | 0 | 0 | 2 | 155 | 0x0A | 0x0A | 98-only, id pairs |
| `0x0052` | 0 | 0 | 0 | 5 | 40 | 0x12 | 0x12 | 98-only table |

## 5. Refuted: libmspub's `shapeSpecifier` at `+0x31`

libmspub reads a "shape type" byte at chunk `+0x31` for marker `0x06`. In this family that
byte is not a kind: across 4 044 `0x0006` chunks it takes 119 distinct values with no
dominant one, and the same offset in other markers carries unrelated data. The object kind
is the marker itself. Likewise libmspub's Escher `ShapeType` domain does not apply — no
corpus document has an `Escher` storage. [OBSERVED]

## 6. `A` and `B` — the descriptor pair

`A` (byte at `+0x02`) and `B` (byte at `+0x03`) are constant per marker within a document
and, for most markers, across the whole corpus. `B` is the **fixed-part length**: for a
record with a counted tail, `size == B + 10 + elementSize·count`; for a compact record,
`size == B`. `A` is a structural landmark — it equals the byte offset of the record's
primary count field in 15 of 21 container types (chapter 11 §11.9) and is mirrored into the
`Contents` header block for the shape classes (chapter 02 §2.5). [OBSERVED]

Consequence: a reader can validate any chunk by recomputing its size from `B` alone, and
can tell a Publisher 98 image shape from a 95/97 one by `B` (`0x8C` vs `0x74`) without
knowing the file's version.

## 7. Open

| Item | Status | Experiment |
|---|---|---|
| the semantic name of `0x0007` (ellipse vs plain frame) | `[INFERENCE]` | draw an ellipse and a frame, diff the two records |
| `0x0008`, `0x0009`, `0x000B`, `0x004E`, `0x004F`, `0x0050`, `0x004C`, `0x0052` interiors | `[UNKNOWN]` | these are 98-only; only the gallery documents exercise them |
| why `0x003A`/`0x003B`/`0x003F` exist only in 97/97deluxe | `[UNKNOWN]` | the 95 and 98 writers drop them; a 97-saved, 98-opened document would show whether the data moved into another record |
