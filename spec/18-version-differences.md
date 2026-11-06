# 18. Version differences: Publisher 95 vs 97 vs 98

All three versions in scope write the **same container** and the **same
version-magic byte**. There is no header field whose value alone identifies the
product version; the versions are distinguished by a small set of derived
constants, by the presence of the text-engine storage, and by which chunk
markers appear.

## 18.1 Corpus used

| label | source | files | version magic `Contents[2]` |
|---|---|---|---|
| P95 | Publisher 95 installer media (`p95/x`) | 128 | `0x22` in 128/128 |
| P97 | Publisher 97 disk set, 11 `PUB4_*.CAB` (`p97/x`) | 106 | `0x22` in 106/106 |
| P97D | Publisher 97 CD "deluxe" (`p97deluxe/x`) | 248 | `0x22` in 248/248 |
| P98 | Publisher 98 CD (`p98/x`) | 2 | `0x22` in 2/2 |

`[OBSERVED]` — every `.PUB` file on all four media was opened with `olefile` and
its `Contents` stream inspected. The Publisher 98 CD carries exactly two `.PUB`
files (`MSPUB.PUB`, `ZMSPUB.PUB`); the Publisher 97 CD carries 248; the
Publisher 97 disk set carries 106; the Publisher 95 installer carries 128.

The binaries are three distinct builds:

| version | main executable | size | text engine |
|---|---|---|---|
| 95 | `MSPUB.EXE` + `MSPUBW32.DLL` | 2 419 200 | none (text inside `Contents`) |
| 97 | `MSPUB.EXE` + `MSPUBW40.DLL` | 2 508 048 | none (text inside `Contents`) |
| 98 | `MSPUB.EXE` + `MSPUB.M14` | 2 241 808 | `SHARED/QUILL/QS98.DLL` |

`[OBSERVED]` — the two Publisher 97 binaries (disk set and CD) are byte
identical (`md5 bbfe12c71748791995ffb3db5af4f6e4`). Neither the 95 nor the 97
executable contains the strings `Quill`, `QuillSub`, `Escher`, `EscherStm` in
either ASCII or UTF-16LE; the 98 executable contains `Quill` (ASCII, 2
occurrences) and `QS98` (UTF-16LE, 1 occurrence) — see chapter 13 and chapter 14.

## 18.2 Storage inventory per version

| OLE2 top-level name | P95 | P97 | P97D | P98 |
|---|---|---|---|---|
| `Contents` | 128 | 106 | 248 | 2 |
| `\x01CompObj` | 128 | 106 | 248 | 2 |
| `\x03Internal` | 128 | 106 | 248 | 2 |
| `\x05SummaryInformation` | 127 | 105 | 246 | 2 |
| `Objects` (with `Object N` children) | 84 | 70 | 202 | 0 |
| `Quill` | 0 | 0 | 0 | **2** |
| `Escher` | 0 | 0 | 0 | 0 |

`[OBSERVED]` — counts are files containing the name, over every file of the
corpus. The distinct top-level name set is therefore
{`\x01CompObj`, `\x03Internal`, `\x05SummaryInformation`, `Contents`, `Objects`}
plus `Quill` from Publisher 98 onward. This is the single largest format change
between 97 and 98 and the only one that adds a storage.

## 18.3 `Contents` header: per-version constants

Header layout is in chapter 02. The measured value sets are:

| offset | width | P95 | P97 | P97D | P98 |
|---|---|---|---|---|---|
| `0x00` | u16 | `0xACE8` (128) | `0xACE8` (106) | `0xACE8` (248) | `0xACE8` (2) |
| `0x02` | u8 | `0x22` (128) | `0x22` (106) | `0x22` (248) | `0x22` (2) |
| `0x03` | u8 | 0 | 0 | 0 | 0 |
| `0x04` | u16 | `0x012C` (128) | `0x012C` (106) | `0x012C` (248) | `0x012C` (2) |
| `0x06` | u16 | **4** (120), **`0x3303`** (8) | 4 (106) | 4 (248) | 4 (2) |
| `0x08` | u32 | = len(Contents) | = len(Contents) | = len(Contents) | = len(Contents) |
| `0x0C` | u16 | **125** (128) | **136** (105), 125 (1) | **136** (248) | **616** (2) |
| `0x0E` | u16 | 53 distinct | 37 distinct | 79 distinct | 295 (2) |
| `0x10` | u16 | 68 distinct | 53 distinct | 97 distinct | 0 (2) |
| `0x12` | u32 | **574** (128) | **640** (105), 574 (1) | **640** (248) | **894** (2) |
| `0x16` | u32 | 30 distinct | 22 distinct | 42 distinct | 940 (2) |
| `0x1A` | u32 | **34** (128) | **34** (106) | **34** (248) | **34** (2) |
| `0x1E` | u16 | 256 (87), 0 (17), 768 (16), 1280 (8) | 256 (49), 1280 (25), 0 (14), 512 (11) | 1280 (125), 256 (75), 0 (28), 768 (11) | 1280 (2) |
| `0x20` | u16 | 1280 (128) | 512 (77), 256 (28), 1280 (1) | 512 (201), 256 (47) | 1280 (2) |

