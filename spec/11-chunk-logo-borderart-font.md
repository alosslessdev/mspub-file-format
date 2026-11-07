# 11 — Document-level records: fonts, logo/design, border art, print setup

Most of a document's non-geometric data lives in **singleton records**: one chunk per
document (or a small fixed number), referenced by id from the DOCUMENT chunk. This
chapter documents their framing, size rules and the payloads that are understood.

All rules below were re-measured over the Publisher 95 corpus (130 documents) and, where
stated, over the whole 493-document corpus. Counts are stated per rule.

## 11.1 DOCUMENT slot map

The DOCUMENT chunk (`0x0015`) holds the ids of its singletons at fixed offsets. `0` means
the record is absent. Every non-zero value resolves to a chunk of the stated type
(130/130 per slot). [OBSERVED]

| Offset | Marker | Record | Present |
|---|---|---|---|
| `+0x04` | `0x0029` | print setup (DEVMODE/DEVNAMES) | 130/130 |
| `+0x06` | `0x0028` | six-key font/format dictionary (§11.8.1) | 130/130 |
| `+0x08` | `0x0014` | first page | 130/130 |
| `+0x46` | `0x0023` | fixed 4-slot table | 130/130 |
| `+0x48` | `0x0031` | design/object set #1 | 130/130 |
| `+0x4A` | `0x001E` | **font table** | 130/130 |
| `+0x4C` | `0x001F` | **line/border-art style table** | 130/130 |
| `+0x4E` | `0x0016` | story container | 130/130 |
| `+0x50` | `0x002A` | font-substitution table | 130/130 |
| `+0x52` | `0x002B` | document name list | 30/130 |
| `+0x54` | `0x0026` | paragraph-style names | 130/130 |
| `+0x56` | `0x0031` | design/object set #2 | 130/130 |
| `+0x58` | `0x0031` | design/object set #3 | 130/130 |
| `+0x5A` | `0x0034` | 14-byte sub-table | 70/130 |
| `+0x5C` | `0x0035` | DLL binding record | 74/130 |
| `+0x5E` | `0x0037` | colour list, 6-byte elements | 16/130 |
| `+0x60` | `0x0038` | colour list, 10-byte elements | 15/130 |
| `+0x68` | `0x0039` | 48-byte document record | 130/130 |
| `+0x86` | `0x003F` | label-sheet template | 35/130, and `0` in the other 181 documents whose DOCUMENT is ≥ 0x88 bytes |

The three `0x0031` slots always name distinct chunks.

`+0x86` exists only in the 154-byte DOCUMENT form (the label files `p97/x/B71xx.PUB`,
`p97/x/D71xx.PUB`, `p97deluxe/x/PageWiz/B51xx.PUB`, `…/D51xx.PUB`, `…/equiplbl.pub`,
`…/lamidtag.pub`, …). It holds the id of the document's one `0x003F` in 35/35, and `0`
in every other DOCUMENT of that size (181/181) and in every DOCUMENT larger than 0x88
bytes (326/326 measured; the one 138-byte DOCUMENT, `p95/x/PAGEWIZ/CATALOG.PUB`, has a
page-id list at that offset and no `0x003F` at all, so the slot belongs to the 154-byte
form). The reader is `MSPUB.EXE` 98 VA `0x00473dcb` / `0x0049f782`, both of which do
`*(ushort *)(DAT_00613920 + 0x86)` and resolve the id through the chunk table —
`DAT_00613920` being the in-memory DOCUMENT record. [OBSERVED]

### 11.1.1 Slots that change meaning between generations

Measured over 487 documents (128 `p95`, 106 `p97`, 248 `p97deluxe`, 5 `p98`). Two slots in
the block above and one below it do **not** keep their meaning, so a reader must dispatch
on version rather than assume the P95 table: [OBSERVED]

| Offset | P95 | P97 / P97D | P98 |
|---|---|---|---|
| `+0x4E` | `0x0016` story container, 128/128 | `0x0016`, 354/354 | `0`, 5/5 — the P98 publications have no story container at all |
| `+0x6A` | **not an id**: the last-page index (`Npages − 1`) | `0x0031`, a **fourth** design set, 247/248 | `0x0045`, 5/5 |
| `+0x6E` | not an id (constant `2`) | `0` | `0x0047` **PALETTE**, 5/5 |

`+0x6E` is the palette reference introduced with Publisher 98 (chapter 09 §9.3) and is the
one document-level singleton whose slot sits outside the `0x46…0x68` block. The Publisher 98
DOCUMENT record is 72 bytes longer than the 95 one (chapter 04 §4.1), and these three slots
account for the re-purposing that came with that growth.

## 11.2 Story container `0x0016`

```
0x00 u16 0x0016
0x02 u8  0x1A              A
0x03 u8  0x10              B
0x04 u32 serial            document serial, replicated in the 0x002D/0x002E children
0x08 u16 id of the 0x001A chunk
0x0A u16 id of the 0x001C chunk
0x0C u16 id of the 0x002E chunk
0x0E u16 id of the 0x002D chunk
```

Fixed 16 bytes (130/130). Slot order is `1A, 1C, 2E, 2D` — not ascending marker order.
`+0x04` is a document serial, not a style id and not a chunk id: its value (2…13 628,
high word 0 in 130/130) is byte-identical to `u32@+0x16` of the same document's `0x002E`
child in 130/130 documents and to `u32@+0x16` of its `0x002D` child in 129/130 (the one
exception is `SITTRLST.PUB`, whose `0x002D` carries 10 against 175 in the other two
records). It exceeds the entry count of every table it could index — larger than
`n` of the `0x001A` child in 130/130, than `count` of the `0x0026` table in 130/130 and
than `n` of the `0x001C` child in 127/130 — so no entry array can be addressed by it.
The earlier "style id, NOT a chunk id" reading is refuted by the replication: a style
selector would not be identical in three independent records. No shipped binary reads
`+0x04` back — the only consumers of the story container resolve its child ids
(`MSPUB.EXE` 95 VA `0x00406088` / `0x0040148c` read the `0x001A` id at `+0x08` and copy
slots out of it with the fixed-element accessor VA `0x004017d7`; `MSPUB.EXE` 98 VA
`0x0050e030` reads the child id at in-memory `+0x10` and indexes it with VA
`0x004fc5a9`) — so the serial is **write-only**: a reader must preserve it verbatim and
must neither resolve it nor index by it. Scan scope: `MSPUB.EXE` 95 (3 826 functions),
97 (4 252) and 98 (5 360). [OBSERVED for the layout, the replication and the scan;
INFERENCE that the number counts document edits, which nothing verifies]

### 11.2.1 `0x001A` — the story's run list

`0x001A` is the story container's first child (`+0x08`). Its size rule is
`26 + 14·n`, but the 14 is **not** an element stride: the record is a 26-byte header, then
`u32[n]`, then `n` **10-byte** slots. The element size word at `+0x08` says `10` in every
instance (482/482), which is the authoritative figure:

```
+0x00 u16  0x001A
+0x02 u8   0x04          A
+0x03 u8   0x04          B
+0x04 u16  n             duplicate at +0x06 (482/482)
+0x08 u16  10            element size (482/482)
+0x0A u16  field         NOT n+1: independent, 0…35, differs from n+1 in 109/482
+0x0C i16  field         small signed, -3…4 is the bulk
+0x0E u16  field         0 (276) or 0xFFFF (206) — a "none" marker
+0x10 u16  flags         small values, mostly odd (1 ×112, 3 ×63, 5 ×52, 7 ×25, 9 ×23; 0 ×26)
+0x12 u16  8             (482/482)
+0x14 u32  0             (482/482)
+0x1A u32[n] offsets     non-decreasing, 465/465 of the non-empty records
+0x1A+4·n   n × 10-byte slots
```

The slot is `{u16 chunkId, u16 flag, u32 offset, u16 index}`; the `chunkId` is the
**first** field, and that is what fixes the field order, because it resolves:

* 4 854 live slots (non-zero id) over 9 604 slots: **4 854/4 854 resolve to a chunk of the
  same document, no miss**; 4 601 name a `0x0000` record and 253 a `0x0001`, i.e. the text
  runs / shapes that belong to the story.
* the 4 750 empty slots are all zero with `index == 0xFFFF` (the "none" marker), so `n` is a
  slot high-water mark and a reader must skip them, exactly as for the free lists of §11.3.1
  (the difference is that `0x001A` marks a dead slot with an all-zero body plus `0xFFFF`, not
  by a link value, because it is the fixed-element flavour and has no offset table).
* the `u32` field steps by 4 between consecutive live slots (0, 24, 28, 32, 36, 40, 44 in
  `BMEMO1.PUB`), so it is a byte offset into a 4-byte-granular table, and `index` is an
  independent small ordinal. The consumers confirm the use, if not the names:
  `MSPUB.EXE` 95 VA `0x00406088` copies a slot out with the fixed-element accessor VA
  `0x004017d7`, branches on the slot `flag` (`2`/`3` take the alternate story path), and
  reads the slot's range as two consecutive `u32` words through the offset-table accessor
  VA `0x00401b19` (which addresses the `u32[n]` prefix: element `k+1` is the array word
  `k`); `MSPUB.EXE` 98 VA `0x0050e030` indexes the same array from the shape's story
  position with VA `0x004fc5a9`. What `offset` addresses, and what the non-`1` `flag`
  values select, remain `[INFERENCE]` — the record is consumed as a list of run ids plus
  their ranges.

Worked example — `p95/x/PAGEWIZ/BMEMO1.PUB` id `0x018E`, 222 bytes, `n = 14`:
`u32[14] = (20, 20, 36, 36, 130, 130, 222, 222, 302, 302, 347, 347, 368, 368)` (seven
distinct ascending values, each doubled — the pairwise duplication holds in 408 of the 465
non-empty records), then slots `(0x01CC,1,0,10)`, `(0,..,0xFFFF)`, `(0x01E1,1,24,11)`,
`(0,..,0xFFFF)`, `(0x019A,1,28,7)`, `(0x01D0,1,32,8)`, `(0x01D1,1,36,9)`, `(0x01E2,1,40,12)`,
`(0x01CD,1,44,13)` — the seven ids are all 102-byte `0x0000` chunks whose parent is
`0x0103`. [OBSERVED]

