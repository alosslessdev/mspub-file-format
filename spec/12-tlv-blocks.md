# 12 — Sub-record framing: fixed records, not typed blocks

This chapter defines how the payload of a chunk is framed. It also records a
**negative result** that changes how every other chapter must be read: the
`{u8 id, u8 type}` typed-block ("TLV") system used by libmspub and by Publisher
2000 and later **does not exist in the Publisher 95 / 97 / 98 document format**.

Everything below is measured over 484 documents
(`p95/x` 128, `p97/ext2` 106, `p97deluxe/x` 248, `p98/x` 2) unless stated
otherwise. All values little-endian.

## 12.1 Verdict

A Publisher 95-98 chunk payload is a **fixed-layout binary record** whose shape
is determined by its `u16` type marker. There is no id/type sub-record stream
inside it. The only variable parts are (a) a counted trailing array of fixed-size
elements (12.4), (b) a length-prefixed binary blob for two markers (12.5), and
(c) explicitly counted string/offset data in the document-level records
(chapters 04, 05, 11).

### Evidence [OBSERVED]

1. **No chunk type walks as a block list.** Using libmspub's block-length table
   (`getBlockDataLength`: `{0x78,0x05,0x08,0x0A} -> 0`, `{0x10,0x12,0x18,0x1A,0x07} -> 2`,
   `{0x20,0x22,0x58,0x68,0x70,0xB8} -> 4`, `0x28 -> 8`, `0x38 -> 16`, `0x48 -> 24`,
   variable for `{0xC0,0x80,0x82,0x88,0x8A,0x90,0x98,0xA0}`), and requiring the
   walk to end exactly at the payload end with at least two blocks, **no marker
   reaches 10 %** over all start offsets 0..63. Best case is `0x05` at 314/3412
   (9 %), which is an artefact of a 62-byte fixed record whose last bytes are
   `00 00`. Reproduce: `notes/p98/slices/tlv-inventory.md` and the script
   `tools/p98_tlvscan.py`.

2. **Two markers have a length-prefixed blob and nothing else** (12.5):
   `0x0021` 527/527 and `0x0022` 2134/2134 chunks satisfy
   `u32@+4 == chunkSize - 8`. Every other marker satisfies it 0 times.

3. **Record sizes are modal and stable.** Per marker the size histogram is
   dominated by one value (12.6): e.g. `0x04` is 59 bytes in 2774/2776 chunks,
   `0x05` 62 in 4474/4476, `0x22` exactly 18 in 2134/2134, `0x2E` exactly 26 in
   482/482.

4. **A `00 00` doublet is not a terminator.** It was proposed as one; it is an
   ordinary zero value. `0x22` chunks end in `00 00` because their last payload
   bytes are zero, not because a list ends there.

> **Reader warning.** Any table in this document set that lists "block ids" for
> Publisher 95-98 predates this measurement. The id/type space is a Publisher
> 2000+ feature (12.8) and is out of scope here.

## 12.2 The chunk record header

Every chunk payload begins:

| Offset | Width | Field | Notes |
|---|---|---|---|
| 0x00 | u16 | `type_marker` | the chunk type (see 12.6) |
| 0x02 | u8 | `stamp_lo` | per-record schema stamp, low byte |
| 0x03 | u8 | `stamp_hi` | per-record schema stamp, high byte |

`type_marker` is the same value that selects the handler in the loader; it is
what the directory is keyed on indirectly (chapters 03, 04).

### The schema stamp `(stamp_lo, stamp_hi)` [OBSERVED]

The two bytes are **constant per marker within a document** and **constant across
the whole corpus for most markers** (2480 marker/file combinations, 3 exceptions).
They are not a length: for `0x04` (line) they equal the record size (59 = `0x3B`),
for `0x06` they are `size` and `size+4`, for `0x22` they are `0` and `8`, for
`0x31` they are `8` and `8`.

The stamps are a **writer-generation fingerprint**: for the same marker the
stamp differs between Publisher 95, 97 and 98, which makes them usable for
version detection independent of the header:

