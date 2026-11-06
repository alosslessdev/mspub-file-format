# 03 — The chunk directory

Every chunk of `Contents` is registered in a flat directory of **10-byte records**. The
directory sits at the absolute offset `u32 @ 0x16` of the header (chapter 02) and is placed
*after* the document data and *before* the chunk area, so the reader must consult it before
it can compute any chunk size: a chunk's size is `next.chunkOffset - chunk.chunkOffset`
(last chunk: to end of stream).

Corpus for every figure below: the 130 Publisher 95 CD documents in `p95/x`
(128 `.PUB` + the 2 `.JSP` publications), 10 732 non-empty records.
Tags: **[OBSERVED]** measured, **[INFERENCE]** concluded from measurements,
**[UNKNOWN]** not decidable from this corpus (the discriminating experiment is named).
Regenerate the tables with `python tools/p95_census.py`.

## 3.1 Structure

```
Contents+u32[0x16] -> D                              directory offset, 0x2BC .. 0x4678

D+0            u16  count                           34 .. 932 = number of chunk records
D+2            u16  idHwm                           id high-water mark (== max(id), §3.5)
D+4            count × 10 bytes:
                 +0  u16  id                       chunk id, unique in the document
                 +2  u16  parentId                 0x00FE/0x00FF for the document record, else a live id
                 +4  u32  chunkOffset              absolute offset into Contents
                 +8  u16  flags                    status word (§3.6)
D+4+10·count   10 × 0x00                            null record (§3.7)
D+14+10·count  <first chunk>                       == min(chunkOffset), 130/130
<chunks>       …, last chunk ends exactly at len(Contents)
```

[OBSERVED] 130/130: `D + 14 + 10·count == min(record.chunkOffset)` and the first chunk's
`u16` type marker is `0x0015` (DOCUMENT). There is no padding, gap or trailer anywhere in
the chunk area: `offset[i+1] == offset[i] + size[i]` for every adjacent pair and the last
extent ends at `len(Contents)`.

**Correction against older notes.** Earlier revisions of this project modelled the block as
`u16 count` followed by `count × {u16 seqSkip, u16 id, u16 parent, u32 offset}`. That parse
consumes the same byte count but shifts every field by one `u16`: it reads the *header's*
`idHwm` as record 0's first field and every record's `flags` as the next record's first
field. The 4-byte header is the only model that satisfies all invariants at once (§3.2), and
it is what `MSPUB.EXE` does (§3.3). `pubcore.Chunk.flags` is the real field;
`Chunk.seq_skip` exists only as a deprecated alias.

## 3.2 Why exactly this framing — the candidate test

Five independent predicates were evaluated for every candidate `(header size, record size)`
split of `D … min(chunkOffset)` over the whole corpus [OBSERVED]:

| predicate | meaning |
|---|---|
| `unique` | the `u16` at `+0` is distinct for every record of a file (128/128 files) |
| `asc` | the `u32` at `+4` is strictly ascending (128/128) |
| `after` | that `u32` is greater than the end of the record array (128/128) |
| `types` | `u16` read at that `u32` is one of the known chunk markers (10 640 probes) |
| `fit` | `header + recordSize·count + 10 <= min(chunkOffset)` |

| candidate | unique | asc | after | known types | verdict |
|---|---|---|---|---|---|
| hdr 2, rec 10 (old model) | 0/128 | 119/128 | 128/128 | **0/10 640** | refuted |
| **hdr 4, rec 10** | **128/128** | **128/128** | **128/128** | **10 640/10 640** | **accepted** |
| hdr 6, rec 10 | 0/128 | 0/128 | 128/128 | 0/10 640 | refuted |
| hdr 2, rec 8 | 0/128 | 0/128 | 128/128 | 2 078/10 640 | refuted |
| hdr 4, rec 8 | 0/128 | 0/128 | 128/128 | 2 186/10 640 | refuted |
| hdr 2, rec 12 | 0/128 | 0/128 | 128/128 | 1 889/10 640 | refuted |
| hdr 4, rec 12 | 0/128 | 0/128 | 0/128 (overruns) | 1 910/10 640 | refuted |