## 11.3 Container header

`0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x002A`, `0x002B`, `0x0032`, `0x0034`, `0x0037`,
`0x0038` (and `0x001A`/`0x001C` with a per-type element size) share one header:

```
+0x00 u16 marker
+0x02 u8  A           structural landmark (see 11.9)
+0x03 u8  B           constant per type
+0x04 u16 nEntries
+0x06 u16 nEntries    duplicate
+0x08 u16 endOffset   == size - 0x0E      (offset-table flavour)
        u16 elementSize                   (fixed-element flavour)
+0x0A u16 mode        0 / 1 / 5
+0x0C u16 freeHead    free-slot-list head, 0xFFFF = list empty   (see 11.3.1)
+0x0E ...             offsets relative to chunk+0x0E, then payload
```

Two flavours:

* **Offset table** — element `k` runs from `chunk+0x0E+off[k]` to the next offset (or to
  `size`). Used by `0x001E`, `0x001F`, `0x0023`, `0x0026`, `0x002A`, `0x002B`, `0x0032`.
* **Fixed element** — payload is `n × elementSize` bytes at `+0x0E`, so
  `size == 0x0E + elementSize·n`. Used by `0x0037` (6), `0x0038` (10), `0x001A` (10, with a
  `u32[n]` prefix — §11.2.1), `0x001C`/`0x002D`/`0x002E` (8).

**Publisher 97 widens the offset entries from `u16` to `u32`**, but the descriptor bytes
`(A, B)` do **not** change: `0x001E` keeps `(0x08, 0x04)` and
`0x001F`/`0x0023`/`0x0026`/`0x002A`/`0x0032` keep `(0x04, 0x04)` in Publisher 95, 97
**and** 98 alike (`0x001E` 493/493 chunks, `0x001F` 493/493). The earlier statement
that `A` doubles with the width is refuted: the widened offset width is invisible in the
stamp. A reader must therefore discriminate the two forms by exact fit (§11.6, §11.7),
never by `A`. [OBSERVED]

### 11.3.1 The free-slot list

`+0x0C` (W16) / `+0x12` (W32) is **not** a sentinel: it is the head of a singly linked
free list threaded through the offset table itself. A slot is *live* when its value is
`>= n+1` (a byte offset, always `>= w·(n+1)`); a slot is *free* when its value is a slot
index (`< n+1`) — that value is the index of the **next free slot**. The list ends at
`0xFFFF` (W16) / `0xFFFFFFFF` (W32), which is also the value of the head when no slot is
free. The in-memory record keeps this list at `header+0x0E` with the slots at
`header+0x12`, where `header = record + A`; the file keeps it at `+0x0C`/`+0x0E` (W16) or
`+0x12`/`+0x16` (W32), i.e. the on-disk form is the in-memory form shifted by the `A`
descriptor.

The operations, `MSPUB.EXE` 98 (complete: 5 360 functions decompiled):

| VA | Operation |
|---|---|
| `0x004fd6b7` | **allocate one slot**. If the head is `-1` and `count == countDup`, grow first (call `0x004fda56`) and then append: `count++`, `slot[count] = slot[count-1]` (a new empty element). Otherwise pop: `head = slot[head]`, then overwrite the popped slot with the value of the next slot whose value is `>= count` — i.e. the freed element is re-created as a zero-length duplicate of the following element. |
| `0x004fd269` | **shift offsets**. Walks `slot[param_2 … n]` and adds a delta to every slot whose value is `>= count`; free links (`< count`) are left untouched. This is the test that distinguishes the two kinds of slot word. |
| `0x004fd748` | store a value into `slot[param_2]`. |
| `0x004fd0a5` | **element accessor** for the offset-table flavour: `base = rec + *(u8*)(rec+2)`; `off[k] = *(u32*)(base + 0x12 + 4k)`; returns `base + 0x12 + off[k]`, and the element length is `next slot with value >= count` minus `off[k]`. It reads every slot as a `u32`, so a `u16` (Publisher 95) table must have been widened before it reaches this routine. |
| `0x004fcbe9` | **element accessor** for the fixed-element flavour: `base + 10 + elementSize·k`, `elementSize` at `base+4`. |

Corpus identity (493 chunks of `0x001F`; the same test also holds for `0x0026`, `0x0032`,
`0x003A`): every slot word that is not a byte offset lies on exactly one chain starting
at the head, each link is a valid slot index, the chain terminates at `0xFFFF`/
`0xFFFFFFFF`, and the chain covers **all** such words — 51/51 chunks with any free word,
0 exceptions (`0x001F` 51, `0x0026` 36/36, `0x0032` 23/23, `0x003A` 12/12). Worked
examples: `AWARD.PUB` head `1`, chain `1 → 0 → 2 → END` (slots `2, 0, 0xFFFF, 0x0A,
0xC04`); `BRCATALG.PUB` head `0x13`, chain `19 → 18 → … → 1 → END` (the run
`1, 2, … 0x12` that looked like an id list is this chain read backwards).

`0x001E` never has a free slot (head `0xFFFF` 493/493); `0x0023` and `0x002A` do not use
the list at all — their word at `+0x0C` is always `0` while no slot is free (493/493 and
490/490), so a reader must not treat `0` as a head for those two types. [OBSERVED]

## 11.4 Size rules

`n` is `u16@+0x04` unless stated. Every rule is exact over the stated population.

| Marker | Rule | Result |
|---|---|---|
| `0x0016` | `size == 16` | 130/130 |
| `0x001A` | `size == 26 + 14·n` (= header 26 + `u32[n]` + `n`×10, §11.2.1) | 482/482 |
| `0x001C` | `size == 26 + 8·n` | 130/130 |
| `0x002D` | `size == 26 + 8·n` | 130/130 |
| `0x002E` | `size == 26` | 130/130 |
| `0x001E` | `u16@+0x08 == size − 0x0E` (n at `+0x04` duplicated at `+0x06`) | 130/130 |
| `0x001F` | same | 130/130 |
| `0x0023` | same | 130/130 |
| `0x0026` | same | 130/130 |
| `0x002A` | same | 130/130 |
| `0x002B` | same | 30/30 |
| `0x0032` | same | 390/390 |
| `0x0028` | `size == 26 + 5·u16@+0x10` (95/97; Publisher 98 re-frames it, §11.8.1) | 130/130 |
| `0x0029` | `u16@+0x30 == size − 54` | 130/130 |
| `0x0031` | `size == 30 + 8·u16@+0x08` | 390/390 |
| `0x0034` | `size == 46 + 14·u16@+0x24` | 70/70 |
| `0x0035` | `size == 200` | 74/74 |
| `0x0036` | `size == 112` | 1/1 |
| `0x0037` | `size == 14 + 6·n` | 16/16 |
| `0x0038` | `size == 14 + 10·n` | 15/15 |
| `0x0039` | `size == 48` (95/97), 56 (98) | 488/488, 5/5 |
| `0x0027` | `size == 42` | 14/14 |
| `0x003A` | `u32@+0x04 == u32@+0x08`, `u32@+0x0C == size − 0x16`, `size ≥ 0x16 + 4·(n+1)`, `u32@(0x16+4·n) == size − 0x16`, `u16@+0x10 == 1` (`n` = `u32@+0x04`) | 342/342 |
| `0x003B` | `size == 26`, `n == 0`, `u32@+0x0C == 4`, `u32@+0x16 == 4` | 12/12 |
| `0x003F` | `size == 180`, `u32@+0x08 == 1` | 35/35 |
| `0x004E` | `size == 0x14 + 45·n` (`u16@+0x0E == 45`, `+0x0A == +0x0C`) | 2/2 |
| `0x004F` | `size == 0x14 + 11·n` (`u16@+0x0E == 11`, `+0x0A == +0x0C`) | 2/2 |
| `0x0050` | `size == 0x14 + 5·n` (`u16@+0x0E == 5`, `+0x0A == +0x0C`) | 2/2 |
| `0x0052` | `size == 40 + 34·n` (`u16@+0x16 == 0x1E`, `+0x12 == +0x14`) | 5/5 |

The last five rows are measured over the Publisher 98 corpus only; `0x003A`/`0x003B`/
`0x003F` over `p97/x` + `p97deluxe/x`. `0x004E`/`0x004F`/`0x0050` share one header whose
`u16@+0x0E` *is* the element size (§11.11.2) — that field is what makes their element
size measurable at all, since each occurs with only two, differently sized, instances.

## 11.5 Font table `0x001E`

One per document, referenced from `DOCUMENT+0x4A`. The record is an **offset-table
container** whose widths change between generations, so a reader must detect the form by
exact fit rather than by version. Three forms occur; all 487 font tables in the corpus
parse under exactly one of them (487/487, no leftovers): [OBSERVED]

| Form | Corpora | Counts | End offset | Offsets | Name encoding |
|---|---|---|---|---|---|
| V95 | all 128 `p95`, 1 `p97` | `u16` at `+0x04`, dup `+0x06` | `u16` at `+0x08` == `size − 0x0E` | `u16[count+1]` at `+0x0E`, relative to `+0x0E`, first = `2·(count+1)` | ASCII, NUL-terminated |
| V32 | 105 `p97`, 248 `p97deluxe`, 5 `p98` | `u32` at `+0x04`, dup `+0x08` | `u32` at `+0x0C` == `size − 0x16` | `u32[count+1]` at `+0x16`, relative to `+0x16`, first = `4·(count+1)` | ASCII, NUL-terminated |
| V32U | the same 5 `p98` documents | as V32 | as V32 | as V32 | **UTF-16LE**, NUL-terminated (2 bytes) |

