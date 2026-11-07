# 08 — Images

Publisher stores pictures as **WMF metafiles embedded as child chunks**, not as
pictures in a stream. A document carries 527 image payloads across the corpus, and
every one of them is a Windows metafile. No BMP, JPEG, PNG, TIFF, PICT or EMF
payload occurs in any of the 493 documents. [OBSERVED]

## 8.1 Model

```
shape record (0x0002, 0x0003, 0x0027)
  └── directory child of type 0x0021 (IMAGE_DATA)
        +0x00  u16 0x0021      marker
        +0x02  u16 0x0800      constant
        +0x04  u32 size        payload length, == chunkSize - 8
        +0x08  ...             WMF metafile, verbatim
```

The parent link in the directory is the image's owner: `0x0021` chunks are children of
`0x0002` (505) or `0x0027` (22) — `0x0027` is the *picture object* that names the source
`.wmf` file, see §8.4. A shape owns zero or one `0x0021` child in the corpus,
and a shape with zero children is an image-shaped frame with no picture. [OBSERVED]

The payload is the metafile **without** any additional wrapper: it can be written to a
`.wmf` file directly. `[OBSERVED]` 527/527 start with `01 00 09 00 00 03` — METAHEADER
type 1 (memory metafile), header size 9 words, version `0x0300`.

Carving was smoke-tested on `p95/x/PAGEWIZ/MODERN.PUB`: 25 payloads extracted; each begins
with a valid METAHEADER. `2·mtSize` equals the payload length in **282/527** chunks; the
remaining 245 carry an even overhang of 2…14 bytes after `META_EOF` (padding, not a record).
A record walk from `+0x12` lands exactly on `2·mtSize` and ends on `META_EOF` (`0x0000`) in
**527/527**. That is the acceptance proof that the payload contains no wrapper and no
prefix — and the reason a reader must cut at `2·mtSize`, not at the length prefix.

## 8.2 `0x0021` IMAGE_DATA

| Offset | Width | Field | Observed |
|---|---|---|---|
| 0x00 | u16 | marker | `0x0021` |
| 0x02 | u16 | class | `0x0800` in 527/527 |
| 0x04 | u32 | payload size | equals `chunkSize − 8` in **527/527** |
| 0x08 | bytes | WMF metafile | starts `01 00 09 00 00 03` |

Payload sizes range from 240 bytes to 132 880 bytes (median 3 844). [OBSERVED]

## 8.3 Image-bearing shape records

`0x0002` (IMAGE) and `0x0003` (SHAPE3) share the shape framing of chapter 06: rotation at
`+0x04`, geometry at `+0x06`, and a counted array whose count sits at `+B` where `B` is the
fixed-part length byte at `+0x03` (chapter 12 §12.4). The array is a **freeform outline
polygon in shape-local EMU**, not an image list: the vertices start at `(0,0)` — the
bounding-box top-left — and their extent equals the box size. Verified on all 91 chunks that
have a non-empty array: `min(x) = min(y) = 0` in 91/91 and `max = (x1−x0, y1−y0)` within
±3 EMU in 90/91 (the single exception, `p97deluxe/x/BANKBROC.PUB` id `0x0148`, overshoots by
211 kEMU — a writer bug). A shape with `count = 0` is a plain rectangle and still owns its
`0x0021` child (477 of the 505 image owners are rectangles). [OBSERVED]

Worked example — `p95/x/PAGEWIZ/PLAIN_CD.PUB`, `0x0002` id `0x02C1`, 222 bytes, count 12:

```
bbox = (65977, 156656) … (799010, 747104)        = (0.072, 0.171) … (0.874, 0.817) in
vertices (local EMU):
  (496972,      0)  (173940, 176305)  ( 74546, 244552)  (     0, 324172)
  (     0, 426543)  (186365, 551662)  (285759, 591473)  (360305, 591473)
  (695761, 392419)  (733034, 187679)  (708185,  85309)  (658488,      0)
```

First and last vertices both lie on `y = 0`, so the outline is closed. A reader that draws
the bounding box instead of the polygon draws the wrong silhouette for these 91 shapes.

| Marker | Base (95/97) | Base (98) | Array |
|---|---|---|---|
| `0x0002` | 126 | 150 | count at `+0x74` (98: `+0x8C`), duplicate `+0x76` (`+0x8E`), elements from `+0x7E` (`+0x96`) |
| `0x0003` | 126 | 150 | same |
| `0x0039` | 48 | 56 | — |

The 10 bytes between the last fixed field and the array are a fixed trailer
`{u16 count, u16 count, u32 8, u16 0}`; that is why the array starts 10 bytes after `B`.
`chunkSize == B + 10 + 8·count` holds for all 1010 `0x0002` and all 2621 `0x0003` chunks.

