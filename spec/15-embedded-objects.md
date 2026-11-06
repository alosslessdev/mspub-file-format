# 15 — Embedded objects (`Objects/Object N`)

A Publisher document can carry OLE objects — WordArt, clip-art gallery items,
Word/Paint documents, or packaged files. Each one is a CFB **storage**
`Objects/Object N`, self-similar to the document itself, holding its own
`Contents` stream plus the OLE1 presentation streams.

Census over the 493-document corpus: 2 162 object storages in 356 files. The
Publisher 98 publications contain none.

## 15.1 Object storage anatomy

`Objects` is a pure container storage with no streams of its own (356/356).
`N` is a per-document object number, not dense (gaps occur). [OBSERVED]

| Stream | Instances | Size range | Meaning |
|---|---|---|---|
| `\x02OlePres000` | 2 162 (all objects) | 40 – 148 880 | mandatory preview; WMF metafile + descriptor |
| `\x01CompObj` | 2 045 | 72 – 120 | OLE1 class descriptor (ProgID, clipboard format) |
| `\x01Ole` | 1 556 | 20 | OLE stream header |
| `Contents` | 1 241 | 95 – 148 832 | the **embedded server's own document** (WordArt / packaged file), NOT a Publisher document — see §15.9 |
| `\x03Internal` | 1 239 | 12 – 16 | Publisher-private state |
| `\x01Ole10Native` | 921 | 652 – 15 844 | packaged (non-OLE) file payload |
| `\x02OlePres001` | 407 | 280 – 49 286 | print-setup record (DEVMODE/DEVNAMES) |
| `\x01Ole10ItemName` | 2 | 5 | packaged-file item name |

Stream-set combinations (object granularity, 2 162 objects):

| Objects | Streams |
|---|---|
| 885 | CompObj, Ole, OlePres000, Internal, Contents |
| 606 | CompObj, Ole10Native, OlePres000 |
| 354 | CompObj, Ole, OlePres000, OlePres001, Internal, Contents |
| 149 | CompObj, Ole, Ole10Native, OlePres000 |
| 115 | Ole, Ole10Native, OlePres000 (no CompObj) |
| 49 | CompObj, Ole, Ole10Native, OlePres000, OlePres001 |
| 2 | Ole, OlePres000, OlePres001, Contents |
| 2 | CompObj, Ole, Ole10ItemName, Ole10Native, OlePres000, OlePres001 |

Two structural consequences, both verified 2 162/2 162: `\x03Internal` and the
nested `Contents` always occur together, and no object carries both
`\x03Internal` and `\x01Ole10Native`. An object is therefore either a
**nested Publisher document** or a **packaged file**, or a bare OLE class shell.
[OBSERVED]

## 15.2 `\x01CompObj` — OLE1 class descriptor

The layout is the OLE1 `CompObj` record. 2 045/2 045 streams parse with no residual
bytes beyond the documented tail.

| Offset | Width | Field | Observed |
|---|---|---|---|
| 0x00 | 4 | reserved1 | `0xFFFE0001` (2 045/2 045) |
| 0x04 | 4 | version | `0x00000A03` |
| 0x08 | 4 | reserved2 | `0xFFFFFFFF` |
| 0x0C | 16 | class block | 4 distinct values, one per ProgID (below) |
| 0x1C | u32 | `cbAnsiUserType` | includes the NUL: 0, 4, 8, 22, 28 |
| … | bytes | AnsiUserType | e.g. `"Microsoft ClipArt Gallery"` |
| … | u32 | `cbAnsiClipboardFormat` | includes the NUL: 0, 8, 12, 16 |
| … | bytes | AnsiClipboardFormat | e.g. `"MS_ClipArt_Gallery"` |
| … | u32 | `cbAnsiProgID` | includes the NUL: 7, 12, 14, 20 |
| … | bytes | AnsiProgID | e.g. `"MSWordArt.2"` |
| … | 16 or 24 | tail | always begins `F4 39 B2 71` |

