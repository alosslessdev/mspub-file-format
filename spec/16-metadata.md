# 16 — Metadata

Publisher 95 writes very little metadata. There is no title/author/subject/created-date property
set: the only standard metadata stream is `\x05SummaryInformation`, and it carries one property,
a thumbnail. Everything else that describes the document lives either in the CFB directory
(container chapter) or in the `Contents` header and the singleton chunks (chapters 02–04).

## 16.1 Stream census

| Stream | Files with it | Notes |
|---|---|---|
| `\x01CompObj` | 128/128 | OLE class descriptor, §16.2 |
| `\x03Internal` | 128/128 | Publisher-private, §16.3 |
| `\x05SummaryInformation` | 127/128 | absent in `p95/x/MSPUB.PUB`; §16.4 |
| `\x05DocumentSummaryInformation` | 0/128 | never written by Publisher 95 |
| `Quill`, `Escher` | 0/128 | Publisher 97/98 only |

[OBSERVED]

## 16.2 `\x01CompObj`

Three serialisation lengths occur; all share the same leading fields, and the shorter variants
simply omit trailing reserved words.

| Length | Files | AnsiUserType |
|---|---|---|
| 70 | 12 | `"Microsoft Publisher"` (20 bytes incl. NUL) |
| 78 | 106 | `"Microsoft Publisher 2.0"` (24 bytes) + one trailing zero dword |
| 94 | 10 | `"Microsoft Publisher 2.0"` + trailing zero dword + Unicode marker + 12 zero bytes |

[OBSERVED] Files at 94 bytes: `MSPUB.PUB`, `BIZTRIP.PUB`, `CLASSIC.PUB`, `CLASS_CD.PUB`,
`JAZZY.PUB`, `JAZZY_CD.PUB`, `MODERN.PUB`, `MODRN_CD.PUB`, `PLAIN.PUB`, `PLAIN_CD.PUB`.
Files at 70 bytes: `BMEMO1.PUB`, `BMEMO2.PUB`, `BRCATALG.PUB`, `CATALOG.PUB`, `CHGADDR.PUB`,
`CLINEAR.PUB`, `ELINEAR.PUB`, `GRAPHCNW.PUB`, `PMEMO1.PUB`, `PMEMO2.PUB`, `POSTER.PUB`,
`VLINEAR.PUB`. The remaining 106 use 78 bytes.

The choice is **not** the `Contents` `+0x06` stamp: only `MSPUB.PUB` and `BIZTRIP.PUB` are in both
the 94-byte group and the `0x3303` group. The correlation that does hold is design lineage — the
94-byte group is exactly the "designer style" templates (`PLAIN`, `CLASSIC`, `MODERN`, `JAZZY`
and their `_CD` variants) plus the shipped blank document. [OBSERVED for the sets; INFERENCE for
"producing build/template lineage"]

### Layout (94-byte form, `p95/x/MSPUB.PUB`)

| Offset | Width | Field | Value |
|---|---|---|---|
| 0x00 | u32 | `Reserved1` | `0xFFFE0001` |
| 0x04 | u32 | `Version` | `0x00000A03` (Win32 CompObj) |
| 0x08 | u32 | `Reserved2` | `0xFFFFFFFF` |
| 0x0C | 16 | `Clsid` | `{00021200-0000-0000-C000-000000000046}` |
| 0x1C | u32 | `AnsiUserTypeLen` | 24 |
| 0x20 | 24 | `AnsiUserType` | `"Microsoft Publisher 2.0\0"` |
| 0x38 | u32 | `AnsiClipboardFormatLen` | 14 |
| 0x3C | 14 | `AnsiClipboardFormat` | `"MSPublisher.2\0"` |
| 0x4A | u32 | `Reserved3` | 0 |
| 0x4E | u32 | `UnicodeMarker` | `0x71B239F4` |
| 0x52 | 12 | padding | 0 |

78-byte form: identical through offset 0x4A (total 78). 70-byte form: `AnsiUserType` is the
20-byte `"Microsoft Publisher\0"`, clipboard format identical, and the stream ends at 70 — no
`Reserved3`, no Unicode marker. [OBSERVED]

