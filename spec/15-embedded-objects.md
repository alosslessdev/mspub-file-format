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
| … | 16 or 24 | `Reserved1` (MS-OLEDS `CompObjStream`; Length = `0x71B239F4`, remainder MUST-be-ignored) |

The tail's first DWORD sits at `Reserved1.Length` past the header + 3 ANSI
strings; its value `0x71B239F4` exceeds `0x28`, so per MS-OLEDS every
subsequent byte is reader-ignored territory. The 16-byte form is
`F4 39 B2 71` + 12 zeros (1 074 streams, byte-identical); the 24-byte form is
`F4 39 B2 71` + `u32 8` + DWORD + DWORD ∈ {96, 136} + 8 zeros (971 streams,
all `MSWordArt.2` with empty UserType and Clipboard strings, CompObj size 76).
The split records which OLE write path ran: the 24-byte form is exactly the
short WordArt record with no UserType/Clipboard strings (WordArt *with*
descriptive strings takes the 16-byte form, 268×); both forms co-occur inside
31 files, i.e. per-object OLE-library behaviour, not a file switch. The
varying DWORD (167 distinct values, ≥ 4.7M, 4-aligned) equals no persisted
size in 0/971 cases and the 96/136 DWORD separates no Contents-length class —
both are ignored writer-side residue that a reader MUST preserve opaquely.
Writer and reader are the OLE runtime (`OleCreate*`/`OleSave` →
`OleLoad` in `PUBOLE98.DLL`: `_MatCreateObject@32` VA `0x60012cf0`,
`_MatLoadObject@20` VA `0x60016d90`); no Publisher function parses past the
ProgID: PE byte search for `F4 39 B2 71` finds 0 hits in `MSPUB.EXE`
95/97/98, `QS98.DLL`, `PUBOLE98/32.DLL`, and a decomp-text sweep finds 0 hits
in all 13 437 functions (5 360 + 4 252 + 3 825 + 208 + 208 + 225).
[OBSERVED for the corpus identity; OS-structure member by offset]

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
equal to 1 (A: x=1; C: y=1). The `x`/`y` word is a class lane: **C16 occurs
iff the object's `CompObj` UserType is the descriptive `Microsoft WordArt
2.0` string, 231/231**; A (A12 591 + A16 417) covers everything else —
empty-UserType converted WordArt (971/971 take the 24-byte `CompObj` tail),
all `WordArt 3.0` (20), all `/I``` (13) — with only 4 A-side exceptions
carrying a WA2 UserType (2 unique PageWizard templates × 2 corpora:
`ITINRARY` Obj 29, `SITTRLST` Obj 1). No C16 ever pairs with an empty
UserType, a WA3 UserType, or a 24-byte tail. The 12-vs-16 framing is a
separate writer-version lane (A12: 567/591 in root-`CompObj`-94 Pub-3.0
documents; A16: 241/417 in root-78 Pub-2.0 documents; C16 mixed).
[OBSERVED 1 239/1 239]

The reader is the shipped OLE layer. `PUBOLE98.DLL` carries the CFB names as
wide strings and opens the lanes explicitly: per-object opener `FUN_60017af0`
(VA `0x60017af0`) selects the Internal lane for `param_4 == -1` and
`Contents` for `0`, building `Object N` names in `FUN_600171a0`/
`FUN_60017210` (VAs `0x600171a0`/`0x60017210`) via `swprintf("%s %ld")`.
The live object selector keys off the `CompObj` CLSID, not the Internal
bytes: `_MatLoadObject@20` (VA `0x60016d90`) reconstitutes via
`OleConvertOLESTREAMToIStorage` + `OleLoad`, then `FUN_60016200` branches
presentation/extent handling on the CLSID at `obj+0x96` (against 16 zero
bytes and the OLE1-converted class). A reader MUST preserve the 12/16 bytes
and MUST NOT treat `x`/`y` as geometry. [OBSERVED for the VAs and the
CompObj/UserType identity; the writer-version direction is INFERENCE]

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
+0x0F  u8  0x00 (1523) or 0x80 (611)    stale bit, see 15.8.1
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

### 15.8.1 The `+0x0F` stale bit

Domain `{0x00, 0x80}` (1 523 / 611 over 2 134 references; all exactly 18 bytes).
`0x80` means the object presentation is **stale — the object needs updating**;
`0x00` means up to date. [OBSERVED]

Writer and reader are the shipped OLE layer, not `MSPUB.EXE`. The writer is
`_MatSaveObject@20` (`PUBOLE98.DLL` VA `0x60016bf0`; the 95-era `PUBOLE32.DLL`
export is the same function at `0x600165A0`): it serialises the 10-byte
`MO`-body as `MO(2) + N(2) + zero(1) + flags(2) + 0(2)`, and `+0x0F` is the
high byte of a copy of the in-memory object flag word at `obj+0x92` shifted
so that bit `0x40` lands at `0x80` — `0x80` iff the flag is set, `0x00`
otherwise. The loader is `_MatLoadObject@20` (VA `0x60016d90`), which reads
the `4D 4F` + 8 bytes and restores the bit (`(u16 & 0x8000) >> 9`) into
`obj+0x92` bit `0x40` before calling `OleLoad`. No function in the `MSPUB.EXE`
95 (3 825 fns), 97 (4 252) or 98 (5 360) decompiled trees reads `rec+0x0F`:
the only `== 0x22` marker dispatch in each (`MSPUB.EXE` 95 VA `0x00444c1d`,
97 VA `0x0042c6d2`, 98 VA `0x004f6f1d`) forwards to the object loader.

The flag is set when the server reports the object not running
(`OleIsRunning == 0`, in `FUN_600164C0`) and cleared once the object is
updated (`_MatUpdateObject@8`, VA `0x60013be0`; also `_MatRevertObject@4` and
the load path); the idle loop (`_MatFIdle@12`, VA `0x60011730`) calls the
updater and clears it. The "display as icon" reading is excluded: iconic is a
different bit of the same word (`_MatIsIconic@8` tests bit `0x08`). A reader
that only draws the cached presentation ignores the bit; a re-saver must
preserve it. [OBSERVED for the VAs and the branch behaviour]

Corroborating skew (not a rule): objects whose preview carries `Advf 32`
(`OlePres000 +0x14`, §15.5) never show `0x80` (359/359 at `0x00`); `Advf 16`
is `0x00` in 36/38; `Advf 2` mixes (`0x00` 1 125 / `0x80` 609). [OBSERVED]

## 15.10 Open

* `0x0022` `+0x0F` flag — domain and negative correlations published in §15.8.1; the two
  candidate readings are still undistinguished.
* `\x03Internal` `x`/`y` bit — variant A/C splits by nothing measured (class, size, owner,
  ordinal). Two readings remain: a saved-state flag or an allocation lane.
* `OlePres000 +0x14` (2 / 32 / 16) — measured against the `0x0022` flag and object class with no
  correlation; `[UNKNOWN]` picture-type field.