Seeded with `hdr 4 / rec 10`, every record's `+4` field lands on a byte whose `u16` is a
known chunk marker — 10 640 independent confirmations, i.e. the offset field really points
at the chunk and not merely at *something* plausible.

## 3.3 Binary evidence

`p95/x/MSPUB.EXE`, VA `0x0045E06A` (decompiled at `notes/p95/decomp/0045e06a_FUN_0045e06a.c`;
secondary copy `C:\pwrk\decomp95`), the load/save bridge for this directory:

1. It performs **two separate 2-byte reads**. The first is the loop bound (`count`); the
   second is held in a 2-byte slot and compared against the in-memory chunk-table size — if
   `tableCount <= fileWord` the table is grown by `fileWord - tableCount + 1`. That is
   high-water-mark semantics, not a chunk field: it is the `idHwm` word at `D+2`. [INFERENCE
   from the arithmetic; the read order is [OBSERVED]]
2. Then `count` iterations of `read(…, 10)` into five consecutive `u16` stack slots. The
   first word is used as an index into the 16-byte-per-entry descriptor table at
   `DAT_00585A74` — the id space starts at `0x100`, consistent with `id` being record `+0`.
3. The five words are copied into that entry as `{+0 parentId, +2 offsetLow, +4 offsetHigh,
   +6 flags, +8 handle}` (+0x0C holds a parent link XOR-obfuscated with the document id).
   The on-disk `flags` therefore round-trips verbatim; the saver re-emits it unchanged and
   never recomputes it (§3.6).
4. On save it writes `count`, the high-water mark, then the same 10-byte records in
   ascending-offset order.

## 3.4 `id` and `parentId` — proven by cross-reference

Independent proof that `+0` is the id and `+2` the parent:

* The DOCUMENT chunk stores the ids of other chunks at `+0x04`, `+0x06`, `+0x08`,
  `+0x46…+0x60`, `+0x68` and `+0x74…`. Every one of those values equals the **first** `u16`
  of exactly one record, and the referenced chunk always has the expected type
  (130/130; chapter 04 §4.3).
* The PAGE chunk stores its child ids at `+0x24`; those equal the first `u16` of the child
  records and each child's **second** `u16` equals the page's own id (727/727; chapter 05).
* The `u16` at `+2` is either the root sentinel (exactly one record per file, the DOCUMENT) or
  an id that resolves inside the same file (10 602/10 602 non-root records). The sentinel is
  `0x00FE` in the 128 `.PUB` documents and `0x00FF` in the two `.JSP` publications
  (`CHEKLIST.JSP`, `INFOSHET.JSP`) — both values are below the id space (min id 256), so a
  reader must accept either, and `0x00FE`/`0x00FF` must never be resolved as ids.

Corpus invariants (130/130 files):

| property | result |
|---|---|
| ids unique within a file | 130/130 (0 duplicates) |
| every `parentId` is `0x00FE`/`0x00FF` or resolves to a live id | 130/130 (0 dangling) |
| exactly one record has a sentinel parent, and it is the DOCUMENT (`0x0015`) | 130/130 |
| `chunkOffset` strictly ascending in directory order | 130/130 |
| `id >= 0x0100` | 130/130 (id space starts at 256; `0x00FE` = 254 is a sentinel *below* it) |
| record 0 is the DOCUMENT and has the smallest offset | 130/130 |

Because offsets ascend, `size = next.chunkOffset - chunk.chunkOffset` and the directory can
be walked linearly without sorting. Directory order is *write* order, not tree order: the
DOCUMENT's children are never contiguous (130/130 groups straddle other subtrees), and 16
parent groups across the corpus have a child written *before* its parent (all inside pages).
Consumers must therefore resolve parents by id, never by position.

## 3.5 `idHwm`

`idHwm == max(id)` in 130/130 files. This is a consequence of the corpus, not an identity:
nothing was ever deleted from a shipped template, so a high-water mark and the largest live
id coincide. The binary treats the word as a mark (§3.3 step 1), so readers MUST use
`max(id)` when they need "largest id" and MAY use `idHwm` only as an allocation hint.