Publisher 98 grows these records by 24 bytes (`0x0002`/`0x0003`) and 8 bytes (`0x0039`);
the geometry fields keep their offsets.

## 8.4 The 18-byte `0x0022` record

`0x0022` is **not** an image record: it is the embedded-object reference
(`"MO"` + object ordinal). See chapter 15 §15.8. It is mentioned here because it shares
the `u32@+4 == size−8` framing with `0x0021` and is often mistaken for image data.

Measured parent census: all 2 134 instances are children of a `0x0003` shape
(2 134/2 134), so the record is per-shape — the shape that displays the object carries the
link. The discriminator against a real image is the body: `4d 4f` (`"MO"`) versus
`01 00 09 00`. [OBSERVED]

## 8.4.1 Picture object `0x0027`

The second image path: a record that names the source metafile and owns the bytes as a
child. 22 instances, 22/22 with a `0x0021` child.

```
+0x00  u16  0x0027
+0x02  u16  0x1616          stamp (fixed-part length B = 0x16)
+0x04  u16  imageDataId     id of the 0x21 child  (22/22)
+0x06  u32  0xFFFFFFFF
+0x0A  s32  top             top edge of the WMF outer window, twips (22/22)
+0x0E  s32  right           right edge of the WMF outer window, twips (22/22)
+0x12  s32  bottom          bottom edge of the WMF outer window, twips (22/22)
+0x16  u32  nameLen
+0x1A  u32  nameLen         duplicate
+0x1E  char[nameLen] name   ASCII, NUL-terminated
```

The three `s32` at `+0x0A`/`+0x0E`/`+0x12` are the cached source window of the
owned metafile: with `(Y0, X0)` the first `META_SETWINDOWORG` (`0x020B`)
parameters and `(H, W)` the first `META_SETWINDOWEXT` (`0x020C`) parameters of
the `0x0021` payload, the triple is `(Y0, X0 + W, Y0 + H)` — the top, right and
bottom edges of the outer window in twips (the metafiles are authored at
1440 units/in, so window units are twips). Verified 22/22 over every `0x0027`
instance in `p95/x`, `p97/x` and `p97deluxe/x` (`p98/x` has none). The only
edge not cached is the left (`X0`, always 0 or −1); it is recovered from the
metafile itself at render time. Units are twips, not EMU: full-page pictures
reproduce letter dimensions exactly (`(0, 15840, 12240)` = 11 × 8.5 in
landscape; `(0, 12247, 15850)` portrait), and border tiles measure
≈ 0.4 × 0.6 in, matching their artwork.

The former "`+0x12` flag, 0 or 1" reading was a mis-split of the worked
example: `+0x12` is the bottom edge, an `s32` coordinate whose domain spans
−1 … 15850. Border tiles anchor their window at negative origins so the
tile's bottom-right corner lands at the page edge (e.g. `pdir62p.wmf`:
`(−793, 613, −1)` = window `(−1, −793)–(613, −1)`), which is why small values
cluster at −1/0/1 while full-page pictures carry page heights. [OBSERVED]

Purpose: the record is the shared gallery/border resource. All 22 instances
are children of the DOCUMENT chunk (`0x0015`), each owns exactly one `0x0021`
child (the `+0x04` id resolves to a `0x0021` chunk 22/22), and the name is the
gallery id (`pdir*.wmf`, 15 distinct names), not a filesystem path: no `pdir`
or `.wmf` literal occurs in any shipped `MSPUB.EXE`. `PICSTORE.DLL`
(`p95/x/SHARED/ARTGALRY/`, also shipped under `p97`/`p97deluxe`/`p98`) exports
the `Add/Get/SetPictureRef` runtime for those ids, but no binary in the
corpus maps a `pdir` name to file bytes — the mapping lives in the gallery
(`ARTGALRY.EXE` imports `GetPictureRef`); a reader resolves the picture
through the `0x0021` child and uses the cached triple for placement without
re-parsing the metafile. [OBSERVED for the linkage and the corpus identity;
INFERENCE for the placement-cache use]

`chunkSize == 0x1E + nameLen` in 22/22. All 22 names end in `.wmf` (`pdir62p.wmf`,
`pdir71p.wmf`, `pdir47l.wmf`, …) — the writer's internal name for the imported metafile,
not a filesystem path. Example, `p95/x/BRBLLOON.PUB` id `0x0134`:

```
27 00 16 16 2d 01 ff ff ff ff e7 fc ff ff 65 02 00 00
ff ff ff ff 0c 00 00 00 0c 00 00 00  "pdir62p.wmf\0"
       ^0x04 = 0x012D = the 0x21 child      ^len 12, twice
```