| Marker | P95 stamp | P97 stamp | P98 stamp | Note |
|---|---|---|---|---|
| 0x0000 SHAPE | `0x5C5E` | `0x5C5E` | — | `(size-8, size-10)` |
| 0x0001 | `0x6060` | `0x6060` | `0x6868` | `(size-10, size-10)` |
| 0x0002 IMAGE | `0x749C` / `0x7490` | `0x749C` / `0x74A4` | `0x8CBC` | `(size+30, size-10)` for 102/94 |
| 0x0003 | `0x749E` / `0x7492` | `0x749E` / `0x74A6` | `0x8CBE` | `(size+32, size-10)` |
| 0x0004 LINE | `0x3B3B` | `0x3B3B` | `0x4343` | `(size, size)` |
| 0x0005 RECT | `0x3E3E` | `0x3E3E` | `0x4646` | `(size, size)` |
| 0x0006 | `0x3539` | `0x3539` | `0x3D41` | `(size+4, size)` |
| 0x0007 ELLIPSE | `0x2929` | `0x2929` | `0x3131` | `(size, size)` |
| 0x000F GROUP | `0x1818` | `0x1818` | — | `(size-14, size-14)` on the modal 38 |
| 0x0014 PAGE | `0x1A1A` | `0x1A1A` | `0x1E1E` | `(size-10, size-10)` on the modal 36 |
| 0x0015 DOCUMENT | `0x6A78` | `0x889E` | `0xB2D2` | `(base-18, base-4)` |
| 0x0016 | `0x101A` | `0x121C` | — | `(size+10, size)` |
| 0x001E | `0x0408` | `0x0408` | `0x0408` | |
| 0x0021 IMAGE_DATA | `0x0800` | `0x0800` | — | blob header (12.5) |
| 0x0022 | `0x0800` | `0x0800` | — | blob header (12.5) |
| 0x0031 LOGO | `0x0808` | `0x0808` | `0x0808` | |
| 0x0039 | `0x304C` | `0x304C` | `0x3858` | `(size+28, size)` |
| 0x0044… | — | — | `0x1C1C` 0x40, `0x1E1E` 0x41, `0x0A0A` 0x43, `0x0838` 0x45, `0x9696` 0x47, `0x1212` 0x4C/0x52 | 98-only markers |
| all other small records | `0x0404` | `0x0404` | `0x0404` | 0x1A/0x1C/0x1F/0x23/0x26/0x2A/0x2B/0x2D/0x2E/0x32/0x37/0x38/0x3A/0x3B |

The full per-marker table with counts is in `blocks/tlv-id-table.md` §A.

**Relation to the `Contents` header.** The header carries the same stamps for the
record types that occur in the document, so the stamp can be re-derived without
scanning chunks. Publisher 95: header `u16@0x26` = shape-0x00 stamp, `@0x2E` =
0x01, `@0x36` = 0x02, `@0x40/@0x4A/@0x52/@0x5A/@0x62` = 0x03/0x04/0x05/0x06/0x07.
[OBSERVED, see 02-contents-header.md §2.5]

The derivation of the stamp values is **[UNKNOWN]**. The measured relations in
the last column of the table above are exact for the modal size and are recorded
so a reader can validate a candidate formula.

## 12.3 Record families

| Family | Markers | Framing |
|---|---|---|
| Shape records | `0x00`–`0x0B`, `0x0F`, `0x16` | fixed record, optional counted array (12.4) |
| Page / document | `0x14`, `0x15` | fixed record + counted u16 array of ids |
| Document-level singletons | `0x1A`, `0x1C`, `0x1E`, `0x1F`, `0x23`, `0x26`, `0x28`, `0x29`, `0x2A`, `0x2B`, `0x2C`, `0x2D`, `0x2E`, `0x32`, `0x34`, `0x35`, `0x37`–`0x3B`, `0x3F` | fixed header + counted data (chapter 04) |
| Logo | `0x31`, `0x32` | fixed record + counted array (chapter 11) |
| Image | `0x21`, `0x22` | length-prefixed blob (12.5), chapter 08 |
| Palette | `0x47` | fixed 192-byte record (chapter 09) |
| 98-only | `0x40`, `0x41`, `0x43`, `0x45`, `0x4C`, `0x52` | fixed records (chapter 11 §11.5) |