Experiment that separates the readings: in Publisher 95 delete a shape, save, re-open — if
`idHwm` keeps the pre-deletion value while `max(id)` drops, the field is a high-water mark.

## 3.6 The `flags` word (`D+4·k+8`)

### 3.6.1 Closed domain

10 732 records carry exactly **13** distinct values [OBSERVED]:

| value | records | share | value | records | share |
|---|---|---|---|---|---|
| `0x1640` | 4 513 | 42.1 % | `0x1548` | 207 | 1.9 % |
| `0x16C0` | 1 890 | 17.6 % | `0x1660` | 129 | 1.2 % |
| `0x1648` | 1 268 | 11.8 % | `0x16C8` | 123 | 1.1 % |
| `0x16E0` | 1 213 | 11.3 % | `0x1540` | 119 | 1.1 % |
| `0x1448` | 696 | 6.5 % | `0x1440` | 67 | 0.6 % |
| `0x1740` | 464 | 4.3 % | `0x1748` | 36 | 0.3 % |
| | | | `0x14C0` | 7 | 0.1 % |

Bit decomposition of the whole corpus:

```
flags = 0x1440 | (bit3 << 3) | (bit5 << 5) | (bit7 << 7) | (cls << 8)
        0x1440 = bits 6 and 10, set on 10 732/10 732 records
```

| bits | mask | always | never | meaning |
|---|---|---|---|---|
| 0–1 | `0x0003` | — | yes | tested by the binary (`& 0x803`) but never set |
| 2, 4 | `0x0014` | — | yes | unused |
| 3 | `0x0008` | — | — | binary: "registered in auxiliary reference lists" **[INFERENCE]** |
| 5 | `0x0020` | — | — | only ever with `cls == 2`; **[UNKNOWN]** |
| 6 | `0x0040` | **yes** | — | cleared by the saver after writing ⇒ "live/persisted" |
| 7 | `0x0080` | — | — | one boolean; **[UNKNOWN]** |
| 8–9 | `0x0300` | — | — | 2-bit class/level enum, values 0–3 (`cls`) |
| 10 | `0x0400` | **yes** | — | set together with node kind 7 |
| 11 | `0x0800` | — | yes | unused |
| 12–14 | `0x7000` | `kind = 1` | — | 3-bit node kind; 1 = "live chunk" (§3.6.2) |
| 15 | `0x8000` | — | yes | unused |

Invariants over all 10 732 records: `bit5 ⇒ cls == 2` and `bit7 ⇒ cls ∈ {0, 2}` (no
exceptions).

### 3.6.2 What the binary says the bits are

Only code paths that touch the 16-byte table entry `+6` (all via `DAT_00585A74`):

| bits | accessor VA | reading |
|---|---|---|
| 0–1 | tested at `0x00411F50`, `0x00401148` (`& 0x803`) | never set in the corpus |
| 3 | reader `0x00407C1A`: `if (entry[6] & 8) FUN_00530C45(id)` → unregisters the id from three auxiliary tables, then clears bit 3 | "chunk is registered in auxiliary reference lists" **[INFERENCE]** |
| 5 | no individual accessor found | **[UNKNOWN]** |
| 6 | save path clears it after writing | live/persisted marker |
| 7 | setter `0x004502F6` (`f = (v<<7 ^ f) & 0x80 ^ f`), re-written by `0x00450083` | one boolean **[UNKNOWN]** |
| 8–9 | getter `0x004010AD` `(f & 0x300) >> 8`; setter `0x0040827E`; "raise to at least n" `0x0040CC5F` called with literals 1, 2, 3 | 2-bit **level/class** enum |
| 10 | set by `0x00405497` together with node kind 7 | constant here |
| 11 | set/cleared by `0x00401A5B` | never set in the corpus |
| 12–14 | `0x00401148` `switch ((f & 0x7000) >> 12)`; `0x00407C1A`/`0x00407DA5` write `(f & 0xEFFF) | 0x6000` for a **free slot**; `0x0045E06A` counts kind 6 as reusable | 3-bit node kind; `1` = live chunk in this corpus |