`[OBSERVED]` — each cell gives the value and the number of files that carry it;
"n distinct" means the field varies per document (it is document data, not a
version constant).

Findings:

* **`0x0C` and `0x12` are the practical version discriminator.**
  `(0x0C, 0x12)` = `(125, 574)` for Publisher 95, `(136, 640)` for Publisher 97
  (105 of 106 disk-set files and 248/248 CD files), `(616, 894)` for
  Publisher 98. `[OBSERVED]`
  The single P97 outlier is `p97/x/INFLNTLB.PUB`, which still reports
  `(125, 574)` — a Publisher 95-era header on the 97 media. It is the only
  file on the 97 media that was not re-saved by the 97 build.
* `0x12` is the offset of the text section (chapter 13), so its growth from 574
  to 640 to 894 follows from a larger fixed region in front of the text; treat
  `(0x0C, 0x12)` as a *derived* signature rather than an independent version tag.
* `0x1A` = 34 is invariant across all 484 files.
* `0x06` is 4 in 476 of 484 files. Eight Publisher 95 files carry `0x3303`:
  `p95/x/MSPUB.PUB`, `p95/x/PAGEWIZ/{BIZTRIP,BRBLLOON,CONGRATS,MRBLBRDR,PERYARD2,SAILBOAT,STILLIFE}.PUB`.
  The field is constant within each file and does not correlate with document
  size or chunk inventory in the sample; see Open `Q18-3`.

## 18.4 Chunk-marker presence

Counts are chunk occurrences, not files. A blank cell means the marker never
appears in that corpus.

<!-- table:chunk-presence -->
| marker | P95 | P97 | P97D | P98 | first seen |
|---|---|---|---|---|---|
| `0x00` | 1092 | 1211 | 2735 | 0 | 95 |
| `0x01` | 218 | 157 | 360 | 2 | 95 |
| `0x02` | 248 | 196 | 561 | 2 | 95 |
| `0x03` | 617 | 479 | 1520 | 2 | 95 |
| `0x04` | 696 | 665 | 1413 | 2 | 95 |
| `0x05` | 1110 | 1062 | 2302 | 2 | 95 |
| `0x06` | 1322 | 867 | 1850 | 2 | 95 |
| `0x07` | 266 | 190 | 692 | 2 | 95 |
| `0x08` | — | — | — | 2 | **98** |
| `0x09` | — | — | — | 2 | **98** |
| `0x0A` | — | — | — | 2 | **98** |
| `0x0B` | — | — | — | 2 | **98** |
| `0x0F` | 827 | 705 | 1394 | 0 | 95 |
| `0x14` | 712 | 593 | 1423 | 12 | 95 |
| `0x15` | 128 | 106 | 248 | 2 | 95 |
| `0x16` | 128 | 106 | 248 | 0 | 95 |
| `0x1A` | 128 | 106 | 248 | 0 | 95 |
| `0x1C` | 128 | 106 | 248 | 0 | 95 |
| `0x1E` | 128 | 106 | 248 | 2 | 95 |
| `0x1F` | 128 | 106 | 248 | 2 | 95 |
| `0x21` | 129 | 88 | 310 | 0 | 95 |
| `0x22` | 489 | 373 | 1272 | 0 | 95 |
| `0x23` | 128 | 106 | 248 | 2 | 95 |
| `0x26` | 128 | 106 | 248 | 0 | 95 |
| `0x27` | 14 | 4 | 4 | 0 | 95 |
| `0x28` | 128 | 106 | 248 | 2 | 95 |
| `0x29` | 128 | 106 | 248 | 2 | 95 |
| `0x2A` | 128 | 106 | 248 | 0 | 95 |
| `0x2B` | 30 | 14 | 27 | 0 | 95 |
| `0x2C` | 137 | 115 | 275 | 2 | 95 |
| `0x2D` | 128 | 106 | 248 | 0 | 95 |
| `0x2E` | 128 | 106 | 248 | 0 | 95 |
| `0x2F` | — | 4 | 8 | 0 | **97** |
| `0x31` | 384 | 413 | 991 | 6 | 95 |
| `0x32` | 384 | 318 | 744 | 6 | 95 |
| `0x34` | 68 | 72 | 191 | 0 | 95 |
| `0x35` | 74 | 66 | 166 | 0 | 95 |
| `0x37` | 16 | 36 | 126 | 2 | 95 |
| `0x38` | 15 | 18 | 94 | 0 | 95 |
| `0x39` | 128 | 106 | 248 | 2 | 95 |
| `0x3A` | — | 95 | 247 | 0 | **97** |
| `0x3B` | — | 4 | 8 | 0 | **97** |
| `0x3F` | — | 13 | 22 | 0 | **97** |
| `0x40` | — | — | — | 2 | **98** |
| `0x41` | — | — | — | 2 | **98** |
| `0x43` | — | — | — | 2 | **98** |
| `0x45` | — | — | — | 2 | **98** |
| `0x47` | — | — | — | 2 | **98** |
| `0x4C` | — | — | — | 2 | **98** |
| `0x52` | — | — | — | 2 | **98** |
<!-- /table:chunk-presence -->

