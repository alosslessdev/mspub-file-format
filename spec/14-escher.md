# 14. Escher / the drawing layer

## 14.1 Summary

**Publisher 95, 97 and 98 documents do not contain an Escher stream.** All
drawing and text-object data for these versions is stored as ordinary chunks
inside the `Contents` stream (chapters 04–12). The `Escher/EscherStm` and
`Escher/EscherDelayStm` storages that the published reference implementation
(libmspub, MPL-2.0) reads belong to the Publisher 2000+ family, which uses
version magic `0x2C` and is out of scope for this document set.

The evidence is a full enumeration of every OLE2 path in every file of the
three in-scope corpora plus the Publisher 98 CD:

| corpus | files | OLE2 paths containing `escher` (any case) | files with `Quill/*` |
|---|---|---|---|
| `p95/x` (Publisher 95 installer templates) | 128 | 0 | 0 |
| `p97/x` (Publisher 97 disk set) | 106 | 0 | 0 |
| `p97deluxe/x` (Publisher 97 CD) | 248 | 0 | 0 |
| `p98/x` (Publisher 98 CD) | 2 | 0 | 2 |
| **total** | **484** | **0** | **2** |

`[OBSERVED]` — enumeration performed over all 484 files; the complete
top-level storage/stream name set is
`\x01CompObj`, `\x03Internal`, `\x05SummaryInformation`, `Contents`, `Objects`
(95/97/98) plus `Quill` (98 only). No other top-level name occurs.

The shipped executables agree:

| binary | `Escher` | `EscherStm` | `Quill` | `QuillSub` |
|---|---|---|---|---|
| `p95/x/MSPUB.EXE` (2 419 200 B) | 0 | 0 | 0 | 0 |
| `p97/x/MSPUB.EXE` (2 508 048 B) | 0 | 0 | 0 | 0 |
| `p98/bin/MSPUB.EXE` (2 241 808 B) | 0 | 0 | 2 | 0 |

`[OBSERVED]` — byte counts of the ASCII and UTF-16LE encodings of each literal
in each binary; both encodings were searched. The Publisher 98 binary loads its
text engine by name (`QS98`, UTF-16LE, one occurrence) which is the DLL shipped
as `SHARED/QUILL/QS98.DLL` on the Publisher 98 CD.

Consequence: a compliant reader for the 0x22 family **must not** require an
`Escher` storage, and a writer must not emit one. Any file that has one is a
Publisher 2000+ document (check `Contents[2]`: `0x2C` rather than `0x22`).

## 14.2 What the drawing layer actually is in 95/97/98

A shape is one `Contents` chunk. Its type marker selects the record variant:

| marker | role | payload size in the corpus |
|---|---|---|
| `0x0000` | shape, general | 102 … 110 |
| `0x0001` | shape variant 1 | 106 … 428 |
| `0x0002` | shape variant 2 (image-like) | 126 |
| `0x0003` | shape variant 3 | 126 … 926 |
| `0x0004` | line | 59 |
| `0x0005` | rectangle | 62 |
| `0x0006` | shape, compact | 53 |
| `0x0007` | shape variant 7 | 41 |
| `0x0008` | shape variant 8 | (see chapter 06) |
| `0x000F` | group | see chapter 07 |
| `0x0016` | document-level shape table record | 16 or 18 |
| `0x0031` | logo/group-like owner | 30 |

`[OBSERVED]` — sizes are the modal payload length over `p97/x`; full tables and
the field maps are in chapter 06 and 07.

Drawing z-order and ownership are expressed by the chunk directory
(`parent` + ascending `chunkOffset`), not by an Escher `SpContainer` tree.
Chapter 03 defines the directory; chapter 07 defines how groups order children.

## 14.3 Record-type inventory (observed)

Because there is no Escher stream, there is no Escher record-type inventory to
publish for this version family. The only "record types" that exist are the
`Contents` chunk markers, inventoried in `notes/p97/slices/dir_inventory.md`
(complete list for all four corpora) and summarised in chapter 18.

For completeness, the mapping a reader needs from the 2000+ vocabulary to this
one:

| Escher concept | 95/97/98 equivalent |
|---|---|
| `SpContainer` (shape) | one shape chunk (`0x00`…`0x08`, `0x16`) |
| `SpgrContainer` (group) | `0x0F` chunk (children = directory children) |
| `OPT` property table (FOPT) | fixed prologue fields of the shape record (chapter 06) |
| `SpPr` / fill `fFill` | fill-type byte and fill-colour index in the shape prologue |
| `x`/`y`/`cx`/`cy` in the `Sp` record | EMU quad in the shape prologue |
| `rotation` | rotation field in the shape prologue |
| `pFopt` blip reference | image chunk (`0x02`/`0x21`) referenced by the shape |

`[INFERENCE]` — the right-hand column is a correspondence, not an encoding:
the left-hand names do not appear in the files.

## 14.4 Open

* `Q14-1` — Do Publisher 2000+ files (`Contents[2] == 0x2C`) really carry
  `Escher/EscherStm`, and is it identical to the OfficeArt record stream? Out of
  scope here; experiment: obtain one Publisher 2000 document and enumerate its
  storages, then compare record framing with the OfficeArt specification.
* `Q14-2` — If a Publisher 98 document is later found that contains an Escher
  storage (none of the two shipped .PUB files does), re-open this chapter.
  Experiment: enumerate storages of every .PUB on any further Publisher 97/98
  media before accepting this chapter as final.