So the word is the chunk manager's **in-memory status word**, persisted verbatim by the
saver. Document-independent content: `kind = 1` (live) and the constant `0x440`.

### 3.6.3 The structural-bit experiment (2 × 2 over 130 files)

Hypothesis under test: some bits encode structure a reader could reconstruct — has
children, last sibling, owns text runs, is a page slot. For each variable bit and each
predicate, the full corpus gives (`a` = feature ∧ bit, `b` = feature ∧ ¬bit, `c` = ¬feature
∧ bit, `d` = neither; `n = 10 732`):

| predicate | bit 3 | bit 5 | bit 7 | bit 8 | bit 9 |
|---|---|---|---|---|---|
| has children | a=1003 b=1562 c=1327 d=6840 | 390/2175/952/7215 | 818/1747/2415/5752 | 32/2533/794/7373 | 2428/137/7208/**959** |
| φ | **+0.24** | +0.05 | +0.02 | −0.14 | +0.09 |
| is last sibling | 454/2241/1876/6161 | 519/2176/823/7214 | 783/1912/2450/5587 | **569/2126/257/7780** | 2461/234/7175/862 |
| φ | −0.07 | +0.12 | −0.01 | **+0.29** | +0.03 |
| owns text runs | 123/397/2207/8005 | 130/390/1212/9000 | **520/0**/2713/7499 | 0/520/826/9386 | **520/0**/9116/1096 |
| φ | +0.01 | +0.09 | **+0.34** | −0.07 | +0.08 |
| is a page slot (`0x14`) | 193/534/2137/7868 | **0**/727/1342/8663 | 274/453/2959/7046 | 33/694/793/9212 | 577/150/9059/946 |
| φ | +0.03 | −0.10 | +0.04 | −0.03 | −0.09 |

Result [OBSERVED]:

* **No bit is predicted exactly by any structural predicate.** The best single association
  in the whole matrix is `bit 7` against `is shape` (φ = −0.80): shapes essentially never
  carry bit 7. Next is `bit 8` against `is last sibling` (21.1 % when last, 3.2 % otherwise,
  φ = +0.29) — a real but diffuse correlate, not a definition.
* The four requested predicates settle as follows:
  * **has children** — no bit corresponds. `bit 3` is the closest (39.1 % vs 16.2 %) and it
    also fires on 1327 leaves; it is not a container flag.
  * **is last sibling** — only `bit 8` moves (21 % vs 3 %); still 2 126 non-last records set
    it and 257 last siblings clear it.
  * **owns text runs** — `bit 7` and `bit 9` are set on **all 520** records that own (or are)
    `0x1A`/`0x1C`, but they are also set on 2713 / 9116 records that do not. The reverse
    implication is exact: every non-shape, document-level or story-related marker has
    `bit 7` = 1 or 0 consistently (§3.6.4), so this is a marker-class property, not a
    per-record one.
  * **is a page slot** — `bit 5` is never set on a page (0/727), but 1342 non-pages set it;
    pages use nine of the thirteen values, more than any other marker.
* The class bits (8–9) fail a *stronger* test as well: the corpus cross-tab `cls ×
  {has_children, last_sibling, first_sibling, only_child, depth}` has no cell above 39 %.

Conclusion: `flags` is **manager state assigned when the chunk is created/registered**, not
a document property. That is why 23 of the 36 markers have one single value in the whole
corpus while the 13 multi-valued ones are exactly the markers that Publisher can create in
more than one way (all shapes, pages, groups, the document and the `0x22`/`0x26` records).

### 3.6.4 Per-marker values (whole corpus)

