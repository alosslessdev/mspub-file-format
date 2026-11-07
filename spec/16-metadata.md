# 16 — Metadata

Publisher 95 writes very little metadata. There is no title/author/subject/created-date property
set: the only standard metadata stream is `\x05SummaryInformation`, and it carries one property,
a thumbnail. Everything else that describes the document lives either in the CFB directory
(container chapter) or in the `Contents` header and the singleton chunks (chapters 02–04).

## 16.1 Stream census

| Stream | Files with it | Notes |
|---|---|---|
| `\x01CompObj` | 130/130 | OLE class descriptor, §16.2 |
| `\x03Internal` | 130/130 | Publisher-private, §16.3 |
| `\x05SummaryInformation` | 129/130 | absent in `p95/x/MSPUB.PUB`; **6 of the 129 are zero-length streams**; §16.4 |
| `\x05DocumentSummaryInformation` | 0/130 | never written by Publisher 95 |
| `Quill`, `Escher` | 0/130 | Publisher 97/98 only |

Census counts over the 130 Publisher 95 CD documents (128 `.PUB` + 2 `.JSP`). A census that
tests *stream content* rather than *stream presence* reports 123 for
`\x05SummaryInformation`; the stream exists in 129 documents and 6 of those are empty.

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

The stream is Publisher-private bookkeeping carried by the CFB layer, not by the
`Contents` chunk directory: 12 bytes in 130/130 outer documents (`00 00 01 00`
+ a third u32 taking 0…241 + a zero tail); every `Objects/Object N/`
substorage carries its own (12 bytes in 41, 16 in 243 nested streams). The low
words are invariant (`0x0000`, `0x0001`); the third u32 has
no observed correlate — it equals neither the chunk count (0/128), the
`Objects` sub-storage count (17/130), nor any directory field — and bytes
`+0x08…+0x0B` are zero in 130/130, so no second field can be read out of the
tail either.

Closed as opaque/proven-carried: the CFB layer's name is all the format needs
(`\x03` = the `STREAMCFB_NOTIFY` VCS hint, so the OLE layer treats the stream
as internal bookkeeping), and the stream is never named by any code path in the
shipped binaries: the wide string `L"Internal"` occurs once per executable
(P95 file offset `0x22653E`, P97 `0x2352FA`, P98 `0x222FFE`) inside the
version-resource block (`ProductVersion`, `InternalName "MSPUB"`), never as a
storage/stream argument. Scan scope: zero hits for an Internal stream open in
`C:\pwrk\decomp95` (3 826 functions; the only `Internal` hit is
`TEXTMETRIC.tmInternalLeading` at P95 VA `0x004B36F9`), `notes/p98/decomp97`
and `notes/p98/decomp98` likewise. A reader MUST preserve the stream verbatim;
the word's exact semantics are unrecoverable from the shipped code — that is
the finding, not an open question. [OBSERVED for the byte census and the
negative]

## 16.4 `\x05SummaryInformation`

Present in **129 of 130** documents; absent only in `p95/x/MSPUB.PUB`. Six of the 129 are
**zero-length streams** — `CLASS_CD.PUB`, `JAZZY_CD.PUB`, `MODRN_CD.PUB`, `PLAIN_CD.PUB`
(the four `*_CD` templates), `CHEKLIST.JSP` and `INFOSHET.JSP` — so 123 documents carry an
actual property set. [OBSERVED]

A reader MUST tolerate an empty `\x05SummaryInformation`: the stream is a directory entry with
zero length and dereferencing its header would read past the end. Treat length 0 as "no
metadata" and skip the property-set parse.

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