V95 also carries `u16 1` at `+0x0A` and `u16 0xFFFF` at `+0x0C`; V32 carries `u16 1` at
`+0x10` and `u32 0xFFFFFFFF` at `+0x12`. Those two constants are the cheapest form
discriminator after the length fields.

Each entry is `{u8 charset, u8 lfPitchAndFamily, name}` — two prefix bytes, no length byte.
Entry *k* runs from `base + off[k]` to `base + off[k+1]`, so contiguity is
`off[k+1] == off[k] + 2 + len(name) + 1` (ASCII) or `+ 2` (UTF-16). Measured: 7 456 entries,
270 distinct faces over the 487 documents.

* `charset` ∈ {`0x00` ANSI, `0x01` DEFAULT, `0x02` SYMBOL, `0xFF`} in 95/97, matching the
  face (`Symbol` and `Wingdings` are `0x02`).
* `lfPitchAndFamily`: low 2 bits pitch, bits 4–6 family — `0x10` ROMAN for `Times New
  Roman`, `0x20` SWISS for `Arial`, `0x30` MODERN for `Courier`, `0x40` SCRIPT for
  `Comic Book`, `0x50` DECORATIVE for `Wingdings`. Bits 2–3 and bit 7 vary between
  documents for the same face and are **not** fields.
* **Publisher 98:** the *second* prefix byte keeps the 95/97 `lfPitchAndFamily` reading
  (measured per face over the 5 documents: `Times New Roman` `0x94`, `Flexure`/
  `Imprint MT Shadow` `0xD4`, `Lucida Handwriting` `0xC4`, `Impact`/`Copperplate Gothic
  Bold` `0xA4`, `Palatino`/`Times` `0x14`, `Symbol` `0x94`; only `Wingdings` moves from
  `0x84`/`0x80` in 95/97 to `0x94`, i.e. the ROMAN bit is added). The *first* byte is
  `lfCharSet` in **every** generation, and its value domain is the Windows charset set:
  `0x00` ANSI, `0x01` DEFAULT, `0x02` SYMBOL, `0xFF` OEM in 95/97, and additionally
  `0xCC` = `RUSSIAN_CHARSET` (204) and `0x4D` = `MAC_CHARSET` (77) in the 5 P98
  publications. The 39 P98 entries carry exactly five first-byte values — `0x00` ×17,
  `0x02` ×10, `0xCC` ×8, `0x01` ×2, `0x4D` ×2. `0xCC` occurs on `Times New Roman`
  (5/5), `Impact` (2/2) and `Book Antiqua` (1/1); `0x4D` occurs on
  `Lucida Handwriting` and `Harrington` in `INFOSHET.JSP` while the **same two faces
  carry `0x00` in `CHEKLIST.JSP`**. The byte is therefore not a property of the face:
  `lfCharSet` is an independent `LOGFONT` member that the author sets per document, so
  two documents may name the same face under different charsets. The earlier readings
  ("`0xCC`/`0x4D` are not Windows charsets", "stale UTF-16 text") are refuted.

  Binary evidence, `MSPUB.EXE` 98. The in-memory font object **is** a `LOGFONTA`:
  `0x00553c5e` returns `memmove(dst, obj, 0x1C)` followed by a 0x40-byte face name, and
  `0x00556f55` / `0x005571aa` hand that pointer straight to `CreateFontIndirectA` /
  `EnumFontFamiliesExA`, so `obj+0x17` is `lfCharSet` and `obj+0x1B` is
  `lfPitchAndFamily`. `0x004ed57b` reads `*(char *)(obj + 0x17)` and branches:
  `0xFF` (OEM) → `GetACP()` then `0x004efd95(codepage, 0)`; `0x01` (DEFAULT) → treated as
  `0x00`; anything else → `0x004efd4c(charset, 0)`, which is
  `TranslateCharsetInfo(charset, &cs, TCI_SRCCHARSET)` and returns
  `cs.fs.fsCsb[0]`. No validation, no case list, no face-name dependency: the byte is
  passed to the Windows charset API verbatim, so any charset value — including
  `0xCC` and `0x4D` — is legal and is reproduced as stored. Reading rule: always treat
  the first byte as `lfCharSet`. [OBSERVED]

Correction to the earlier statement that the table has "no length byte" and a fixed
stride: the stride is `2 + strlen + 1`, and the Publisher 97/98 tables widen every offset
to 32 bits, which is why a fixed-stride walk fails on those corpora.

## 11.6 Border art: `0x001F` and the `.BDR` library

One `0x001F` per document. 87 of the 130 `p95` chunks are the empty 16-byte form, 73 of
the 108 `p97` and 183 of the 250 `p97deluxe` chunks the empty 26-byte form (all 5 `p98`
chunks empty); the rest carry **named border-art styles**. The marker `0x0046` BORDER_ART
of the 2000+ block model does not exist here. [OBSERVED]

### The container: two widths, discriminated by exact fit

`0x001F` is an **offset-table container** in two width forms, and the earlier statement
that the entry prefix "is 2 or 4 bytes, discriminator unknown" is settled by the
container, not by the entry: the offset *slots* are `u16` in Publisher 95 and `u32` in
Publisher 97/98, and the form is detected by exact fit, because `(A, B)` stays
`(0x04, 0x04)` in all 493 instances (there is no A-byte signal). [OBSERVED]

| Form | Counts | Header | Offsets |
|---|---|---|---|
| W16 (Publisher 95) | 130 `p95` + 1 `p97` (43 populated, 87 empty 16-byte in `p95`) | `u16@+0x04` == `u16@+0x06`, `u16@+0x08` == `size − 0x0E` | `u16[n+1]` at `+0x0E`, relative to `+0x0E` |
| W32 (Publisher 97/98) | 107 `p97`, 250 `p97deluxe`, 5 `p98` | `u32@+0x04` == `u32@+0x08`, `u32@+0x0C` == `size − 0x16` | `u32[n+1]` at `+0x16`, relative to `+0x16` |

Every one of the 493 chunks matches exactly one row (0 ambiguous, 0 matching neither).
The slot table is `n+1` slots: the **last slot always equals the end offset** (144/144
populated chunks, all corpora). `n` is a **slot high-water mark, not an entry count**: a
chunk may have far fewer live elements than slots (e.g. `BRCATALG.PUB` `n = 21` with two
entries, `CLASSIC.PUB` `n = 2` with none). The words that are not byte offsets are the
**free-slot list** of §11.3.1: 51 chunks carry one, and in 51/51 the chain from the head
at `+0x0C`/`+0x12` visits exactly the non-offset slots and ends at `0xFFFF`/
`0xFFFFFFFF`. The earlier description of a "prefix block" and of "an id list occupying
consecutive slots" is superseded — `BRCATALG.PUB`'s run `[0x2C, 0xFFFF, 1, 2, … 0x12,
0xC66, 0x1036]` is a free chain `19 → 18 → … → 1 → END` whose head is `0x13`, with only
`0x2C` (entry 0), `0xC66` (entry 1) and `0x1036` (end) being offsets. `AWARD.PUB` is the
other worked shape: head `1`, chain `1 → 0 → 2 → END`, live slots `3` (`0x0A`, the
`Waveline` entry) and `4` (`0xC04`, the end). [OBSERVED]

A slot is therefore addressed by the **border-style index** stored at `+0x31` of the
shape's in-memory record: the renderer does
`FUN_004fd0a5(*(u16 *)(shape + 0x4C), *(u16 *)(shape + 0x31))` — the `0x001F` chunk id
and the style index — and receives the entry pointer (`MSPUB.EXE` 98, caller
`0x0042c3a9`). The reader must apply the same rule: `off[k]` is an entry only when
`k` is not on the free chain.

### The `0x001F` entry

```
+0x00  u16      refCount          live-shape reference count for this style (§11.6.1);
                                  observed {1 ×137, 2 ×9, 3 ×3, 4 ×2, 6 ×1}
+0x02  char[42] nameSlot          NUL-terminated ASCII name; bytes after the NUL are
                                  stale text from a previous longer name