## 12.4 The counted trailing array

Several records end with `count` elements appended after a fixed part. The count is
stored **twice, in two adjacent u16 slots**, and the array begins immediately after
the fixed part. This is exact — every size variant is explained, with no exceptions.

| Marker | Fixed part (base) | Count field | Duplicate | Element size | Fit |
|---|---|---|---|---|---|
| `0x0000` SHAPE | 102 | `u16@+0x5C` | `+0x5E` | 2 | 589/589 variants (p95+p97d) |
| `0x0014` PAGE (95/97) | 36 | `u16@+0x1A` | `+0x1C` | 2 | 2728/2740; the 12 misses are the P98 pages below |
| `0x0014` PAGE (98) | 40 | `u16@+0x1E` | `+0x20` | 2 | 12/12 |
| `0x0002` IMAGE | 126 | `u16@+0x74` | `+0x76` | 8 | 1005/1005 |
| `0x0003` | 126 | `u16@+0x74` | `+0x76` | 8 | 2616/2616 |
| `0x0031` LOGO | 30 | `u16@+0x08` | `+0x0A` | 8 | 1794/1794 |

The duplicate slot is a used/allocated pair: it is **equal to the count in every chunk of
`0x02`, `0x03`, `0x31` and in all 12 P98 pages** (the only records where equality was tested
chunk-by-chunk). A reader SHOULD accept either value but MUST validate the size equation against
the first slot. For `0x02`/`0x03` this rule alone explains every observed size — no second
optional region exists (the earlier concern about large LOGO records is void: a 446-byte LOGO has
count 52, and 30 + 8·52 = 446).

Worked example — `p97deluxe/x/PageWiz/AUDIOLBL.PUB`, SHAPE chunk id `0x0157`:
payload `…`, `u16@+0x5C = 2`, `u16@+0x5E = 2`, array at `+0x66` = `0x011F, 0x0133`,
chunk size 106 = 102 + 2·2. Both array values resolve to existing chunks in the
same document (types `0x00` and `0x03`), so the array holds **chunk ids**.

The **PAGE** array holds page/chunk ids in directory order (chapter 05 §5.3);
the **LOGO** array is decoded in chapter 11 §11.1.

**Rule for a reader.** Compute `n = u16@count_field`; require
`chunkSize == base + n*element_size`; if the equality fails, the chunk uses a
variant layout and MUST be reported, not truncated.

Markers whose size varies but which are **not** explained by this rule:
`0x01`, `0x0F`, `0x1A`, `0x1E`, `0x1F`, `0x23`, `0x26`, `0x28`, `0x29`, `0x2A`,
`0x2B`, `0x2C`, `0x32`, `0x34`, `0x37`, `0x3A`. Their variable part is string or
offset data, not a counted array; see chapters 04/05/11 and §12.7.

## 12.5 Length-prefixed blobs (`0x21`, `0x22`)

Exactly two markers use:

```
+0x00  u16  type_marker  0x0021 or 0x0022
+0x02  u16  stamp        0x0800 for both, in every observed chunk
+0x04  u32  length       == chunkSize - 8  (100 %)
+0x08  u8[length] body
```

| Marker | chunks | length condition | body |
|---|---|---|---|
| `0x0021` IMAGE_DATA | 527/527 | 100 % | WMF (`01 00 09 00 00 03`), chapter 08 |
| `0x0022` | 2134/2134 | 100 % | always 10 bytes: `4d 4f` (`MO`) + `u16` ordinal 0..9 + 6 zero bytes |

`0x0022` occurs 1..N times per document (356 files, 1272 in `p97deluxe/x`).
Its 10-byte body is constant apart from the ordinal, which is 0..9 in the corpus.
Semantics of the record: **[UNKNOWN]** — it lives in the document-globals group;
the reader can skip it safely by its length.