| marker | flags | marker | flags |
|---|---|---|---|
| `0x00` | 1448×555, 1548×181, 1640×152, 1540×119, 1648×71, 1440×21, 1748×9 | `0x22` | 1740×457, 1440×32 |
| `0x01` | 1640×137, 1648×37, 1448×18, 1548×17, 1748×10, 1440×3 | `0x23` | 16C0 |
| `0x02` | 1640×237, 1648×13 | `0x26` | 16C0×118, 16E0×12 |
| `0x03` | 1648×322, 1640×297 | `0x27` | 16C0 |
| `0x04` | 1640×518, 1648×180 | `0x28` | 16C0 |
| `0x05` | 1640×963, 1648×149 | `0x29` | 16C0 |
| `0x06` | 1640×1268, 1648×56 | `0x2A` | 16C0 |
| `0x07` | 1640×239, 1648×29 | `0x2B` | 16C0 |
| `0x0F` | 1640×460, 1648×367 | `0x2C` | 16C0 |
| `0x14` | 16C0×267, 1640×242, 1448×123, 1648×44, 1748×17, 1440×11, 1548×9, 14C0×7, 1740×7 | `0x2D` | 16C0 |
| `0x15` | 16C8×123, 16C0×7 | `0x2E` | 16C0 |
| `0x16` | 16C0×130 | `0x31` | 16E0×390 |
| `0x1A` | 16E0×130 | `0x32` | 16E0×390 |
| `0x1C` | 16C0×130 | `0x34` | 16C0×70 |
| `0x1E` | 16C0×130 | `0x35` | 16C0×74 |
| `0x1F` | 16E0×130 | `0x36` | 16C0×1 |
| `0x21` | 1660×129 | `0x37` | 16E0×16 |
| | | `0x38` | 16E0×15 |
| | | `0x39` | 16E0×130 |

Two sub-populations worth naming [OBSERVED]:

* The seven files whose DOCUMENT record is `0x16C0` instead of `0x16C8` are `MSPUB.PUB`,
  `CLASS_CD.PUB`, `JAZZY_CD.PUB`, `MODRN_CD.PUB`, `PLAIN_CD.PUB`, `CHEKLIST.JSP` and
  `INFOSHET.JSP` — the master template, the four `*_CD` templates and the two `.JSP`
  publications. This is **not** the 8-file `0x3303` header sub-population (only `MSPUB.PUB`
  is in both).
* `0x22` splits into class 3 (457) and class 0 (32). The class-0 instances of a file are a
  contiguous ordinal tail, i.e. one specific paste/import operation created them.

## 3.7 The 10 zero bytes after the records

Immediately after the last record there are exactly **10 bytes, all `0x00`, in 130/130
files**; no other gap size occurs, and the first chunk starts right after them.
[OBSERVED]

They are a **null record** (`id = 0, parent = 0, offset = 0, flags = 0`), not alignment
padding:

* They are *not* counted by `count` — `count` equals the number of live chunks exactly.
* Read as a record, `offset = 0` lies before the directory and would violate the strict
  ascending rule of §3.4; `flags = 0` decodes to node kind 0, a kind that never occurs in a
  live record.
* Ten bytes is exactly one record, and the value is 0 in all 130 files, not a repeating
  alignment fill (a fill would be 2 or 4 bytes and would also appear between chunks; nothing
  is ever padded between chunks).

**The "trailer stamp family" is this padding read through the old framing.** Older revisions
reported a 12-byte trailer `u16 stamp ∈ {0x1540,0x1548,0x1640,0x1648}; u32 0; u32 0; u16 0`.
The first two of those twelve bytes are simply the low `u16` of the *last directory record's
`flags` word* (§3.6) leaking past the end of a 2-byte-header parse; the remaining ten are
the null record described above. There is **no trailer**: `D+14+10·count` is the first chunk
in 130/130 files, and `0x1640`/`0x16C0` stamps appearing "after the directory" are record
flags, not a terminator.

## 3.8 Parent graph

* Root: exactly one record per file has `parentId` equal to a sentinel (`0x00FE` in 128 `.PUB`,
  `0x00FF` in the 2 `.JSP`) and it is the DOCUMENT (`0x0015`) record. 130/130.
* No orphans (every non-root parent resolves), no cycles, no self-parent.
* Depth histogram (DOCUMENT = 0): `0:130, 1:2506, 2:3599, 3:855, 4:1327, 5:1398, 6:764,
  7:137, 8:16`.
