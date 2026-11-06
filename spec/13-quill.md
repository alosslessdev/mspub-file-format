# 13 — The Quill text engine (Publisher 98 only)

Publisher 98 moved text out of `Contents` into a separate text engine whose data lives in
the stream **`Quill/QuillSub/CONTENTS`**. Publisher 95 and 97 have no `Quill` storage at
all (0 of 358 documents), so all their text is embedded in `Contents`; a reader must
handle both eras.

Five documents in the corpus carry a Quill stream — the two blank `.PUB` files and the
three `.JSP` publications on the Publisher 98 CD. They are small but structurally
complete: between them they exercise 14 of the chunk kinds.

## 13.1 Stream structure

The stream begins with a **chunk-reference list**:

```
+0x00  (payload)          ; the list header lives at 0x18 in every shipped file
...
0x18   u16 tag            0x0200 in the shipped files
0x1A   u16 count          number of records in this list
0x1C   u32 nextListOffset offset of the next list, 0xFFFFFFFF terminates the chain
0x20   record[count]                          24 bytes each
```

Record layout (24 bytes):

```
+0x00  u16  0x0018        record tag
+0x02  char[4] name       "TEXT", "STRS", "STSH", "SGP ", ...
+0x06  u16  id            chunk ordinal within the name
+0x08  u32  0x00000001
+0x0C  char[4] name2      usually equal to `name`
+0x10  u32  offset        absolute offset inside this stream
+0x14  u32  length         length in bytes
```

`[OBSERVED]` — 5/5 documents terminate the chain at `0xFFFFFFFF`, and every record's
`offset + length` lies inside the stream. This framing matches libmspub's
`parseQuillChunkReference`, i.e. two independent sources agree.

## 13.2 Chunk kinds observed

| Name | Docs | Instances | Role |
|---|---|---|---|
| `TEXT` | 3 | 3 | the character data |
| `STRS` | 3 | 3 | string table (styles/format names) |
| `FDPP` | 3 | 9 | paragraph property runs |
| `FDPC` | 3 | 5 | character property runs |
| `STSH` | 5 | 10 | style sheet(s); always two per document |
| `SYID` | 5 | 5 | style-id map |
| `FONT` | 5 | 5 | font table |
| `SGP ` | 5 | 5 | 4-byte document/section marker |
| `INK ` | 5 | 5 | 4-byte marker |
| `BTEP` | 3 | 3 | bookmark/table entry table |
| `BTEC` | 3 | 3 | bookmark/table entry count/list |
| `TCD ` | 1 | 2 | table cell data |
| `TOKN` | 1 | 1 | token table |
| `MCLD` | 3 | 3 | large binary blob (17 788 bytes in `CHEKLIST.JSP`) |

Measured sizes: `TEXT` 1 404 / 2 082 / 23 130 bytes; `STSH` from 30 to 1 324; `FONT` 60
to 156; `MCLD` 296 to 17 788. [OBSERVED]

The Quill engine also recognises a wider name set that the shipped documents do not
exercise: `PL  `, `SHPT`, `PLC `, `BMKT`, `PRNT`, `STSH2`, `TCD`. Strings for several of
these are present in `SHARED/QUILL/QS98.DLL` on the Publisher 98 CD. A reader must
dispatch on the name and skip unknown chunks by their recorded length.

## 13.3 `TEXT` — character data

`TEXT` is **UTF-16LE** text, starting directly at the first byte of the chunk (there is no
character-count prefix):

```
4D 00 69 00 63 00 72 00 6F 00 73 00 6F 00 66 00 74 00 20 00 ...
"M i c r o s o f t   P u b l i s h e r   9 8   C o l o r   S c h ..."
```

`[OBSERVED]` on all three documents with a `TEXT` chunk. Ranges of the character array are
referenced by the `FDPC`/`FDPP` runs and by shape text anchors; a reader maps a character
index to a byte offset by doubling it.

Control characters: the Publisher 95/97 in-`Contents` text layer used `0x0B` as a
non-breaking space and `0x0D 0x0A` as a paragraph separator; the 98 engine keeps the same
conventions in UTF-16. `[INFERENCE]` — inherited behaviour, not yet isolated per document.

## 13.4 `STRS` — string table