## 12.6 Record-size table

Counts are chunks; "mode" is the most frequent size; "files" is how many of the 484
documents contain the marker.

| Marker | chunks | files | min | mode | stamp | element rule |
|---|---|---|---|---|---|---|
| 0x0000 SHAPE | 5038 | 482 | 102 | 102 (4292) | 0x5C5E | +2·n @0x5C |
| 0x0001 | 737 | 484 | 106 | 106 (482) | 0x6060 | variant |
| 0x0002 IMAGE | 1007 | 484 | 126 | 126 (977) | 0x749C/0x74A4 | +8·n @0x74 |
| 0x0003 | 2618 | 484 | 126 | 126 (2553) | 0x749E/0x74A6 | +8·n @0x74 |
| 0x0004 LINE | 2776 | 484 | 59 | 59 (2774) | 0x3B3B | fixed |
| 0x0005 RECT | 4476 | 484 | 62 | 62 (4474) | 0x3E3E | fixed |
| 0x0006 | 4041 | 484 | 53 | 53 (4039) | 0x3539 | fixed |
| 0x0007 ELLIPSE | 1150 | 484 | 41 | 41 (1148) | 0x2929 | fixed |
| 0x0008 | 2 | 2 (p98) | 128 | 128 | 0x7688 | fixed |
| 0x0009 | 2 | 2 (p98) | 61 | 61 | 0x3535 | fixed |
| 0x000A | 2 | 2 (p98) | 126 | 126 | 0x747D | fixed |
| 0x000B | 2 | 2 (p98) | 86 | 86 | 0x4E4E | fixed |
| 0x000F GROUP | 2926 | 161 | 38 | 38 (1335) | 0x1818 | variant |
| 0x0014 PAGE | 2740 | 484 | 36 | 36 (1497) | 0x1A1A | +2·n @0x1A |
| 0x0015 DOCUMENT | 484 | 484 | 116/146/190 | 154 (216) | 0x6A78/0x889E/0xB2D2 | +2·(pages-1) |
| 0x0016 | 482 | 482 | 16 | 18 (353) | 0x121C | variant |
| 0x001A | 482 | 482 | 26 | 54 (83) | 0x0404 | variant |
| 0x001C | 482 | 482 | 26 | 34 (55) | 0x0404 | variant |
| 0x001E | 484 | 484 | 63 | 92 (11) | 0x0408 | variant (strings) |
| 0x001F | 484 | 484 | 16 | 26 (254) | 0x0404 | variant |
| 0x0021 IMAGE_DATA | 527 | 59 | 248 | — | 0x0800 | length-prefixed |
| 0x0022 | 2134 | 356 | 18 | 18 (2134) | 0x0800 | length-prefixed |
| 0x0023 | 484 | 484 | 28 | 50 (161) | 0x0404 | variant |
| 0x0026 | 482 | 482 | 35 | 51 (244) | 0x0404 | variant |
| 0x0027 | 22 | 22 | 42 | 42 | 0x1616 | fixed |
| 0x0028 | 484 | 484 | 56 | 56 (422) | 0x1010 | variant |
| 0x0029 | 484 | 484 | 149 | 205 (83) | 0x2C2C | variant |
| 0x002A | 482 | 482 | 16 | 26 (353) | 0x0404 | variant |
| 0x002B | 71 | 71 | 27 | 41 (15) | 0x0404 | variant |
| 0x002C | 529 | 484 | 40 | 58 (470) | 0x1818 | variant |
| 0x002D | 482 | 482 | 26 | 26 (480) | 0x0404 | fixed |
| 0x002E | 482 | 482 | 26 | 26 (482) | 0x0404 | fixed |
| 0x002F | 12 | 12 | 38 | 38 | 0x0808 | fixed |
| 0x0031 LOGO | 1794 | 484 | 30 | 30 (1742) | 0x0808 | +8·n @0x08 |
| 0x0032 | 1452 | 484 | 16 | 26 (1041) | 0x0404 | variant |
| 0x0034 | 331 | 331 | 172 | 256 (203) | 0x2424 | variant |
| 0x0035 | 306 | 306 | 200 | 200 (306) | 0xC8C8 | fixed |
| 0x0037 | 180 | 180 | 14 | 14 (126) | 0x0404 | variant |
| 0x0038 | 127 | 127 | 14 | 14 (127) | 0x0404 | fixed |
| 0x0039 | 484 | 484 | 48 | 48 (482) | 0x304C | fixed |
| 0x003A | 342 | 342 | 26 | 26 (330) | 0x0404 | variant |
| 0x003B | 12 | 12 | 26 | 26 | 0x0404 | fixed |
| 0x003F | 35 | 35 | 180 | 180 | 0xB4B4 | fixed |
| 0x0040 | 2 | 2 (p98) | 28 | 28 | 0x1C1C | fixed |
| 0x0041 | 2 | 2 (p98) | 40 | 40 | 0x1E1E | fixed |
| 0x0043 | 2 | 2 (p98) | 20 | 20 | 0x0A0A | fixed |
| 0x0045 | 2 | 2 (p98) | 8 | 8 | 0x0838 | fixed |
| 0x0047 PALETTE | 2 | 2 (p98) | 192 | 192 | 0x9696 | fixed (chapter 09) |
| 0x004C | 2 | 2 (p98) | 40 | 40 | 0x1212 | fixed |
| 0x0052 | 2 | 2 (p98) | 40 | 40 | 0x1212 | fixed |