* Depth by marker [OBSERVED, closed]:
  `0x15` = 0; `0x14`, `0x16`, `0x1E`, `0x1F`, `0x23`, `0x26`, `0x27`, `0x28`, `0x29`,
  `0x2A`, `0x2B`, `0x31`, `0x34`, `0x35`, `0x37`, `0x38`, `0x39` = 1;
  `0x1A`, `0x1C`, `0x2C`, `0x2D`, `0x2E`, `0x32` = 2; `0x36` = 2; `0x22` = 3–7;
  shapes `0x00`–`0x0F` = 2–8.
  That is a chapter-level rule: every page hangs directly off the document; every
  document-level singleton is depth 1; `0x1A`/`0x1C`/`0x2D`/`0x2E` live under `0x16`; `0x2C`
  under `0x14`; `0x32` under `0x31`; `0x36` under `0x29`; `0x22` under `0x03`.
* Fan-out: 8097+ leaves, maximum 214 (page `0x14` in `BIZSALE.PUB`).

## 3.9 Chunk census (130 documents, 10 732 chunks, 36 markers)

`bytes` = sum of chunk sizes; `size min/mode/max` in bytes; `flags` are the values of §3.6.4.

| marker | n | files | per-file | parents (top 2) | bytes | size min/mode/max | distinct | depth |
|---|---|---|---|---|---|---|---|---|
| `0x0000` SHAPE / text frame | 1108 | 130 | 1–49 | 0x14×893, 0x0F×215 | 113 446 | 102/102/108 | 4 | 2–5 |
| `0x0001` SHAPE1 (14-byte tail) | 222 | 130 | 1–10 | 0x14×153, 0x0F×69 | 36 734 | 106/106/540 | 18 | 2–4 |
| `0x0002` IMAGE | 250 | 130 | 1–26 | 0x14×138, 0x0F×112 | 31 612 | 126/126/182 | 2 | 2–5 |
| `0x0003` SHAPE3 (polygon) | 619 | 130 | 1–53 | 0x14×388, 0x0F×231 | 88 570 | 126/126/958 | 12 | 2–6 |
| `0x0004` LINE | 698 | 130 | 1–326 | 0x0F×460, 0x14×238 | 41 182 | 59/59/59 | **1** | 2–8 |
| `0x0005` RECT | 1112 | 130 | 1–258 | 0x0F×823, 0x14×289 | 68 944 | 62/62/62 | **1** | 2–7 |
| `0x0006` SHAPE_OBJECT | 1324 | 130 | 1–375 | 0x0F×1170, 0x14×154 | 70 172 | 53/53/53 | **1** | 2–8 |
| `0x0007` SHAPE7 | 268 | 130 | 1–48 | 0x14×150, 0x0F×118 | 10 988 | 41/41/41 | **1** | 2–7 |
| `0x000F` GROUP | 827 | 40 | 1–214 | 0x0F×695, 0x14×132 | 35 904 | 38/38/228 | 34 | 2–7 |
| `0x0014` PAGE | 727 | 130 | 5–12 | 0x15×727 | 31 242 | 36/36/116 | 28 | 1 |
| `0x0015` DOCUMENT | 130 | 130 | 1 | root | 16 274 | 124/124/138 | 6 | 0 |
| `0x0016` story container | 130 | 130 | 1 | 0x15×130 | 2 080 | 16/16/16 | **1** | 1 |
| `0x001A` story table #1 | 130 | 130 | 1 | 0x16×130 | 33 522 | 26/54/1370 | 33 | 2 |
| `0x001C` story table #2 | 130 | 130 | 1 | 0x16×130 | 22 308 | 26/34/890 | 45 | 2 |
| `0x001E` FONT table | 130 | 130 | 1 | 0x15×130 | 28 751 | 63/74/758 | 94 | 1 |
| `0x001F` line/border style table | 130 | 130 | 1 | 0x15×130 | 181 828 | 16/16/33828 | 33 | 1 |
| `0x0021` IMAGE_DATA | 129 | 23 | 1–25 | 0x02×115, 0x27×14 | 915 716 | 248/1368/114148 | 62 | 2–6 |
| `0x0022` OLE reference | 489 | 84 | 1–52 | 0x03×489 | 8 802 | 18/18/18 | **1** | 3–7 |
| `0x0023` 4-slot table | 130 | 130 | 1 | 0x15×130 | 4 009 | 28/30/36 | 6 | 1 |
| `0x0026` paragraph-style names | 130 | 130 | 1 | 0x15×130 | 11 915 | 35/35/649 | 27 | 1 |
| `0x0027` clip-art reference | 14 | 14 | 1 | 0x15×14 | 588 | 42/42/42 | **1** | 1 |
| `0x0028` paper/print block | 130 | 130 | 1 | 0x15×130 | 7 500 | 56/56/86 | 6 | 1 |
| `0x0029` PRINT SETUP | 130 | 130 | 1 | 0x15×130 | 39 698 | 149/171/1066 | 18 | 1 |
| `0x002A` font-substitution | 130 | 130 | 1 | 0x15×130 | 2 577 | 16/16/203 | 3 | 1 |
| `0x002B` document names | 30 | 30 | 1 | 0x15×30 | 887 | 27/29/34 | 3 | 1 |
| `0x002C` page layout grid | 139 | 130 | 1–2 | 0x14×139 | 8 422 | 58/58/100 | 6 | 2 |
| `0x002D` story mirror A | 130 | 130 | 1 | 0x16×130 | 3 412 | 26/26/58 | 2 | 2 |
| `0x002E` story mirror B | 130 | 130 | 1 | 0x16×130 | 3 380 | 26/26/26 | **1** | 2 |
| `0x0031` design/object-set | 390 | 130 | 3 | 0x15×390 | 15 244 | 30/30/486 | 13 | 1 |
| `0x0032` design string table | 390 | 130 | 3 | 0x31×390 | 12 340 | 16/16/769 | 15 | 2 |
| `0x0034` 14-byte sub-table | 70 | 70 | 1 | 0x15×70 | 14 392 | 172/172/256 | 2 | 1 |
| `0x0035` DLL binding | 74 | 74 | 1 | 0x15×74 | 14 800 | 200/200/200 | **1** | 1 |
| `0x0036` print-setup companion | 1 | 1 | 1 | 0x29×1 | 112 | 112/112/112 | **1** | 2 |
| `0x0037` colour list (6 B) | 16 | 16 | 1 | 0x15×16 | 242 | 14/14/20 | 2 | 1 |
| `0x0038` colour list (10 B) | 15 | 15 | 1 | 0x15×15 | 210 | 14/14/14 | **1** | 1 |
| `0x0039` 48-byte record | 130 | 130 | 1 | 0x15×130 | 6 240 | 48/48/48 | **1** | 1 |