## 8.5 Extraction algorithm

For every `0x0021` chunk in the document:

1. Read `u32` at `+0x04`; require it equals `chunkSize − 8`.
2. The image is exactly `chunk[8 : 8 + size]`.
3. Resolve the owner by `parentId`; attach the image to that shape.
4. Write the bytes as a `.wmf` file; no transcoding is required.

Recurse into `Objects/Object N/Contents` first if the document has embedded objects
(chapter 15) — nested documents carry their own shapes and images.

## 8.6 Validation

| Check | Result |
|---|---|
| `u32@+4 == chunkSize − 8` | 527/527 |
| payload starts with a WMF signature | 527/527 |

Both are enforced by `tools/validate.py` (`image_data_length_prefix`, `image_data_wmf`).

## 8.7 Open

* Whether non-WMF payloads are possible: none occur in the corpus, and the binary's
  graphics-import filters (`SHARED/GRPHFLT/*.DLL`: BMP, JPEG, PCX, TIFF, PCD) convert to
  WMF on import, which is consistent with "always WMF". `[INFERENCE]`
* `0x0039` is a 48-byte (56 in 98) document-level record with no image children — the
  earlier suggestion that it is image-bearing was based on a misread marker (`39` decimal
  = `0x27`). Its framing is documented in chapter 11 §11.1 and it is **proven opaque**: the
  48-byte record is carried through the chunk copy untouched and no shipped binary reads it
  (scan: `MSPUB.EXE` 95/97/98, `QS98.DLL`, `PUBOLE32.DLL`), so a reader preserves it verbatim.
* `0x0027` triple closed in §8.4.1: cached WMF outer-window edges (top, right,
  bottom) in twips, 22/22; `+0x12` is the bottom edge, not a flag.

Closed since the previous revision: the Publisher 98 24-byte growth; see §8.7.1.

### 8.7.1 The Publisher 98 24-byte growth — located, not decoded

The counted tail of `0x0002`/`0x0003` starts at the record's `B` byte in **both**
generations, so the growth is entirely inside the fixed part: `size == B + 10 + 8·N` with
`B = 116`, `N` at `+0x74` (95/97) and `B = 140`, `N` at `+0x8C` (98) — 3 643/3 643 chunks
over the four corpora. [OBSERVED]

The 24 bytes split into two insertions, each measured against a field that kept its
meaning:

| Insertion | Evidence | Where it lands in 98 |
|---|---|---|
| 8 bytes | e.g. `p95/x/PAGEWIZ/PLAIN_CD.PUB` id `0x0188` and `p97/x/MSPUB.PUB` id `0x011A` carry the `FE FF` word at `+0x29`, the P98 records at `+0x31`; the `u32 0xFFFFFFFF` sits at `+0x70` (95/97) and `+0x78` (98) | somewhere before `+0x29` — the 8-byte insertion chapter 06 §6.3 localises for the simple primitives (`00 E4 C0 07 00 E4 C0 00 00` over `+0x21…+0x29`), which is where the P98 `0x0002` records carry the same run |
| 16 bytes | the count header moves `+0x74` → `+0x8C` while the sentinel moved only `+0x78` | a 16-byte block at `+0x7C…+0x8B`, between the sentinel and the count header |

All ten P98 `0x0002`/`0x0003` instances (one of each per publication, all in the gallery
page) are zero at `+0x7C…+0x8B` and carry the sentinel at `+0x78` (10/10), and the five
payloads of each marker are byte-identical, so the *content* of the 16-byte block is not
exercised anywhere on the CD. `[OBSERVED for the position and the zero fill; UNKNOWN for
the fields]`

What the 24 bytes provably are **not**: not a longer trailing array (the array still
starts at `B + 10` with 8-byte elements, 10/10), not a second counted list (no count pair
appears in `+0x7C…+0x8B`), and not an append — the sentinel that 95/97 places at `+0x70`
already sits 8 bytes later at `+0x78`, so the growth is inserted before it and the fixed
part is shifted, not extended. `[OBSERVED for the shift; UNKNOWN for which field each of
the two insertions belongs to]`

The P98 record reader that would name the fields was not isolated in
`notes/p98/decomp98`: the `+0x8C`/`+0x96`/`B`-based hits there are runtime-struct offsets,
and no function was found that indexes a chunk buffer by the record's `B` byte. The
remaining blocking fact is the meaning of the 16-byte block at `+0x7C…+0x8B`; the one
experiment that settles it is a P98 document with a non-gallery picture on a page (the
five gallery records are all-zero in that range).