## 12.7 Version-specific bases

The DOCUMENT record grows across generations; the rule
`size == base + 2·(page_count - 1)` holds exactly, so a reader can derive the page
count from the record size alone (verified: p95 128/128 at base 116, p97 105/106 at
base 146 — the single exception is a P95-format file inside the 97 corpus — p97d
248/248 at 146, p98 2/2 at base 190).

| Generation | document base | document stamp | shape-record base |
|---|---|---|---|
| 95 | 116 | 0x6A78 | 102 (0x00), 106 (0x01), 59 (0x04), 62 (0x05), 53 (0x06), 41 (0x07) |
| 97 | 146 | 0x889E | same |
| 98 | 190 | 0xB2D2 | +8: 114 (0x01), 67 (0x04), 70 (0x05), 61 (0x06), 49 (0x07) |

The shape-record growth is uniform (+8 bytes per shape for the simple primitives).
Where the extra bytes go is a chapter 06 question; the stamps record the same fact
independently.

## 12.8 The `{u8 id, u8 type}` block space is 2000+

libmspub's `MSPUBBlockID.h` / `MSPUBBlockType.h` and its base parser
(`MSPUBParser.cpp`, which also requires a `Quill/QuillSub/CONTENTS` stream) describe
a *different* container generation: a trailer that is itself a block tree
(`TRAILER_DIRECTORY = 0x90`, `GENERAL_CONTAINER = 0x88`, `STRING_CONTAINER = 0xC0`,
`DUMMY = 0x78`, `SHAPE_SEQNUM = 0x70`) and chunk payloads that are block lists.

That model is also the one that gives the chunk numbers `TABLE = 0x10`,
`CELLS = 0x63`, `FONT = 0x6C`, `BORDER_ART = 0x46`, `PALETTE = 0x5C`. Publisher 95-98
does not use those numbers: the palette is **`0x47`**, the document is `0x15`, the
page is `0x14`, and markers `0x10`, `0x46`, `0x5C`, `0x63`, `0x6C` do not occur in
any of the 484 corpus documents (chapters 09, 10, 11 record what the family uses
instead).

Consequence: this specification does **not** publish block-id rows for 95-98. The
2000+ block space is documented separately in `blocks/tlv-id-table.md` §B as a
pointer, with the explicit warning that it is a different format generation.

## 12.9 Parsing algorithm