Strings are length-prefixed **including** the terminating NUL. Two tail variants
exist: 16 bytes (`F4 39 B2 71` + 12 zeros, 1 074 streams) and 24 bytes
(`F4 39 B2 71`, `u32 8`, a varying u32, a u32 that is always 96 or 136, 8 zeros;
971 streams, all WordArt). Tail semantics `[UNKNOWN]`. [OBSERVED]

Class table (whole corpus):

| AnsiUserType | ClipboardFormat | ProgID | class block @0x0C | size |
|---|---|---|---|---|
| — | — | `MSWordArt.2` | `f0120200 00000000 c0000000 00000046` | 76 |
| `Microsoft ClipArt Gallery` | `MS_ClipArt_Gallery` | `MS_ClipArt_Gallery` | `26000300 00000000 c0000000 00000046` | 120 |

The document's own root `\x01CompObj` uses the same record shape with the
Publisher class (chapter 01 §1.4).

## 15.3 `\x01Ole` — 20 bytes, constant

`01 00 00 02` followed by 16 zero bytes, byte-identical in all 1 556 instances.
Field names follow MS-OLEDS (version, flags, link-update option, reserved,
moniker size); the moniker size is 0, i.e. every object is **embedded, never
linked**. [OBSERVED]

## 15.4 `\x03Internal`

Six `u16` fields, two shapes, plus optional trailing zeros:

| Variant | Bytes | Fields |
|---|---|---|
| A12 | 12 | `00 00 01 00 00 00 01 00 00 00 00 00` |
| A16 | 16 | A12 + 4 zero bytes |
| C16 | 16 | `00 00 01 00 00 00 00 00 01 00 00 00 00 00 00 00` |

As `u32` groups the record is `[0x00010000, x, y]` with exactly one of `x`, `y`
equal to 1 (A: x=1; C: y=1). The choice correlates with nothing measured
(object number, class, sizes, owner) — `[UNKNOWN]`. [OBSERVED]

The document-level `\x03Internal` is 12 bytes in all documents with the same
`00 00 01 00 00 00` prefix followed by a `u16` in 0…181; also `[UNKNOWN]`.

## 15.5 `\x02OlePres000` — preview metafile

```
+0x00  u32 0xFFFFFFFF
+0x04  u32 3                format id, constant in all 2570 presentation streams
+0x08  u32 4                record kind (8 exceptions are print records)
+0x0C  u32 1
+0x10  u32 0xFFFFFFFF
+0x14  u32 2 | 32 | 16      picture-type field, unidentified
+0x18  u32 0
+0x1C  u32 width            HIMETRIC (0.01 mm)
+0x20  u32 height           HIMETRIC
+0x24  u32 cbWmf            == len(stream) - 40 in 2135/2162
+0x28  ...  WMF metafile    starts 01 00 09 00 00 03 (memory metafile, v0x0300)
```

2 135 of 2 162 streams carry an exact WMF at `+0x28`; 18 carry the WMF plus
trailing bytes; 8 are print records; one is an empty 40-byte descriptor. No DIB
or bitmap payload occurs anywhere in `OlePres000`. [OBSERVED]

## 15.6 `\x02OlePres001` — print setup

Same 8-byte prologue, then a `DEVNAMES`-style record: `cbDevNames` at `+0x08`,
string offsets at `+0x0C`/`+0x0E` (relative to `+0x08`), driver and device
strings, `[INFERENCE]` from the offsets and the string content, `[OBSERVED]` for
the byte layout. It appears only in objects that also have `OlePres000`.

## 15.7 `\x01Ole10Native` — packaged file

Two framings occur; both are verified byte-exactly on all 921 instances.

| Group | Count | Framing |
|---|---|---|
| A | 55 | classic OLE1 `Ole10Native` header: `u32 totalSize`, `u16 flags`, `u16 length` + label, `u16 length` + file name, `u16` type, `u32 dataSize`, data |
| B | 866 | Publisher variant: `u32 totalSize`, then the file name as a length-prefixed ANSI string, `u32 dataSize`, data |