+0x2C  u16      bandTwips         border band width, twips (80, 120, 200, 240, 480, 720 …)
+0x2E  u16      edgeWidthTwips    edge-tile width
+0x30  u16      edgeHeightTwips   edge-tile height
+0x32  u16[8]   tileOffset        byte offsets of the 8 tiles, relative to the entry start
+0x42  …                          the tiles, each a standard memory WMF
```

The earlier reading of `+0x00` — "`1`, or `4` when the entry carries an id list" — is
refuted twice over: no entry carries an id list (the id-looking run in `BRCATALG.PUB` is
the free chain, §11.3.1) and the word is not a discriminator at all — it is the entry's
**reference count**, see §11.6.1. All 152 entries located this way have a
printable NUL-terminated name at `+0x02` (0 exceptions), which is what validates the
parse. The entry prefix is **always two bytes**; it is the offset *slots* that are 2 or 4
bytes wide. Census under the free-list rule (unique entry offsets per chunk): **152
entries in 128 chunks, 45 distinct names, 1 216 tile slots, 1 216/1 216 tiles begin
`01 00 09 00 00 03`** (a `METAHEADER`, type 1, header 9 words, version `0x0300`). This
supersedes the earlier 144 / 139 / 42 / 1 112 figures, which were counted without
skipping the free chain and therefore both over-counted "populated" chunks (a free link
reads as a tiny offset) and under-counted entries (a link in the first slot hides the real
first entry). The eight slots are the border sides
**clockwise from the top-left**: TL, top, TR, right, BR, bottom, BL, left; the offsets are
**not** monotonic and the same tile is often shared by two slots, so a reader must take
each tile's extent from its own WMF header, never from the gap to the next offset.
[OBSERVED]

### 11.6.1 Entry `+0x00` — a live-shape reference count

`+0x00` is the number of shapes that currently use the style. `MSPUB.EXE` 98 VA
`0x00404e77` maintains it through the same entry accessor the renderer uses: it resolves
the shape's *old* border-style index `*(short *)(shape + 0x31)`, and when that index is
not the "no border" sentinel `-2` it does `*entry += -1` — then, after storing the *new*
index into `shape + 0x31`, `*entry += 1` on the new entry (again skipping `-2`). The
earlier "no switch reads it" observation is correct and is *why* it is a count: the accessor
returns the entry pointer and the caller adjusts a counter; nothing ever branches on the
value.

Corpus agreement: every one of the 152 entries carries a value `>= 1` (the census above
has no `0` and no negative word), which is what a writer that decrements on un-apply and
re-increments on apply leaves behind for styles still in use. The value therefore carries
no information a reader needs — it is a runtime refcount persisted by the writer, like the
counters of §11.11.1's `0x0052` records, and a reader must not use it to locate entries.

Worked example — `p95/x/PAGEWIZ/AWARD.PUB` `0x001F` id `0x0101`, size 3 090, W16 with
`n = 4`: slots `(2, 0, 0xFFFF, 0x0A, 0xC04)`, entry 0 at `+0x18` (`refCount` 1, name
`Waveline`), record at `+0x44` = `400, 400, 400` twips, tile offsets
`(66, 476, 816, 1 226, 1 566, 1 976, 2 316, 2 726)`, first tile at `+0x5A`. The same
document in `p97deluxe/x/PageWiz/` is the W32 form: size 3 108, `n = 4`, slots
`(2, 0, 0xFFFFFFFF, 0x14, 0xC0E)`, entry at `+0x2A`, first tile at `+0x6C` — the byte
content of the name/record/tiles is unchanged, only the slot width and the header shift by
8.

### The `PUBBRD/*.BDR` library

The 15 catalogue files on the CD use a different, much simpler container:

```
+0x00  u16  magic     0x5458 ('X','T')
+0x02  u16  version   1   (all 61 copies across the four CDs)
+0x04  u16  count N
+0x06  char[42][N]    name slots, NUL-terminated, stale text after the NUL
+0x06+42N       N × 22-byte records: bandTwips, edgeWidthTwips, edgeHeightTwips, u16[8]
+0x06+42N+22N   22-byte terminator
+…              the payload tiles, concatenated with no gaps
```

`size == 6 + 42·N + 22·(N+1) + Σpayload` holds for 61/61 files; the 22-byte record's
offsets are relative to the record itself, and every payload is a memory WMF (zero
placeable-WMF or BMP payloads in the whole set). [OBSERVED]

**Documents embed, they do not reference.** Of 527 `0x0021` IMAGE_DATA bodies, **zero** are
byte-identical to any `.BDR` payload; but 118 documents carry byte-identical border-art
tiles inside their `0x001F` chunk (900 occurrences, 38 distinct styles), each stored as
name + original `BORDERS\*.BDR` path + a private copy of the tiles. A reader therefore never
needs the CD library to render a document, and a `.BDR` file is a catalogue for the UI, not
a resource the document points at. [OBSERVED]

## 11.7 Design / object sets `0x0031` and `0x0032`

`0x0031` is a direct child of the DOCUMENT and is referenced from `+0x48`, `+0x56` and
`+0x58` (three per document in 487/487). A further 342 documents carry a **fourth**
`0x0031` that is not named by those three slots; 1 461 of the 1 803 instances are the
parent of exactly one `0x0032`. [OBSERVED]

**The fourth instance is the property set: it is referenced from `DOCUMENT+0x6A` and it is
the parent of the `0x003A` arena.** Measured over all 484 documents: the word at `+0x6A`
resolves to a `0x0031` in 342/342 documents that carry four design sets — 95 in `p97` and
247 in `p97deluxe`, which is exactly the split of §11.1.1 — and in the 140 documents where
the word is not a chunk reference at all (128 of them `p95`, where it holds the page index)
it never names a `0x0031`. In all 342, that chunk's only child is a `0x003A`
(`0x3A` ×1, no `0x0032`), i.e. the fourth design set is the one whose arena carries the
per-object property records of §11.12. The earlier note "no `0x0032` child, not referenced
from `+0x48/+0x56/+0x58`" was correct about the child and wrong about the reference: the
reference is the fourth slot, not one of the three. [OBSERVED]

### `0x0031` payload

```
+0x00  u16  0x0031
+0x02  u16  0x0808        stamp (fixed-part length B = 8)
+0x04  u16  0
+0x06  u16  child32Id     id of the 0x0032 child — 1461/1461 of the parents
+0x08  u16  count
+0x0A  u16  count         duplicate
+0x0C  u16  4             element size of each array
+0x0E  u16  arrayOffset   0 in the 30-byte form
+0x10  u32  0
+0x14  u32  0
+0x18  u16  0
+0x1A  u32  0x7FFFFFFF    sentinel
+0x1E  u32[count]         array A: chunk ids, last element 0x7FFFFFFF
+0x1E+4·count  u16[count]{id, value}   array B
```

`size == 30 + 8·count` (1 803/1 803), because the two arrays are `4·count` bytes each.
Array A is a list of the design's object chunk ids; its last element is `0x7FFFFFFF` in all
52 non-empty instances, and the ids it names are `0x000F` GROUP (1 187), `0x0005` RECT
(153), `0x0001` (144), `0x0003` (97), `0x0002` (65), `0x0006` (60), `0x0007` (24),
`0x0000` (16), `0x0004` (3). Array B is `count` `{u16 id, u16 value}` pairs over a
**design-local id space**: the ids must not be relied on as chunk ids. In 21 of the 52
populated instances none of them resolves at all, and in `CLASSIC.PUB`'s 52-pair instance
18 of the 52 do not. Where they do resolve they are a mix — some are ids array A also
lists, others are object chunks outside A (31/52 populated instances have at least one
resolving id that A does not list) — so the two arrays address the same object set under
different conventions and only array A is a clean chunk-id list. [OBSERVED]

**The `value` is an index into the design's own `0x0032` name table.** Over the 40
populated instances that have a `0x0032` child, every value is `<` that child's `count`
(40/40, no exception), the values are pairwise distinct (40/40), and when the design's
`count` equals the name count the multiset is exactly `0 … count−1` (`CLASSIC.PUB`
id `0x0105`: 52 pairs, 52 names, a permutation of 0…51; `79` pairs against `80` names
leaves exactly one name unreferenced). The pair list is therefore the object → name map of
the design: the `id` names the object, the `value` selects its entry in the `0x0032`
name table of §11.7. The earlier "value domain 0…45, meaning unknown" reading was a
domain scan without the partner table; the upper bound is the name count, not 45.
[OBSERVED]

Worked example — `p95/x/PAGEWIZ/CLASSIC.PUB` id `0x0105`, 446 bytes, count 52:

```
+0x06 = 0x0106   the 0x0032 child
+0x1E = 0x010A 0x0115 0x0123 0x012B 0x013F … 0x0727 0x7FFFFFFF
```

### `0x0032` payload — the name table

Same container family as §11.3, with the same two width forms:

| Form | Counts | End offset | Offsets | Entries |
|---|---|---|---|---|
| L1 (u16) | `u16` at `+0x04`, dup `+0x06` | `u16` at `+0x08` == `size − 0x0E` | `u16[count+1]` at `+0x0E`, first = `2·(count+1)` | ASCII names |
| L2 (u32) | `u32` at `+0x04`, dup `+0x08` | `u32` at `+0x0C` == `size − 0x16` | `u32[count+1]` at `+0x16`, first = `4·(count+1)` | ASCII names |

Measured: 387 L1 (all in `p95` plus 3 `p97`), 1 070 L2 (all `p97`/`p97deluxe`/`p98`). The
4 L2 instances in `p97/x/JAZZY.PUB` and `PLAIN.PUB` whose offset array is not monotone are
**not a writer variant**: they are ordinary offset tables whose free-slot list (§11.3.1) is
non-empty, and `offs[0] = 5` is the *first slot being free*. Measured on those 4:

| File | Chunk | `n` | head `+0x12` | chain |
|---|---|---|---|---|
| `JAZZY.PUB` | `0x0106` (id 262) | 80 | 78 | `78 → END` (`slot 78 = 0xFFFFFFFF`) |
| `JAZZY.PUB` | `0x0104` (id 260) | 24 | 0 | `0 → 5 → 7 → END` (`offs[0] = 5`) |
| `PLAIN.PUB` | `0x0106` (id 262) | 88 | 82 | `82 → END` |
| `PLAIN.PUB` | `0x0104` (id 260) | 35 | 27 | `27 → 28 → 26 → 0 → 25 → END` |

So the table is **allowed** to start with a free link and the parse is not off by one
field: `offs[0]` is an offset only in a chunk whose head chain does not visit slot 0. A
reader must drop the free slots and take the entries from the remaining slot values, exactly
as for `0x001F` and `0x003A`. `tools/validate.py` now enforces the chain for every `0x0032`
instance (`freelist_0x32_chain`: 1 479/1 479 chunks over the four CDs satisfy it, 23 of them
with a non-empty free list). [OBSERVED]

1 455 names total. The names are the design's object names (`Titles`, `Corner`,
`Pinstripes`, `Table of Contents`, …), and `count` matches the `0x0031` count that owns them.

Worked example — `p95/x/PAGEWIZ/CLASSIC.PUB` id `0x0106`, 589 bytes, count 52, L1:
`+0x08 = 0x023F = 575 = 589 − 14`, offsets `0x6A, 0x70, 0x77, … 0x023F`, first string at
`+0x0E + 0x6A = 0x78` = `"Title\0"`, next at `0x7E` = `"Column\0"`.

The three slots correspond to the three design sets every Publisher template is built on;
the naming is `[INFERENCE]`, the structure is `[OBSERVED]`.

## 11.8 Records `0x0028`, `0x0029`, `0x0036`

* `0x0028` — the six fixed application codes are a **key→font table**, not print parameters
  (§11.8.1). In short: the six keys live as a 30-byte constant table in the executable, each
  key's dictionary index is the `u16` array at `+0x04`, and each key's `value` is the index
  of the `Symbol` entry in the document's `0x001E` font table.
* `0x0029` — print setup. Four EMU margins at `+0x16`, page width/height at `+0x48`/`+0x4C`
  (equal to the DOCUMENT's, 130/130), DEVMODE `dmPaperSize` at `+0x50`, then device, driver
  and port as NUL-terminated strings whose cumulative ends are the four `u16` at
  `+0x3E…+0x44`. Contains **no timestamps**.
* `0x0036` — a fixed 112-byte record whose **parent is the `0x0029` print-setup record**
  (not the DOCUMENT), one instance in the entire corpus (`CHEKLIST.JSP`), byte-identical
  across all four CD revisions. Its `(A,B)` stamp is `0x7070`, i.e. `A = B = 112 = size` —
  the same self-describing stamp `0x003F` uses. Only five fields are non-zero: `+0x10` `1`,
  `+0x12` `4`, `+0x1E` `1`, `+0x6A` `2`, `+0x6E` `0x46`; everything else is zero, so there is
  almost no payload to identify. No module reads it: the stamp `0x7070` never appears as an
  immediate in `MSPUB.EXE` 98 (5 360 functions), 97 (4 252) or 95 (3 293), and the record is
  reached only through its parent's child list (§11.8.2).

### 11.8.1 `0x0028` — six fixed keys, a key→font table

```
+0x00 u16 0x0028
+0x02 u16 0x1010          A = B = 0x10, the count offset
+0x04 u16[6]              per-key dictionary index (§11.3.1's free list is unused here)
+0x10 u16 n               n >= 6; duplicate at +0x12
+0x14 u16 5               element size
+0x16 u16 1
+0x18 u16 0xFFFF
+0x1A n × 5              {u16 key, u8 0, u16 value}
```

`n == (size − 26) / 5` holds for every 95/97 instance (479/479); 422 of those are the
minimum `n = 6` (56 bytes). The five Publisher 98 records are re-framed (§11.8.1, last
paragraph). The record order is **not** ascending by key: `MSPUB.PUB` stores the six in the
order `0x14B7, 0x18B7, 0x14A8, 0x14DE, 0x14E0, 0x142A`, `BMEMO1.PUB` the exact reverse.

**The 5-byte record is `{u16 key, u8 0, u16 value}` — the value sits at `+0x03`, not
`+0x02`.** The disassembly of the builder settles it: it copies four bytes of the table
entry, then stores the computed `u16` at struct offset 3 (`MSPUB.EXE` 95 VA `0x0044de79`,
`mov [esp+0x1b], bp` with the struct at `+0x18`). Read as `u16` at `+0x02` the field is
`0x0100`/`0x0200` and looks like a flag; read at `+0x03` it is `1`/`2`, which is what the
code produces and what the `Symbol`-index correlation below needs.

**The six keys are compile-time constants.** `MSPUB.EXE` 95 keeps them as a 30-byte table
in `.rdata` at VA `0x593FA0` (`b7 14 00 01 00 | b7 18 00 01 00 | a8 14 00 01 00 |
de 14 00 01 00 | e0 14 00 01 00 | 2a 14 00 01 00`) — the whole default payload, with the
value byte equal to `1`. The walker is VA `0x0044de44`: it loads `0x593FA0` into a register,
copies the four-byte head plus the fifth byte into a stack record, calls the key lookup
`0x0044df14`, stores the returned byte into a six-`u16` array of its argument, and advances
the pointer by 5 while it is `< 0x593FBE` — i.e. exactly six iterations. Nothing compares
the keys to anything, so this is a **table walk, not a switch**: the six are table rows,
which is why they can never be chunk ids (all six exceed `0x087D`, the largest chunk id in
the corpus).

**The `u16[6]` at `+0x04` is the per-key dictionary index.** The lookup `0x0044df14`
delegates to `0x0044debc`, which walks a per-document list of 5-byte keys (entry `k` from
`0x00401717`), compares the 5 bytes byte-for-byte, and returns `k`; on a miss it appends
the key (`0x00405f4c`) and returns the new `k`. `0x0044df14` then adds 10 to that index and
returns it, and the builder stores it as a `u16` at `entry + 4 + 2k` (`0x0044de9f`). Corpus:
the array's values are `10 … 0x31`, and the six keys of `MSPUB.PUB` get `0x0A … 0x0F` —
indices 0…5.

**The `value` is the document's `Symbol` font index.** The second operand of the same
builder is `0x00440822`, which calls `0x0044086b(fontTableId, "Symbol", 0x50, 2, 2)`; that
routine searches the document's `0x001E` table for an entry with a matching size stamp and
the name `Symbol`, appends one when absent, and returns its index (0 when
`CreateFontA` fails). `0x00440822`'s return is what lands in the record's `+0x03`.
Corpus: all six records of one document carry the same value (each of the six keys shows the
same 293/158 split between `2` and `1`), the domain over the corpus is `0 … 9` with `2`
×279 and `1` ×158, and of the 130 documents whose font table actually carries a `Symbol`
face the value equals that face's index in 123 (the 7 exceptions and the 354 documents with
no `Symbol` entry carry a persisted session index — the face is compacted away on save, the
same staleness the `0x0052` pointers show). A reader must therefore treat this as a
write-side index, not a reference. [OBSERVED]

**Publisher 98 spells the answer out.** The same six keys are written as 20-byte records
`{u32 key-low-byte, u16 0x4120, UTF-16LE face name}`: `p98/x/MSPUB.PUB`'s 194-byte
`0x0028` holds `0xB7, 0xB7, 0xA8, 0xDE, 0xE0, 0x2A` followed by `Symbol\0` six times
(offsets `0x4A, 0x5E, 0x72, 0x86, 0x9A, 0xAE`), plus the six `u32` indices `0…5` at
`+0x04` — the 95/97 `+10` bias is gone. So each of the six keys selects **a font slot**, and
in every shipped publication all six resolve to `Symbol`. [OBSERVED]

**The consumer reads the keys, not the records.** `MSPUB.EXE` 95 VA `0x004cf710` (case 10 of
a character-format loader) takes a 5-byte key out of a text-run record and calls
`0x0044df14(DOCUMENT->+0x06, &key)`, storing the returned byte at `+0x1E` of the run
format. That is the same lookup the builder uses, against the same chunk, so the chunk is a
per-document **key dictionary** and the six fixed rows are its permanent members.

### 11.8.2 `0x0036` — a child of the print-setup record

`0x0036`'s only instance has `parent = 0x010c`, which is the document's `0x0029` print-setup
record (`p95/x/CHEKLIST.JSP`), so the earlier "document-level companion" framing is wrong:
it is a sub-record of `0x0029`. The payload is `36 00 | 70 70 |` then zeros with five
exceptions, listed above.

**Closed as opaque.** The record is never read and never written by any shipped binary:
the scan covers `MSPUB.EXE` 95/97/98, `QS98.DLL`, `PUBDLG.DLL`, `MSPUBW32.DLL`,
`PUBOLE32.DLL` and `PUB3STP.DLL` (12 905 functions), none of which mentions the `0x7070`
stamp or dispatches on the marker; it is carried through the chunk copy untouched. A reader
must therefore preserve the 112 bytes verbatim. The field *meanings* are not recoverable
from the shipped code — that is the finding, not an open question. `[OBSERVED]`

## 11.9 The `A` byte

`A` is a structural landmark, not a length. It equals the byte offset of the record's
primary count field in 15 of 21 container types (`0x001A`/`0x001C`/`0x001F`/`0x0023`/
`0x0026`/`0x002A`/`0x002B`/`0x002D`/`0x002E`/`0x0032`/`0x0037`/`0x0038` → 4; `0x0031` → 8;
`0x0028` → 0x10; `0x0034` → 0x24). Exceptions: `0x001E` (A = 8, count at `+0x04`), `0x002C`
(A = 0x18, counts at `+0x14`), `0x0029` (A = 0x2C, no count), `0x0027` (A = 0x16, a string
offset), `0x0035` (A = 0xC8, the chunk size), `0x0039` (A = 0x4C). [OBSERVED]

## 11.10 Colour lists `0x0037` / `0x0038`

`0x0037` (16 documents) uses 6-byte elements: `RR GG BB 20 flag`. The triple is unambiguous;
the `0x20` tag byte is the literal-RGB tag of chapter 09, and the trailing flag takes
{0,1,2,8,9,0x18}. `[INFERENCE]`: a document-level custom-colour list. `0x0038` is the same
container with the element size word set to 10, and it is **declared but never populated by
any shipped build**: all 145 instances over 601 documents are the 14-byte empty form
(§11.10.1).

Population measured over all 487 documents: `0x0037` — 183 instances, count 0 in 129, 1 in
48, 2 in 5, 5 in 1, always `size == 14 + 6·count`; `0x0038` — 127 instances, **all 14 bytes
with count 0**. [OBSERVED]

### 11.10.1 `0x0038` — declared, never populated

Widening the population to every document on the four CDs (601 files, 484 of them unique
documents) gives 145 `0x0038` instances and **no populated one**: every instance is exactly
14 bytes, `count == 0` at `+0x04`/`+0x06`, and `u16@+0x08 == 10`, i.e. the header of the
fixed-element flavour (§11.3) with an element size and an empty array. The pair therefore
shares one writer: it emits the 14-byte header for both markers and only the size word
differs — `0x0037` is exercised (54 populated instances) and `0x0038` is not.

There is no fill loop to find. The blocking fact is not "the corpus is too small" but that
the element size is a **declared constant with no producer**: no function in the complete
decompiled trees of `MSPUB.EXE` 98 (5 360 functions), 97 (4 252), 95 (3 293) or `QS98.DLL`
(2 104) stores to the `count` word of a `0x0038` record, and the marker appears in none of
them in a chunk-type dispatch (the `case 0x38` sites in the 98 build are command IDs
paired with `0xa7`/`0xa9`, not chunk types). A reader must therefore treat a non-zero count
as impossible in these generations and must not try to decode a 10-byte element; the record
is `[UNKNOWN]` by construction, not by missing evidence. [OBSERVED, negative]

`tools/validate.py` enforces the empty form for every `0x0038` (`rec_0x38_empty`): 14 bytes,
count 0, element size 10 — so a future instance with a payload fails loudly instead of
being silently misparsed.

## 11.11 Publisher-98-only document records

Six markers occur in the Publisher 98 publications and nowhere else. All six are now
framed; the remaining unknowns are field semantics, listed in §11.13. All are direct
children of the DOCUMENT except `0x004C`/`0x0052`, which hang off `0x0045`. [OBSERVED, 5 documents]

| Marker | Size | Layout |
|---|---|---|
| `0x0040` | 28, fixed | `u16 0x0202` at `+0x04`, zeros elsewhere; 4 instances, byte-identical |
| `0x0041` | 40, fixed | **a page slot**, not a distinct feature — see below |
| `0x0045` | 8, fixed | `u16 id of the 0x004C chunk` at `+0x04`, `u16 id of the 0x0052 chunk` at `+0x06`; 5/5 |
| `0x0043` | 20 + 2·N | `N` at `+0x0A`, duplicate `+0x0C`; `N` `u16` chunk ids from `+0x14`. The ids are the top-level objects of every page except the first (the shape-gallery page), excluding `0x002C` — set-equal 5/5 |
| `0x004C` | 40 + 6·N | `N` at `+0x12`, duplicate `+0x14`; `N` `u32` 16.16 values at `+0x24`, sentinel `0x7FFFFFFF` at `+0x24+4N` (10/10 across both markers), then `N` `u16` ids at `+0x28+4N` — **109/109 ids resolve** to real chunks. Maps an id to a shape; the values equal the `u32` at `0x0008+0x58` |
| `0x0052` | 40 + 34·N | `N` at `+0x12`, duplicate `+0x14`; `u16 0x001E` (record size) at `+0x16`; `N` sorted unique `u32` keys at `+0x24`, sentinel `0x7FFFFFFF` at `+0x24+4N` (5/5), then `N` × 30-byte records — see below |

Two further markers, `0x004E`/`0x004F`/`0x0050`, are Publisher-98-only and occur in
`CHEKLIST.JSP` alone; they share one header (§11.11.2).

### 11.11.1 `0x0052` payload — per-shape metadata with persisted pointers

`0x0052` hangs off `0x0045`, one per document, and is populated in 3 of the 5 P98
publications (110 records; `MSPUB.PUB`/`ZMSPUB.PUB` carry the empty 40-byte form). [OBSERVED]

```
+0x00 u16 0x0052
+0x02 u16 0x1212
+0x04 u32 0                 three zero dwords through +0x0F (5/5)
+0x10 u16 0
+0x12 u16 N                 duplicate at +0x14
+0x16 u16 0x001E            record size (30)
+0x18 u16 state             0 / 2 / 9, per document
+0x1A u32 0
+0x1E u32 0
+0x22 u16 0
+0x24 u32[N] keys           strictly ascending and distinct (5/5)
+0x24+4N    u32 0x7FFFFFFF  sentinel (5/5)
+0x28+4N    N × 30-byte records
```

The 30-byte record (110/110 of the shape):

| Offset | Width | Field | Observed |
|---|---|---|---|
| `+0x00` | u32 | tag | `1` in 109, `2` in the `INFOSHET.JSP` record |
| `+0x04` | u32 | ordinal | 1 … 114, never equal to the chunk-id space |
| `+0x08` | u32 | ptrA | absolute address in one per-document heap range (`0x3177xxxx` for `CHEKLIST.JSP`, `0x0286xxxx`/`0x0288xxxx` for `CLRCHK.JSP`/`INFOSHET.JSP`) |
| `+0x0C` | u32 | ptrB | same range (`ptrB > ptrA` in 103/110, `<` in 7) |
| `+0x10` | u16 | flags | `0x10` ×107, `0x40` ×2, `0x50` ×1 |
| `+0x12` | f32 | const | `0xCB18967C` = −9 999 996.0, 110/110 |
| `+0x16` | f32 | const | `0xCB18967C` = −9 999 996.0, 110/110 |
| `+0x1A` | f32 | value | `18.0` ×16 (the two documents whose flags include `0x40`/`0x50`), `0.0` ×94 |

What the record provably is **not** [OBSERVED]:

* not a chunk-id map — 0 of the 110 keys and 0 of the 110 ordinals resolve to a chunk id
  in their own document;
* not offsets/lengths — `ptrA`/`ptrB` are 3–4 orders of magnitude larger than the chunk
  (`0x0286_3DD4` … `0x3177_8430` against a 550-byte chunk and a ≤ 4 MB document) and they
  differ per document while the record count does not, so they are **persisted pointer
  values**, not chunk-relative data (`[INFERENCE]`: heap addresses leaked into the file by
  the writer — a reader must ignore them);
* not geometry — the two `−9 999 996.0` words are bit-identical in every record and are a
  sentinel for "unset", not a coordinate.

The keys are shape ordinals: on all 3 populated documents the key set is a superset of
`{v >> 16}` of the `0x004C` value array (15 ⊇ {1,4,5,…}, 94 ⊇ {5,7,8,…}, 1 ⊇ {1}), i.e.
the same 16.16 ordinal scale. Both arrays are emitted in ascending order and are
positionally aligned: in 3/3 populated documents `keys[k]` is the key of record `k`
(keys strictly ascending, records in the same order). The `+0x04` word is a **separate
ascending sequence number** — unique within the document, spanning 1…114 for 110 records
(1…20 for 15, 3…114 for 94, 1 for 1), with gaps — not a key and not a chunk id.

**Nothing reads this record.** Scan scope: `MSPUB.EXE` 98 (all 5 360 functions
decompiled), `MSPUB.EXE` 97 (4 252), `MSPUB.EXE` 95 (3 293) and `QS98.DLL` (2 104); the
only 30-byte-stride array walker in any of them is the P95/P97 *in-memory* append at
`0x0058f20b` (97) / `0x00575043` (95), `*(int *)(index * 0x1E + 0x2A + obj)` with the
index at `obj+0xB4`, and it is absent from the 98 build (no `* 0x1E` anywhere in
`notes/p98/decomp98`). No function in the 98 build computes the `+0x28 + 4·N` record base
of this chunk, and none reads `0xCB18967C` from a file record — the only two uses of
`−9 999 996.0` (`0x004eab08`, `0x0051c0cd`) pass it as a *limit argument* to a virtual
drawing method at vtable `+0x80`, i.e. the sentinel is regenerated at runtime, never
loaded. The record is reached only through the `0x0045` object: that record is
materialised as a C++ object whose in-memory form has a vtable pointer at `+0x14`
(`MSPUB.EXE` 98 VA `0x005b51d5`, `**(code **)(*obj + 0xF0)(obj)`), so its file `+0x06`
(which names this chunk) is consumed by a constructor, not by a byte-offset reader.
`MSPUB.M14`, the only other candidate module, is not a PE (`3f 5f 03 00`) and cannot be
imported by Ghidra. The `0x0052` payload is therefore a **writer-side dump of a live
in-memory table** whose pointers are not re-read: a reader must skip it. [OBSERVED for
the negative and the scan scope; INFERENCE for "dump of a live table", supported by
`ptrA`/`ptrB` lying in one per-document heap range]

### 11.11.2 `0x004E` / `0x004F` / `0x0050` — print/checklist sub-records

All three are children of a `0x000A` shape in `CHEKLIST.JSP` (2 instances each: ids
`0x0150`/`0x0153` (`0x004E`), `0x0128`/`0x0156` (`0x004F`), `0x0111`/`0x0129` (`0x0050`))
and occur nowhere else in the 493 documents. They share one header, and it carries the
element size — which is why the size rule is exact even though each marker has only two,
differently sized, instances: [OBSERVED]

```
+0x00 u16 marker
+0x02 u16 0x0A0A
+0x04 u32 0           6/6
+0x08 u16 0           6/6
+0x0A u16 n           duplicate at +0x0C (6/6)
+0x0E u16 elementSize 45 / 11 / 5 by marker
+0x10 u16 field       1 in the two `0x004E` records, 0 in `0x004F`/`0x0050`
+0x12 u16 field       0 in five records, 2 in `0x004E` id `0x0153`
+0x14 ...             n × elementSize
```

`size == 0x14 + elementSize·n` in 6/6 instances:

| Marker | elementSize | Instances (size, n) | Elements |
|---|---|---|---|
| `0x004E` | 45 | 2 × (290, 6) | 6 × 45-byte records; element 0 is a prologue block (`FF FF`, a `u16 1` and four `0x39` words), elements 1–5 carry a leading `u16` in {0x40,0x50,0x60,0x70} (or 0 when empty) and repeated `0xC0E4` marker words |
| `0x004F` | 11 | (306, 26), (207, 17) | `{u16 kind ∈ 1…5, u16 row, u16 col, u8 pad == 0, u32 value}` — 43/43 elements; `row`/`col` are byte-doubled ordinals (`0x0101`, `0x0202` …, `0x0201` once) and `value` ∈ {`0x711BF`, `0x25350`, `0x37CF8`, `0x394C7`, `0x5E817`, `0x882D8`, `0x83B67`, `0xA8EB7`}, i.e. EMU coordinates in the 0.17…0.76 in range |
| `0x0050` | 5 | (155, 27), (110, 18) | `{u16 id, u16 id, u8 flag}` — 45/45 elements with both id words equal; `flag` is 0 except the final two elements, which repeat the last id with flag 2 then 1 |

**How the array is addressed.** The header is an `A`-descriptor container with `A = 10`
(the `0x0A0A` stamp), and the accessor is `MSPUB.EXE` 98 VA `0x004fcbe9`:
`base = rec + A`, `elementSize = *(short *)(base + 4)`, element `k` at
`base + 10 + elementSize·k`. That is exactly `+0x0E` (element size) and `+0x14` (array)
of the file, which is why the size rule is exact. The `0x004E` array is **not indexed by
position**: VA `0x004e279f` takes the first `u16` of each `0x004F` element as the index
(`*(char *)(kind * 0x2D + 10 + array0x004E)`) and tests byte `+0x0A` of that 45-byte
element — so `0x004F.kind ∈ 1…5` is a **format index into the five `0x004E` elements
1…5** (element 0 is the prologue and is never addressed), not a row/column.

**The 45-byte element** is a cell/box format record. Its width fields are decoded: bytes
`+0x14`, `+0x1A`, `+0x20`, `+0x26` are each passed to VA `0x004547f1`, which converts the
byte to EMU as `b * 0x319C` (12 700 EMU = 1 pt) for `b < 0x80`, a 1/3-pt fractional form
for `b ≥ 0x81`, and `0` for `0xFF` — i.e. four **line widths in points** (the four sides
of a cell). All four are `0` in both `0x004E` instances, so the widths are unexercised.
`[OBSERVED for the accessor, the index relation and the widths]`

Each side's colour travels with its width. VA `0x0050c3cb` strokes one cell side at a
time: for side 1 it passes `u32@+0x13` and `u16@+0x17` to the pen setter VA `0x0050d4e0`,
for side 2 `u32@+0x19` / `u16@+0x1D`, for side 3 `u32@+0x1F` / `u16@+0x23`, for side 4
`u32@+0x25` / `u16@+0x29` — each pair adjacent to that side's width byte — and
`0x0050d4e0` forwards both words to VA `0x004298b3` before stroking the side's rectangle
with the GDI `Rectangle` primitive (VA `0x0041de97`). A side whose width byte is `0`
takes the no-stroke path instead. So each 45-byte element holds four
`{u32 colour, u8 width, u16 colour-ext}` side slots at `+0x13`/`+0x19`/`+0x1F`/`+0x25`
(widths at `+0x14`/`+0x1A`/`+0x20`/`+0x26`), and in both shipped instances every colour
word is either `0` or the unset-colour sentinel `0xC0E4…` that VA `0x0040402e` writes
(chapter 06 §6.3) — the checklist cells carry no side colour. `[OBSERVED: the four
colour pairs are live arguments of the stroke path, not merely stored words]`

What remains opaque is the head of the element — the leading `u16`
(`0x40`/`0x50`/`0x60`/`0x70` across elements 1–5, `0xFFFF` in the prologue, `0` in an
empty element), the `u32@+0x04` / `u16@+0x08` words, the `+0x0B…+0x12` run and the
trailing `u16@+0x2B` (1…15 over the corpus) — and byte `+0x0A` beyond its one test: VA
`0x004e279f` returns nonzero when some kind-addressed element has `+0x0A == 0`, and its
callers (`0x004e2823`, `0x004e3209`) use the result as a table-shape predicate. No
function in `MSPUB.EXE` 98 (5 360 functions), 97 (4 252), 95 (3 826) or `QS98.DLL`
(2 104) reads any of those head/trailer words. They are therefore **proven opaque**:
a reader must preserve the 45 bytes verbatim; only the four side slots have a consumer.
`[OBSERVED for the boolean test and the scan scope]`

### `0x0041` is a page slot

`0x0041` is byte-identical to a 40-byte Publisher 98 PAGE (`0x0014`) except for two fields:

```
PAGE 0x14:  14 00 1e 1e 00 00 00 00 00 00 00 00 e0 d0 5c 01 e0 d0 5c 01 …
0x41:       41 00 1e 1e 00 00 00 00 00 00 00 00 e0 d0 5c 01 e0 d0 5c 01 …
                                            +0x22:  02 00 (PAGE)  /  08 00 (slot)
```

So `0x0041` is a page record whose `+0x22` slot kind is `8` instead of `2`. It carries the
same 40-byte framing (`B = 0x1E`, count at `+0x1E`, duplicate `+0x20`, array at `+0x28`).
The document's page count therefore includes `0x0041` records: `p98/x/MSPUB.PUB` has six
`0x0014` and one `0x0041`, which is the seven pages that make the DOCUMENT size rule of
chapter 04 §4.1 balance. [OBSERVED]

The 40-byte PAGE form, for reference:

| Offset | Width | Field | Observed |
|---|---|---|---|
| `+0x00` | u16 | marker | `0x0014` or `0x0041` |
| `+0x02` | u16 | stamp | `0x1E1E` |
| `+0x04` | u32 | 0 | — |
| `+0x08` | u32 | 0 | — |
| `+0x0C` | u32 | build stamp | `0x015CD0E0` in 4 of 5 publications, different in `ZMSPUB.PUB` |
| `+0x10` | u32 | same as `+0x0C` | — |
| `+0x14` | u32 | 0 | — |
| `+0x18` | u32 | 0 | — |
| `+0x1C` | u16 | 0 | — |
| `+0x1E` | u16 | count | page-child count |
| `+0x20` | u16 | count | duplicate |
| `+0x22` | u16 | slot kind | `2` = page, `8` = page slot |
| `+0x24` | u32 | 0 | — |
| `+0x28` | u16[count] | child ids | — |

## 11.12 Publisher 97-era records

Four markers occur in the Publisher 97 corpora and in neither 95 nor 98. All have exact
size rules; `0x003A` and `0x003F` are now mapped. [OBSERVED]

| Marker | Instances | Size | Parent | Framing |
|---|---|---|---|---|
| `0x002F` | 12 | 38, fixed | `0x0016` story container | `+0x04 u16 2`, **`+0x06` = the id of its `0x003B` child (12/12)**, `+0x08`/`+0x0A` `1`, `+0x0C` `4`, `+0x0E` `1` or `2`, `+0x10` a small signed value (0, −23, −102, −425), `+0x12 … +0x1C` zero, `+0x1E` not a chunk id (6 770 … 7 829 in the PageWiz files), `+0x20`/`+0x22` `0`/`0xFFFF`; interior opaque — no consumer in 12 905 functions, preserved verbatim |
| `0x003A` | 342 (95 `p97`, 247 `p97deluxe`) | 26 … 1 014 | `0x0031` design set, 342/342 | u32 container: `u32@+0x04 == u32@+0x08` (slot high-water mark), `u32@+0x0C == size − 0x16` (end), `u16 1` at `+0x10`, the free-slot-list head at `+0x12` (`0xFFFFFFFF` = empty, in all 330 empty records; a slot index 6…56 in the 12 populated), `u32[n+1]` slots at `+0x16` with slot *n* == end — **all 342, the 12 populated included**; the slots index a record arena (below) |
| `0x003B` | 12 | 26, fixed | `0x002F`, 12/12 | one byte body, 12/12: `3b 00 04 04  00000000 00000000 04000000 0100 ffffffff 04000000` |
| `0x003F` | 35 | 180, fixed | `0x0015` document, 35/35 | label/label-sheet template record — full map below |

**`0x002F`'s consumer.** The record is a story-container child, and its only pointer-shaped
field (`+0x06`) is the link to its own `0x003B` child, proven on all 12 instances (for
`CLASSIC.PUB` the `0x002F` at id `0x021E` names `0x021A`, which is its 26-byte `0x003B`;
`MODERN.PUB` names `0x0588`, `plain_cd.pub` names `0x0238`). Nothing else in the record is a
reference: `+0x1E` is not a chunk id in 11 of the 12 (it is 2 001, 6 770, 6 847, 7 110,
7 829 in the PageWiz files) and `+0x10` is a signed value. No consumer was located. Scan
scope: the
complete decompiled trees of `MSPUB.EXE` 98 (5 360 functions), 97 (4 252), 95 (3 293) and
`QS98.DLL` (2 104) contain no chunk-type dispatch case for `0x2F` — the `case 0x2f` blocks
found (`MSPUB.EXE` 95 VA `0x00572fcb`) belong to a style-property copier whose switch
variable is a property id in 4…0x194, not a marker — and the pair occurs only in the four
PageWiz templates of `p97/x` and `p97deluxe/x` (present in neither `p95` nor `p98`). The
record is therefore **read-only evidence of a writer state**, not a reference a reader must
follow. [OBSERVED, negative]

The 26-byte empty form shared by `0x003A`/`0x003B` is the same container shape as the
`0x0032` L2 form (§11.7) — count, duplicate, end offset, `u16 1`, `u32 0xFFFFFFFF`, one
`u32` slot — which is why the pair is grouped here rather than with the fixed records.
The two empty bodies are byte-identical apart from the marker (`3a`/`3b`): 330/330 and
12/12 respectively. [OBSERVED]

**Correction.** The previous revision claimed the 12 populated `0x003A` instances "do not
follow" the container rule. They do: `u32@+0x0C == size − 0x16` and slot *n* == end hold
12/12 (and 342/342 with the empty form). The earlier failure came from comparing against
`size − 0x0E`.

### `0x003A` payload — an arena of records behind a slot table

```
+0x00 u16 0x003A
+0x02 u16 0x0404
+0x04 u32 nSlots              duplicate at +0x08; a SLOT HIGH-WATER MARK, not an entry count
+0x0C u32 end                 == size − 0x16
+0x10 u16 1
+0x12 u32 freeHead            free-slot-list head (§11.3.1); 0xFFFFFFFF = list empty
+0x16 u32[n+1] slots          relative to +0x16; slot n == end; the table ends at
                              0x16 + 4·(n+1), where the arena begins
      arena: records at the slot targets
```

The slots are the mixed table of §11.3.1: a slot value `>= n+1` is an offset to a record
in the arena, a value `< n+1` is the next link of the free list, and the list starts at
`+0x12` and ends at `0xFFFFFFFF`. The corpus confirms the chain on 12/12 populated
instances (all non-offset words on one chain from the head, 0 exceptions). The `+0x12`
word that earlier revisions called "headerWord / pointer to the index block" is that
head: `CLASSIC.PUB` has head `0x1B` with chain `27 → 12 → 29 → 21 → 20 → 28 → 19 → 18 →
7 → 0 → 8 → END` and 23 live slots. The record at a slot target is length-prefixed:

```
+0x00 u16 0                 reserved
+0x02 u32 length            whole record length, header included
+0x06 u32 type              property type (see below)
+0x0A u8[length−10] payload
```

Measured over the 12 populated instances (8 distinct documents — `CLASSIC`, `JAZZY`,
`MODERN` and `PLAIN` are byte-identical duplicates between `p97/x` and
`p97deluxe/x/PageWiz`): 289 slot-referenced records, **289/289 `u16@+0 == 0`**, and
exactly two `type` values:

| `+0x06` | count | `length` | payload |
|---|---|---|---|
| `1` | 288 | 14 | one `u32` ∈ {0 ×93, 1 ×99, 2 ×96} |
| `4` | 1 | 29 | NUL-terminated string, `"Your Email Address\0"` |

`type` 1 carries a fixed 4-byte number and `type` 4 a NUL-terminated string; the two
observed types coincide with the `MsoPropertyType` numbering (`msoPropertyTypeNumber =
1`, `msoPropertyTypeString = 4`) — `[INFERENCE]`, the domain is what is observed.

**The arena is one record per `0x0031` array-A element** (12/12): the arena record count
equals `u16@+0x08` of the parent `0x0031` design set (the array-A count) in every populated
instance — `CLASSIC` 22, `JAZZY` 18, `MODERN` 26, `PLAIN` 11, `class_cd` 18, `jazzy_cd`
42, `modrn_cd` 35, `plain_cd` 40 — and array A's last element is the `0x7FFFFFFF`
sentinel, so record *k* describes array-A element *k*. `[OBSERVED]`

The earlier "1-byte residue" anomaly in `p97deluxe/x/PageWiz/plain_cd.pub` is explained
and does not exist: that record has `n = 101` slots (41 live) and an arena of
`40 × 14 + 1 × 29 = 575` bytes, exactly the record array including its single `type`-4
string record. The slot table is `4·(n+1) = 408` bytes as everywhere else.

### `0x003F` payload — a label-sheet template

```
+0x00 u16 0x003F
+0x02 u16 0xB4B4               the (A,B) stamp, A = B = 0xB4 = 180 = the record size
+0x04 u32 orientation         1 = portrait, 0 = landscape; see below
+0x08 u32 1                   35/35
+0x0C u32 pageWidthEmu        8.5 in (letter) or 8.27 in (A4) — equal to the DOCUMENT's
+0x10 u32 pageHeightEmu       11 in or 11.69 in
+0x14 u32 marginLeftEmu       horizontal (left = right) page margin
+0x18 u32 marginTopEmu        vertical (top) page margin
+0x1C u32 gapXEmu             gap between adjacent label columns
+0x20 u32 gapYEmu             gap between adjacent label rows
+0x24 u32 labelWidthEmu       cross-checked against the name text
+0x28 u32 labelHeightEmu
+0x2C u32 columns             label grid
+0x30 u32 rows
+0x34 char[] name             ASCII, NUL-terminated ("Avery 5160,Address,(1\" x 2 5/8\"),1,");
                             bytes after the NUL are stale text from a previous longer name
```

**The four margins, in file order.** `+0x14`/`+0x18` are the page margins applied
symmetrically and `+0x1C`/`+0x20` are the gaps *between* labels, which is what the grid
arithmetic shows over the 35 records:

```
+0x14 (left)    2·m1 + columns·labelWidth  + (columns−1)·gapX  == pageWidth   33/35 exact
+0x18 (top)     m2   + rows·labelHeight    + (rows−1)·gapY     ≤  pageHeight  35/35
+0x1C (gapX)    contributes (columns−1) times, never 2 times
+0x20 (gapY)    contributes (rows−1) times, never 2 times
```

The horizontal identity is exact to within 0.0017 in in 33/35 (the two `Avery L7160`
records are 1 570 EMU short); the vertical one is exact for the 21 letter-size templates
(`2·m2 + rows·labelHeight + (rows−1)·gapY == pageHeight`) and a top-anchored fit for the
rest, because the `L716x` templates store a rounded 5/8 in top margin. Worked example
`B5160.PUB`: `2·0.188 + 3·2.625 + 2·0.125 = 8.501 in` against `pageWidth = 8.5 in`;
`2·0.5 + 10·1.0 + 9·0 = 11 in` against `pageHeight = 11 in`. If `+0x1C` were a third page
margin the sum would be 8.376 in and the labels would not tile the sheet, so the
`(columns−1)`/`(rows−1)` multiplicity is what fixes the reading. [OBSERVED]

**`+0x04` is the sheet orientation.** It is `1` in 33 records and `0` in the two
`Avery L7169` files (`p97/x/B7169.PUB`, `p97/x/D7169.PUB`), and those two are the only
records whose grid cannot fit the page in page coordinates: two 5.472 in columns need
10.94 in against an 8.27 in page width. Transposed they fit exactly —
`2·0.402 + 2·5.472 = 11.748` against `pageHeight = 11.693`, and
`2·0.182 + 2·3.902 + 0.1 = 8.268` against `pageWidth = 8.268` — i.e. the label sheet is
printed landscape. The domain and the action per value are fixed by
`MSPUB.EXE` 98 VA `0x00474583`: it writes the page/label object's 2-bit field at `+0x58`
to `1` when the template's `+0x04 != 0` (and `+0x08 != 0`), and to `2` when `+0x04 == 0`
(`+0x58 = (+0x58 & 0xFFFD) | 1` versus `(+0x58 & 0xFFFE) | 2`). That same 2-bit field is
what the page-setup dialog drives as a two-state radio group — VA `0x0047574b` calls
`CheckRadioButton(hwnd, 0x100E, 0x100F, (value != 1) + 0x100E)`, so `1` is the first
option and everything else the second. `[OBSERVED for the domain {0,1}, the two actions
and the geometry; INFERENCE that the two options are portrait and landscape]`

**The readers.** All three sites are in `MSPUB.EXE` 98 and take the record from
`DOCUMENT+0x86` (§11.1):

| VA | What it does with the record |
|---|---|
| `0x00473dcb` | copies the **12 consecutive dwords `+0x04 … +0x30`** into one row of the label-template list (`DAT_005fd628`, 0x30-byte rows) and `wcscpy`s the wide-converted name from `+0x34` into the row; the list is then walked to fill the label picker |
| `0x00473bc1` | multiplies row dwords 10 and 11 (record `+0x2C`/`+0x30`) and prints "N labels per sheet" — 0x30-byte rows, `(&DAT_005fd650 + index·0x30)` = `+0x28`/`+0x2C` of the row |
| `0x00474583` | applies row dwords 8 and 9 (record `+0x24`/`+0x28`) as the label width/height of the page object (`+0x5A`/`+0x5E`) and row dword 0 (record `+0x04`) as the orientation mode |
| `0x0049f782` | reads record `+0x2C` and `+0x30` as the grid counts when it builds the print descriptor (`param_2[0x17]`/`param_2[0x18]`) |

The four margins are copied into the picker row by `0x00473dcb` but **no code reads them
back**: `DAT_005fd628` is referenced only from `0x00473bc1`, `0x00473dcb`, `0x00474583`
and `0x00474673`, and none of those touches row dwords 4…7 (`+0x14`…`+0x20`); the layout
that actually places labels uses the *page* record's margins (`0x004f5e26`). The margin
order above is therefore established by the grid arithmetic over the corpus, not by a
consumer. [OBSERVED]

Other evidence: all 35 records are children of the DOCUMENT (0x0015, 35/35); `+0x34` is
printable in 35/35 and the bytes after the NUL are zero in 33/35 — the two non-zero tails
are the stale fragment `,1,` in `B5161.PUB`/`B5163.PUB`, the same stale-text idiom as the
`0x001F` name slot (§11.6);
`+0x24`/`+0x28`/`+0x2C`/`+0x30` were cross-checked against the dimensions and grid embedded
in the name: height matches 35/35 **inches**, width 33/35 (the two `Avery 5660` documents
state `2 5/6"` in the name while the field and the real label are 2 5/8"), columns×rows in
{(3,10)×8, (2,7)×4, (2,3)×4, (2,5)×3, (3,7)×2, (3,6)×2, (2,8)×2, (3,4)×2, (2,2)×2,
(3,3)×2, (2,10)×2, (4,20)×1, (2,4)×1} — every pair is a real Avery grid. `+0x0C`/`+0x10`
are the page size and are identical for all records of one installation (`0x7698F0`×
`0x997AA0` = 8.5×11 in on the PageWiz templates, `0x735B40`×`0xA325A0` = 8.27×11.69 in on
the `…716x` label files). [OBSERVED]

## 11.13 Open

| Item | Status | Experiment |
|---|---|---|
| `0x0016 +0x04` style id | `[INFERENCE]` | decompile the story-container consumer in `MSPUB.EXE` and resolve `+0x04` against `0x0026`/`0x001F` entry order |
| `0x004E` 45-byte element interior | partly closed: the four **line widths in points** are at `+0x14`/`+0x1A`/`+0x20`/`+0x26` (VA `0x004547f1` × `0x319C` EMU/pt) and `+0x0A` is a boolean tested by VA `0x004e279f`; the leading `u16` (`0x40/0x50/0x60/0x70`) and the `0xC0E4` colour words have **no reader** — all four widths are 0 in both instances, so no field of this record is exercised | decompile the table renderer around VA `0x0050b7d2` (5-element `0x2D`-stride stack array) and the `0x004e279f` caller to name the leading `u16` and the `0xC0E4` slots |
| `0x0052` `+0x04` ordinal owner | **closed negative**: `+0x04` is a document-wide ascending sequence number (unique, 1…114 over 110 records), not a key and not a chunk id; `ptrA`/`ptrB` are persisted heap addresses. No code reads the chunk (scan scope and VAs in §11.11.1) | — |