### CLSID variants

| CLSID | Files |
|---|---|
| `{00021200-0000-0000-C000-000000000046}` | 127 |
| `{00021201-0000-0000-C000-000000000046}` | 1 — `p95/x/PAGEWIZ/BIZTRIP.PUB` |

[OBSERVED] The differing dword is the first (`00021200` → `00021201`), i.e. the CLSID is
versioned in its low word. A reader that dispatches on the CLSID must accept both.

## 16.3 `\x03Internal`

12 or 16 bytes, Publisher-private, read as `u16, u16, u32, u32`:

| Variant | Bytes | Files |
|---|---|---|
| 12-byte | `00 00 01 00 00 00 00 00 00 00 00 00` | 50 |
| 12-byte | `00 00 01 00 00 00 05 00 00 00 00 00` | 10 (word 2 = 5) |
| 12-byte | word 2 = 3 / 4 / 2 | 10 / 9 / 7 |
| 16-byte | `00 00 01 00 00 00 01 00 00 00 00 00 00 00 00 00` | 116 |

[OBSERVED] Fields 0 (`0x0000`) and 1 (`0x0001`) are invariant; the third u32 takes 0…5.
Semantics [UNKNOWN] — the discriminating experiment is to edit and re-save a document and see
which word moves.

## 16.4 `\x05SummaryInformation`

Present in 127 files, absent in `p95/x/MSPUB.PUB`. Four of the 127 are **zero-length**
(`CLASS_CD.PUB`, `JAZZY_CD.PUB`, `MODRN_CD.PUB`, `PLAIN_CD.PUB`), so 123 files carry an actual
property set. [OBSERVED]

### Stream header

```
0x00 u16  ByteOrder        0xFFFE
0x02 u16  Version          0
0x04 u32  SystemIdentifier 0x0A03 (0x0004 in 4 files)
0x08 16   CLSID            all zero
0x18 u32  NumPropertySets  1
0x1C 16   FMTID            F29F85E0-4FF9-1068-AB91-08002B27B3D9 (SummaryInformation)
0x2C u32  SectionOffset    0x30 (48) in 119 files, 0xBC (188) in 4
```

[OBSERVED] The section offset varies, so it must be read, not assumed.

### Section

```
SectionOffset + 0  u32  SectionSize
SectionOffset + 4  u32  NumProperties   (= 1 in all 123)
SectionOffset + 8  u32  PID             (= 0x11, PIDSI_THUMBNAIL)
SectionOffset + 12 u32  ValueOffset     (relative to SectionOffset)
```

At `SectionOffset + ValueOffset`: `u32 VT` = `0x47` (`VT_CF`), `u32 Size`, then
`0xFFFFFFFF`, `u32` payload size, then the payload (the thumbnail metafile). The leading
`0xFFFFFFFF` is present in 123/123 property values. [OBSERVED]

**Publisher 95 writes no other summary property.** There is no `PIDSI_TITLE` (0x02),
`PIDSI_AUTHOR` (0x04), `PIDSI_CREATE_DTM` (0x0C) or any other PID in the corpus — the whole
stream is the thumbnail and its headers. [OBSERVED]

Consequence: a re-implementation that needs a title/author must read it from the document's text
chunks, not from metadata. This is the single largest behavioural difference from the libmspub
prior-art assumption that `SummaryInformation` carries the usual Office property set.

## 16.5 Embedded objects

`Objects/Object N/` substorages carry their own `\x01CompObj`, `\x01Ole`, `\x02OlePres000`
(and `001`), optionally `\x01Ole10Native`, plus a nested `Contents` document. Their metadata is
therefore self-describing at the OLE level; the `Contents` stream of a nested object follows the
same rules as the outer document (identical `0xACE8` header, same version 300, same tag 125 —
verified by parsing several with `pubcore`). [OBSERVED]

The link from a drawing shape to its `Object N` substorage is carried by the shape record, not by
metadata — see the shape chapters.