`[OBSERVED]` — a reader must try both framings and pick the one whose sizes are
self-consistent; a re-implementer should write group B for new documents if it
must choose one, since it dominates the corpus.

## 15.8 Linkage: how the document body refers to an object

**The link is the `u16` ordinal at `+0x0A` of a `0x0022` record.** No other
mechanism survived testing. [OBSERVED]

`0x0022` is a fixed 18-byte record (2 134 instances, always exactly 18 bytes):

```
+0x00  u16 0x0022   marker
+0x02  u16 0x0800
+0x04  u32 10       always size - 8
+0x08  u16 "MO"     4D 4F
+0x0A  u16 N        object number -> Objects/Object N
+0x0C  3 bytes 0
+0x0F  u8  0x00 (1201) or 0x80 (933)   per-reference state, see 15.8.1
+0x10  u16 0
```

Verified on `p97/x/AUDIOLBL.PUB`: `Contents+0x15E5` (file offset `0x29E5`) is
`22 00 00 08 0A 00 00 00 4D 4F 01 00 00 00 00 00 00 00`, and the file contains
exactly one object, `Object 1`.

Negative results: class names/ProgIDs never appear in `Contents`; the object
number is not stored in the shape record; there is no OLE moniker anywhere. So a
reader resolves an embedded object only through `0x0022` and the storage name.

## 15.9 Recursion requirement

`Objects/Object N/Contents` is **not** a Publisher document. All 1 241 such streams in
the 493-document corpus were checked and none begins with the `0xACE8` magic:

| First bytes | Streams | Meaning |
|---|---|---|
| `57 6f 72 64 41 72 74 20` (`"WordArt "`) | 1 239 | WordArt 2.0 document |
| `78 56 34 12 4c 45 02 00` | 2 | packaged little-endian binary |

Sizes range from 95 to 148 832 bytes. A Publisher reader must therefore treat this
stream as **opaque** and attach it to the object for the owning server; recursing into it
with the Publisher parser is wrong. (An earlier revision of this chapter asserted the
opposite; the assumption was never measured and the measurement refutes it.) [OBSERVED]

Nesting depth is one level in every file (no `Objects` inside an `Object N`); nothing in the
format forbids deeper nesting. `[OBSERVED for depth; INFERENCE for the general case]`

### 15.8.1 The `+0x0F` flag

Domain `{0x00, 0x80}` (1 201 / 933 over 2 134 references). Tested against every object property
available and **no correlation holds**:

| Hypothesis | Result |
|---|---|
| object class / ProgID | rejected — `MSWordArt.2` occurs 644× with `0x00` and 573× with `0x80` |
| packaged (`Ole10Native`) vs nested document | rejected — both kinds occur under both values |
| owner shape marker | rejected — every `0x0022` parent is a `0x0003` shape, both values occur |
| `CompObj` length (class variant) | rejected — all four lengths occur under both values |
| preview size (icon vs content) | rejected — `>2k` previews occur 1 145× at `0x00` and 409× at `0x80` |

So it is a per-reference state, not a class discriminator. `[OBSERVED]` The two readings still
consistent with the data are "object needs updating" and "display as icon"; the discriminating
experiment is to save one document twice, once with an object inserted as an icon and once as
content, and diff the byte. A reader must preserve it.

## 15.10 Open

* `0x0022` `+0x0F` flag — domain and negative correlations published in §15.8.1; the two
  candidate readings are still undistinguished.
* `\x03Internal` `x`/`y` bit — variant A/C splits by nothing measured (class, size, owner,
  ordinal). Two readings remain: a saved-state flag or an allocation lane.
* `OlePres000 +0x14` (2 / 32 / 16) — measured against the `0x0022` flag and object class with no
  correlation; `[UNKNOWN]` picture-type field.
