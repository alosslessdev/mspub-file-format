# 08 — Images

Publisher stores pictures as **WMF metafiles embedded as child chunks**, not as
pictures in a stream. A document carries 527 image payloads across the corpus, and
every one of them is a Windows metafile. No BMP, JPEG, PNG, TIFF, PICT or EMF
payload occurs in any of the 493 documents. [OBSERVED]

## 8.1 Model

```
shape record (0x0002, 0x0003, 0x0039)
  └── directory child of type 0x0021 (IMAGE_DATA)
        +0x00  u16 0x0021      marker
        +0x02  u16 0x0800      constant
        +0x04  u32 size        payload length, == chunkSize - 8
        +0x08  ...             WMF metafile, verbatim
```

The parent link in the directory is the image's owner: `0x0021` chunks are children of
`0x0002` (505) or `0x0039` (22). A shape owns zero or one `0x0021` child in the corpus,
and a shape with zero children is an image-shaped frame with no picture. [OBSERVED]

The payload is the metafile **without** any additional wrapper: it can be written to a
`.wmf` file directly. `[OBSERVED]` 527/527 start with `01 00 09 00 00 03` — METAHEADER
type 1 (memory metafile), header size 9 words, version `0x0300`.

Carving was smoke-tested on `p95/x/PAGEWIZ/MODERN.PUB`: 25 payloads extracted; each begins
with a valid METAHEADER whose `mtSize` field (in 16-bit words) equals half the carved file
length — e.g. a 1 360-byte payload declares 680 words. That is the acceptance proof that
the payload contains no wrapper, no prefix and no trailing padding.

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
`+0x04`, geometry at `+0x06`, and a counted array header at `+0x74`/`+0x76` with 8-byte
elements from `+0x78` (Publisher 95/97). The array is **not** the image list — a shape
whose array count is 0 still owns an `0x0021` child — it is a per-image placement array
used by multi-image shapes. `[OBSERVED]` for the framing, `[UNKNOWN]` for the element
fields.

| Marker | Base (95/97) | Base (98) | Array |
|---|---|---|---|
| `0x0002` | 126 | 150 | count at `+0x74`, duplicate at `+0x76`, 8-byte elements at `+0x78` |
| `0x0003` | 126 | 150 | same |
| `0x0039` | 48 | 56 | — |

Publisher 98 grows these records by 24 bytes (`0x0002`/`0x0003`) and 8 bytes (`0x0039`);
the geometry fields keep their offsets.

## 8.4 The 18-byte `0x0022` record

`0x0022` is **not** an image record: it is the embedded-object reference
(`"MO"` + object ordinal). See chapter 15 §15.8. It is mentioned here because it shares
the `u32@+4 == size−8` framing with `0x0021` and is often mistaken for image data.

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

* Element layout of the `+0x78` placement array (8-byte elements) — `[UNKNOWN]`; the
  discriminating experiment is a shape with two pictures on one frame.
* Whether non-WMF payloads are possible: none occur in the corpus, and the binary's
  graphics-import filters (`SHARED/GRPHFLT/*.DLL`: BMP, JPEG, PCX, TIFF, PCD) convert to
  WMF on import, which is consistent with "always WMF". `[INFERENCE]`
* `0x0039` is image-bearing but only 48/56 bytes long — it looks like a shape that
  *references* a picture rather than owning geometry; its role is `[UNKNOWN]`.
