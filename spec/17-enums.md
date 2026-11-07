# 17 — Enum domains

Consolidated registry of the enumerated values used across the format. Each entry
is measured over the 493-document corpus unless marked from binary evidence. Where
the value domain is known but the meaning of an individual value is not, the
semantics are marked `[UNKNOWN]` — a reader must preserve unknown values
unchanged.

## 17.1 Container and header enums

| Field | Location | Domain | Notes |
|---|---|---|---|
| `magic` | `Contents +0x00` | `0xACE8`, `0xACE7` | `ACE7` is the legacy form (chapter 02) |
| `version_magic` | `Contents +0x02` | `0x22`, (`0x2C` = 2000+) | 95/97/98 all write `0x22` |
| `format_version` | `Contents +0x04` | `200`, `300`, `710` | 300 = this family; loader also accepts the legacy pair 200/710 |
| `header_tag` | `Contents +0x0C` | `125` (P95, and one P97 file), `136` (P97/97-deluxe), `616` (P98), `704` (version 200) | accepted per build; see chapter 02 §2.2 |
| directory record `flags` | directory | `0x1440 \| (bit3<<3) \| (bit5<<5) \| (bit7<<7) \| (cls<<8)`, 13 values | every bit named below; the per-record writer forces bit 6 = 1 and bits 11/15 = 0 (chapter 03 §3.6) |

Bit decomposition of the 13-value domain (10 732 non-document records, all 493 documents):

| bits | mask | meaning | anchor |
|---|---|---|---|
| 0–1 | `0x0003` | **in-use state**: 0 idle, 1 in use, 2 sticky, 3 assignable; always 0 on disk | setter/restorer VA `0x0041D0C7` |
| 2, 4 | `0x0014` | unused — never set in any corpus record | — |
| 3 | `0x0008` | "registered in auxiliary reference lists" `[INFERENCE]` | tested by VA `0x00407C1A` |
| 5 | `0x0020` | record-class **memory/allocation** flag ("owns a separate payload block") `[INFERENCE]`; set on exactly `0x1A 0x1F 0x21 0x31 0x32 0x37 0x38 0x39` and 12/130 of `0x26`, never with `cls != 2` | no individual setter; invariant only |
| 6 | `0x0040` | **persisted / live record** — forced 1 on every record | writer VA `0x00538727`; save traversal VA `0x0044D3FC`; cleared at load VA `0x0045E143` |
| 7 | `0x0080` | **linked OLE object** (object is a link, not embedded) — closed in chapter 03 §3.6.5 | setter VA `0x004502F6` (P98 `0x004F74DA`); menu switch VA `0x00438216` |
| 8–9 | `0x0300` | 2-bit **class/level** (0…3) | getter VA `0x004010AD`, setter VA `0x0040827E` |
| 10 | `0x0400` | constant 1 on disk; set on objects that have a parent | ctor VAs `0x0044D909`, `0x004628E3` |
| 11 | `0x0800` | "selected" `[INFERENCE]` — force-cleared on save and on load | writer VA `0x00538727`; loader VA `0x0045E30A`; setter VA `0x00401A5B` |
| 12–14 | `0x7000` | 3-bit **slot kind**: 1 = live chunk (all disk records), 6 = free/reusable | loader VA `0x0045E15B`; free-slot write VA `0x00407DA5` |
| 15 | `0x8000` | traversal mark — force-cleared on save and load | writer VA `0x00538727`; loader VA `0x0045E14A` |

Bits 2 and 4 are the only write-only bits: no corpus record sets them and no setter exists,
so a reader cannot observe them and must reproduce 0. Everything else is either forced by
the writer (6, 11, 15) or has a named accessor above; the full derivation is in chapter 03
§3.6.

Directory `flags` domain observed over all 493 documents (non-document records):

```
0x1440 0x1448 0x14C0 0x1540 0x1548 0x1640 0x1648 0x1660 0x16C0 0x16C8 0x16E0 0x1740 0x1748
```

The document record (index 0) instead carries `idHighWaterMark`, not a flags value.

## 17.2 Chunk markers → object class

The marker **is** the shape/object type discriminator. Mapping observed in all four
corpora (counts and per-version presence in
[blocks/chunk-markers.md](blocks/chunk-markers.md)):

| Marker | Class | Chapter |
|---|---|---|
| `0x0000`, `0x0001`, `0x0003`, `0x0007` | free-form shape (polygon/curve family) | 06 |
| `0x0002`, `0x0003` (98) | image-bearing shape | 08 |
| `0x0004` | line | 06 |
| `0x0005` | rectangle | 06 |
| `0x0006` | shape hosting an embedded OLE object | 15 |
| `0x0008`, `0x0009`, `0x000A`, `0x000B` | shape variants, Publisher 98 only in corpus | 06 |
| `0x000F` | group | 07 |
| `0x0014`, `0x0041` | page / page slot (98) | 05 |
| `0x0015` | document | 04 |
| `0x0016` | document-level record holding four chunk ids | 06 |
| `0x001A`, `0x001C`, `0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x0028`, `0x0029`, `0x002A`, `0x002C`, `0x002D`, `0x002E`, `0x0031`, `0x0032`, `0x0034`, `0x0035`, `0x0037`, `0x0038`, `0x0039` | per-document tables/styles/logos | 11 |
| `0x0021` | image data blob | 08 |
| `0x0022` | 18-byte "MO" record | 08, 12 |
| `0x0047` | palette (98) | 09 |