```
parse_chunk(chunk):
    tm = u16(chunk, 0)
    if tm in {0x21, 0x22}:                 # length-prefixed blob
        n = u32(chunk, 4); body = chunk[8:8+n]
        assert 8+n == len(chunk)           # else: report, do not guess
    elif tm in COUNTED:                    # 0x00, 0x02, 0x03, 0x14, 0x31
        base, off, dup, elem = COUNTED[tm]
        n = u16(chunk, off)
        assert u16(chunk, dup) == n
        assert len(chunk) == base + n*elem
        items = [chunk[base+i*elem : base+(i+1)*elem] for i in range(n)]
    else:
        parse_fixed_record(tm, chunk)      # per-chapter layout
```

`COUNTED = {0x00:(102,0x5C,0x5E,2), 0x02:(126,0x74,0x76,8), 0x03:(126,0x74,0x76,8),
0x14:(36,0x1A,0x1C,2), 0x31:(30,0x08,0x0A,8)}`.

## 12.10 The 16-bit descriptor `(A, B)` — closed

The "stamp" is simply the two descriptor bytes at chunk `+0x02` (A) and `+0x03` (B), read as
a 16-bit value. Measured over all 493 documents: [OBSERVED]

| Behaviour | Markers | Count |
|---|---|---|
| `(A, B)` constant for the marker | 40 of 54 | all instances |
| `B` constant, `A` per-document (`0x0002`, `0x0003`) | 2 | 6 and 4 distinct `A` values |
| `(A, B)` changes only in Publisher 98 (record grew) | 5 | `0x0004` 59→67, `0x0005` 62→70, `0x0006` 57/53→65/61, `0x0007` 41→49, `0x000F` 24→32, `0x0014` 26→30 |

So there is no separate derivation to find: `B` is the writer-side fixed-part length descriptor
(chapter 06 §6.1) and `A` is a per-marker class byte, per-document only for the two record
families that carry a counted tail of 8-byte elements. For `0x0003` the four `A` values are
`0x8E`, `0x92`, `0x9A`, `0x9E`; for `0x0002` they are the same family. What selects `A` per
document is still `[UNKNOWN]` and is tracked in chapter 06 §6.9 — not here.

Closed by reference, no longer open in this chapter:

* `0x0022` body semantics — the 18-byte record is `"MO"` + object ordinal; see chapter 15 §15.8.
* Element content of the SHAPE and LOGO arrays — chapters 06 §6.4 and 11.7.

## 12.11 Rare markers `0x0036`, `0x004E`, `0x004F`, `0x0050`

These four markers occur only in the `.JSP` publications on the Publisher 98 CD
(`CHEKLIST.JSP`), with 1-4 instances each, so they are recorded here as measured
framing rather than as a completed layout. All four follow the same idiom as the
counted records of 12.4: a duplicated `u16` count in the header.

| Marker | Instances | Size | Header bytes (hex) | Duplicate count |
|---|---|---|---|---|
| `0x0036` | 4 (identical) | 112 | `36 00 70 70 00 00 00 00 …` | none observed |
| `0x004E` | 2 | 290 | `4E 00 0A 0A 00 00 00 00 00 06 00 06 00 2D 00 01 00 …` | `u16@+0x0A` == `u16@+0x0C` |
| `0x004F` | 2 | 306 / 207 | `4F 00 0A 0A 00 00 00 00 00 1A 00 1A 00 0B 00 … 50 53` | `u16@+0x0A` == `u16@+0x0C` |
| `0x0050` | 2 | 155 / 110 | `50 00 0A 0A 00 00 00 00 00 1B 00 1B 00 05 00 …` | `u16@+0x0A` == `u16@+0x0C` |

`[OBSERVED]` size, prologue bytes and the duplicate-count idiom. `[UNKNOWN]` the
element size and meaning of each array; the two records of `0x004E`/`0x004F`/
`0x0050` in that file differ only in the count and payload length, so a single
document with a controlled edit would settle each element size. Treatment: a
reader must preserve these records verbatim when rewriting a document.

`0x004F` ends with the ASCII bytes `50 53` ("PS") in the sampled file —
`[INFERENCE]` a marker for a PostScript/print descriptor record.