[OBSERVED] 36 distinct markers, and no other marker value occurs. Notes:

* `0x0016` is a container: `0x001A`, `0x001C`, `0x002D`, `0x002E` are its four children, in
  that order (chapter 06 §6.7).
* `0x0003` owns all 489 `0x0022` records; `0x0031` owns all 390 `0x0032` records.
* `0x0021` (image data) is owned by `0x0002` (image) and by `0x0027` (clip art).
* `0x0036` occurs once in the whole 130-document corpus, inside `CHEKLIST.JSP`, under the
  `0x0029` print-setup record; the identical record exists in the `CHEKLIST.JSP` copies of
  the 97, 97-deluxe and 98 CDs (chapter 17 §17.10).

## 3.10 Validation predicates

```
directory_offset in [0x22, len(Contents)-4)
directory_offset + 14 + 10*count == min(chunkOffset)
Contents[D+4+10*count .. +10] == 10 x 0x00
ids unique ; id >= 0x0100
every parentId in {0x00FE, 0x00FF} or resolves to an id in the file
exactly one record has a sentinel parentId and it is the 0x0015 chunk
chunkOffset strictly ascending ; offset[i+1] == offset[i] + size[i] for adjacent records
last extent ends at len(Contents)
idHwm == max(id)                       (corpus property, not a format guarantee)
flags & 0x1440 == 0x1440 ; flags & 0x7000 == 0x1000
flags in the 13-value set of §3.6.1
every chunk's u16 type marker is one of the 36 markers of §3.9
```

`tools/validate.py` checks the structural subset of these against every corpus; it reports
0 violations over the 493 shipped documents.