Header as observed: `u32 count`, `u32 relativeOffset` (= 8 in the sampled file), then a
`u32[count]` array at `4 + relativeOffset`. The array values are lengths, and the strings
follow the array. `[OBSERVED]` header shape; `[UNKNOWN]` the exact length semantics — in
`CLRCHK.JSP` the values sum to 702 while only 386 bytes follow the array, so the lengths are
**not** byte counts of a contiguous UTF-16 block. The discriminating experiment is a
document whose string table has one entry edited and the two candidate interpretations
diffed.

## 13.5 `FDPC` / `FDPP` — property runs

`FDPP` carries paragraph properties and `FDPC` character properties, as runs over the
`TEXT` character array. Both appear as fixed 512-byte records in the sampled documents —
512 is the block size of the Quill allocator, not a record size, so a reader must use the
run count inside the record rather than the chunk length. `[OBSERVED]` sizes;
`[UNKNOWN]` the run header layout. This is the largest remaining gap in this chapter.

## 13.6 `STSH` / `SYID` — style sheets and style-id map

Every document has exactly two `STSH` chunks (30 bytes + 60 bytes in the blank documents;
30 + 1 324 in `CHEKLIST.JSP`) and one `SYID`. In the blank documents `STSH` is small
enough to be a style-sheet header with no styles, which makes those two chunks the best
sample for decoding the header. `SYID` is 8 bytes in the blank documents and 68–384 bytes
in the populated ones — it maps style ids to style-sheet entries. `[OBSERVED]` sizes and
counts; `[UNKNOWN]` the field maps.

## 13.7 `FONT`

A font table in the same shape as the `Contents` font table (chapter 11 §11.5): a small
header followed by entries carrying a UTF-16 font name. `CLRCHK.JSP` starts
`78 00 00 00 02 00 00 00 a0 c3 bb 00 04 00 00 00 …` followed by
`"Abadi MT Condensed"` in UTF-16. `[OBSERVED]` that font names are stored UTF-16 and are
recoverable by scanning for the name; `[UNKNOWN]` the entry header fields.

## 13.8 How text attaches to shapes

The Quill stream holds the character array and the run tables; the shapes reference ranges
of it. The linkage is not yet pinned: candidates are the `SYID` map and a per-shape text id
in the shape record. `[UNKNOWN]` — this is the second-largest gap and the one that matters
most for rendering. The experiment: take `CHEKLIST.JSP` (which has 23 130 characters of
`TEXT` across several frames) and correlate shape order with `FDPP` run boundaries.

## 13.9 Publisher 95 / 97 text

Documents without a `Quill` storage carry their text **inside `Contents`**: the
`Contents +0x12` field points at a text section (constant 574 in the Publisher 95 corpus)
and the text chunks are part of the ordinary chunk list. `[OBSERVED]` that no 95/97 file has
a Quill storage; `[UNKNOWN]` the exact chunk markers used for the in-`Contents` text layer
— the candidates are the document-level records of chapter 11 and the `0x002B`/`0x0039`
family. Closing this is the remaining work for full text support of 95/97.

## 13.10 Validation

`tools/validate.py` checks that the chunk-reference chain terminates at `0xFFFFFFFF` inside
the stream (`quill_list_terminates`, 5/5) and `tools/pubread.py` lists the chunk names for
any document. Neither yet validates the payload layouts, because they are not published.

## 13.11 Open

| Item | Status | Experiment |
|---|---|---|
| `FDPC`/`FDPP` run header layout | `[UNKNOWN]` | decode `CHEKLIST.JSP` runs against its 23 130-character `TEXT` |
| `STSH`/`SYID` field maps | `[UNKNOWN]` | start from the 30-byte `STSH` of the blank documents |
| `STRS` length semantics | `[UNKNOWN]` | controlled edit of one string table entry |
| text → shape linkage | `[UNKNOWN]` | correlate `FDPP` boundaries with shape order |
| Publisher 95/97 in-`Contents` text chunks | `[UNKNOWN]` | compare a 97 document with and without a text frame |
| `MCLD`, `TOKN`, `BTEP`, `BTEC`, `TCD ` payloads | `[UNKNOWN]` | they appear in only one or three documents |