`[UNKNOWN]` for the exact object class of every marker not listed with a chapter
chapter reference; those markers have size rules only (chapter 12).

## 17.3 Page

| Field | Location | Domain |
|---|---|---|
| `pageKind` | PAGE `+0x18` (95/97), `+0x1C` (98) | `0` ×2604, `2` ×80, `4` ×80, `1` ×9 |

`0` = ordinary page, `2` = composites the following layer page's objects into its own
z-order, `4` = layer page with an empty child list, `1` = behaves like `0` in the
corpus (`[UNKNOWN]` distinction). See chapter 05.

## 17.4 Document

| Field | Location | Domain |
|---|---|---|
| `coordinateSystem` | DOCUMENT `+0x12` | `0` ×403, `8` ×35, `1` ×19, `3` ×17, `6` ×8, `4` ×7, `5` ×3, `7` ×1 |
| `publicationType` | DOCUMENT `+0x64` | `0 … 34` (0…26 in Publisher 95), 26 distinct |
| `defaultTabTwips` | DOCUMENT `+0x3C` | `720` ×484, `432` ×4, `360` ×3, `1296` ×2 — twips |

`coordinateSystem` selects how the publication page is arranged on the sheet. The
dispatcher is VA `0x004DB30C`, which rewrites the page rectangle per value; chapter 04
§4.10 gives the full table.

| Value | Meaning |
|---|---|
| `0` | one page per sheet (base rectangle) |
| `1` | two pages per sheet, side by side (x extent halved) |
| `2` | two pages per sheet, stacked (y extent halved); the two-page-spread view is enabled only for this value |
| `3` | four pages per sheet, fold on the left (both extents halved) |
| `4` | four pages per sheet, fold on the top (both halved, page rotated 90°) |
| `5` | index card, 5 × 3 in default |
| `6` | business card, 3.5 × 2 in default |
| `7` | banner (page-size limit ×4.8, zoom floor 68 %) |
| `8` | label (Publisher 97 only; no geometry transform) |

`8` never occurs in the Publisher 95 corpus and `2` never occurs in any corpus file, though
both are handled by the dispatcher. The name `coordinateSystem` is the one libmspub uses for
the same word; the meanings above come from the binary, not from prior art. [OBSERVED]

`publicationType` is read by three switches (VAs `0x004BF85F`, `0x004C6C37`, `0x00561D04`)
that map it onto a resource index and a help/navigation topic. All 35 label publications
carry `15`, the value the Publisher 97 layout table maps to `coordinateSystem == 8`
(chapter 04 §4.9.3).

## 17.5 Geometry

| Field | Location | Domain |
|---|---|---|
| `rotation` | shape `+0x04` | `0 … 3599`, **1/10 degree** (0.1°), counter-clockwise, mod 3600 |
| coordinates | shape `+0x06` | signed EMU; `left ≤ right`, `top ≤ bottom` |
| descriptor byte `A` | chunk `+0x02` | per marker **and build**, from the 54-byte table at VA `0x00593308`; the constructors' internal split point, **not** a length or the record extent (chapter 04 §4.11) |
| descriptor byte `B` | chunk `+0x03` | per marker **and build**; last fixed byte, `base = B + 10` for every family; per marker table in chapter 12 §12.2 |

## 17.6 Colour

Colour is a 32-bit **colour reference**, not an RGB tuple. The top three bits of the
high byte select the space (chapter 09 §9.1):

| Tag range | Space | Resolution |
|---|---|---|
| `0x00`–`0x1F` | palette index | look up in the 56-entry table |
| `0x20`–`0x3F` | literal RGB (`COLORREF`: R low byte) | direct |
| `0x40`–`0x5F`, `0x80`–`0x9F` | derived colour | binary-only transform |
| `0xA0`–`0xBF` | automatic | `0x4737B` when the low word is 0 |
| `0xC0`–`0xDF` | brightness-modified reference | binary-only transform |
| `0x60`–`0x7F`, `0xE0`–`0xFF` | returned unchanged | — |

The 56-entry default palette is tabulated in chapter 09 §9.2 and is available to
code as `tools/palette.py` (generated from that table, with `decode_colorref`).

## 17.7 Version signatures

| Observation | P95 | P97 | P98 |
|---|---|---|---|
| DOCUMENT size | base | base + 30 | base + 72 |
| DOCUMENT descriptor `u16@+0x02` (bytes `+0x02/+0x03`) | `0x6A78` (`78 6A`) | `0x889E` (`9E 88`) | `0xB2D2` (`D2 B2`) |
| PAGE record base | `0x24` | `0x24` | `0x28` |
| PAGE descriptor bytes `+0x02/+0x03` | `1A 1A` | `1A 1A` | `1E 1E` |
| page slots | `0x14` | `0x14` | `0x14`, `0x41` |
| shape record | base | base | base + 8 (image-bearing shapes +24) |
| text engine | in `Contents` | in `Contents` | `Quill/QuillSub/CONTENTS` |
| drawing layer | none | none | `Escher/EscherStm` |
| palette chunk `0x47` | absent | absent | present |

See chapter 18 for the per-chunk delta table.
