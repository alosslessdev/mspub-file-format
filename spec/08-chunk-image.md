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
+0x0A  s32  dx              [UNKNOWN] unit
+0x0E  s32  dy              [UNKNOWN] unit
+0x12  u32  0 or 1          [UNKNOWN]
+0x16  u32  nameLen
+0x1A  u32  nameLen         duplicate
+0x1E  char[nameLen] name   ASCII, NUL-terminated
```

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
* `0x0039` is image-bearing but only 48/56 bytes long — it looks like a shape that
  *references* a picture rather than owning geometry; its role is `[UNKNOWN]`.
* The 24 bytes added to the Publisher 98 `0x0002`/`0x0003` fixed part — `[UNKNOWN]`. The
  five P98 publications carry one gallery instance each and all five payloads are
  byte-identical, so there is no differential. Landmarks: the `0xFFFFFFFF` word at `+0x70`
  (95/97) sits at `+0x78` in 98, and the count fields moved from `+0x74` to `+0x8C`.
* `0x0027` `+0x0A`/`+0x0E` (`dx`, `dy`) units — `[UNKNOWN]`; the values (−793, +613) are far
  too small to be EMU and may be a crop offset in metafile units.