`[OBSERVED]` — counts over every file of each corpus.

Cautions when reading this table:

* The P98 column comes from **two** files, and those two files are "blank
  publication" documents that contain one instance of most object kinds. Their
  marker set is therefore the *complete* set the 98 build can emit, but the
  counts carry no statistical weight.
* The P95 column has 8 files with the anomalous `0x04` header word (Open
  `Q18-3`); their markers are included in the counts.
* Markers `0x08`–`0x0B` are absent from 95/97 and present in 98. Markers
  `0x2F`, `0x3A`, `0x3B`, `0x3F` are absent from 95 and present in 97.
  Those eight markers are the marker-level fingerprint of the version bump.

## 18.5 What actually changed in the payloads

Re-saving the same template under a newer build is the only controlled
comparison available, because the corpora are template libraries rather than
user documents. The measured example is `AUDIOLBL.PUB`, which exists on both the
95 installer and the 97 disk set:

| chunk | P95 size | P97 size | delta |
|---|---|---|---|
| `0x15` DOCUMENT | 124 | 154 | +30 |
| `0x29` | 171 | 208 | +37 |
| `0x23` | 30 | 48 | +18 |
| `0x1E` | 133 | 157 | +24 |
| `0x1F` | 16 | 26 | +10 |
| `0x31` LOGO | 30 | 30 | 0 (two extra instances) |
| `0x32` | 16 | 26 | +10 |
| `0x2A` | 16 | 26 | +10 |
| `0x26` | 75 | 97 | +22 |

`[OBSERVED]` — `p95/x/PAGEWIZ/AUDIOLBL.PUB` vs `p97/x/AUDIOLBL.PUB`, chunk
payload extents taken from the directory (chunk size = next offset − own offset).

The pattern is a *uniform widening of fixed records* (typically +10 or +18
bytes) plus new `0x31`/`0x3A` instances, i.e. Publisher 97 grew existing
records rather than replacing them. The generic per-template table is in
`notes/p97/slices/version_diff.md`.

## 18.6 Version boundary for the text layer (summary)

| version | text storage | engine | chapter |
|---|---|---|---|
| 95 | inside `Contents` (text section at `Contents[0x12]`) | in `MSPUB.EXE` | 13.5 |
| 97 | same, unchanged | in `MSPUB.EXE` | 13.5 |
| 98 | **`Quill/QuillSub/CONTENTS`** (+ the legacy section still present) | `QS98.DLL` | 13.2 |

`[OBSERVED]` — storage enumeration (§18.2) plus binary string search (§18.1).

## 18.7 Open

* `Q18-1` — The two P98 documents are blank publications. A Publisher 98
  document *with* text would show whether the legacy `Contents` text section is
  still populated alongside Quill, or emptied. Experiment: obtain/author one
  98 document with text and compare `Contents[0x12]` section contents with its
  Quill `TEXT`/`STRS` chunks.
* `Q18-2` — Whether Publisher 97 can *read* a Publisher 98 Quill document is a
  binary-behaviour question; there is no `Quill` string in the 97 executable, so
  the answer is expected to be "no". Experiment: static check of the 97 import
  table and of its storage-name table (no dynamic run available).
* `Q18-3` — Header `0x06` is `0x3303` in exactly eight Publisher 95 files
  (listed in §18.3) and `4` in the other 476. Its meaning is unknown: it is not
  a size, not a page count, and not a template class. Experiment: convert one of
  the eight with the 95 build and one with the 97 build and compare the written
  value; if it is preserved verbatim the field is an opaque per-document
  "creator/tool version" stamp.
