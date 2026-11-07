# 03 — The chunk directory

Every chunk of `Contents` is registered in a flat directory of **10-byte records**. The
directory sits at the absolute offset `u32 @ 0x16` of the header (chapter 02) and is placed
*after* the document data and *before* the chunk area, so the reader must consult it before
it can compute any chunk size: a chunk's size is `next.chunkOffset - chunk.chunkOffset`
(last chunk: to end of stream).

Corpus for every figure below: the 130 Publisher 95 CD documents in `p95/x`
(128 `.PUB` + the 2 `.JSP` publications), 10 732 non-empty records.
Tags: **OBSERVED** measured, **INFERENCE** concluded from measurements, **UNKNOWN** not
decidable from this corpus (the discriminating experiment is named). Claim-level tags are
written in brackets; this legend names them without brackets so a marker count finds only real
unresolved claims.
Regenerate the tables with `python tools/p95_census.py`.

## 3.1 Structure

```
Contents+u32[0x16] -> D                              directory offset, 0x2BC .. 0x4678

D+0            u16  count                           34 .. 932 = number of chunk records
D+2            u16  idHwm                           saver writes max(id); loader size hint (§3.5)
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
| `unique` | the `u16` at `+0` is distinct for every record of a file (130/130 files) |
| `asc` | the `u32` at `+4` is strictly ascending (130/130) |
| `after` | that `u32` is greater than the end of the record array (130/130) |
| `types` | `u16` read at that `u32` is one of the known chunk markers (10 732 probes) |
| `fit` | `header + recordSize·count + 10 <= min(chunkOffset)` |

| candidate | unique | asc | after | known types | verdict |
|---|---|---|---|---|---|
| hdr 2, rec 10 (old model) | 0/130 | 0/130 | 130/130 | **0/10 732** | refuted |
| **hdr 4, rec 10** | **130/130** | **130/130** | **130/130** | **10 732/10 732** | **accepted** |
| hdr 6, rec 10 | 0/130 | 0/130 | 130/130 | 0/10 732 | refuted |
| hdr 2, rec 8 | 0/130 | 0/130 | 130/130 | 2 119/10 732 | refuted |
| hdr 4, rec 8 | 0/130 | 0/130 | 130/130 | 2 205/10 732 | refuted |
| hdr 2, rec 12 | 0/130 | 0/130 | 0/130 (overruns) | 1 862/10 732 | refuted |
| hdr 4, rec 12 | 0/130 | 0/130 | 0/130 (overruns) | 1 927/10 732 | refuted |

Seeded with `hdr 4 / rec 10`, every record's `+4` field lands on a byte whose `u16` is a
known chunk marker — 10 732 independent confirmations, i.e. the offset field really points
at the chunk and not merely at *something* plausible.

## 3.3 Binary evidence

`p95/x/MSPUB.EXE`, VA `0x0045E06A` (decompiled at `notes/p95/decomp/0045e06a_FUN_0045e06a.c`;
secondary copy `C:\pwrk\decomp95`), the load/save bridge for this directory:

1. It seeks to `+0x16` and performs **two separate 2-byte reads**: `count` into
   `[ebp-0x60]` (call VA `0x0045E0C7`) and `idHwm` into `[ebp-0x5C]` (call VA
   `0x0045E0E5`). On the normal (non-legacy) load path the hwm is then compared with the
   current in-memory chunk-table size (VA `0x0045E1EA`) and the table is grown so that its
   size becomes `idHwm + 1` (amount VA `0x0045E1F4`, grow call VA `0x0045E215`, size update
   VA `0x0045E224`). That is an allocation rule — the table is indexed by id — not a
   validation of the records (§3.5). The read order and the arithmetic are [OBSERVED]; see
   §3.3.1 for the saver that produces the value.
2. Then `count` iterations of a 10-byte read (call VA `0x0045E28D`) into a five-word stack
   buffer. The first word indexes the 16-byte-per-entry descriptor table at
   `DAT_00585A74` — the id space starts at `0x100`, consistent with `id` being record `+0`.
3. The five words are copied into that entry as `{+0 parentId, +2 chunkOffset (u32),
   +6 flags}`; `+0x0C` receives the parent link XOR-obfuscated with the document id, and
   `+8` (a runtime handle) is not written by the loader. The loader
   then clears **bit 11** of the status word it just stored (`and [entry+6], 0xF7FF`, VA
   `0x0045E30A`). No other bit of the loaded record changes, so bits other than 11
   round-trip. [OBSERVED]
4. On save it writes `count` (VA `0x00536E2E`), then `max(id)` (VA `0x00536E7E`), then the
   same 10-byte records in ascending-offset order. Each record copy has bit 6 forced to 1 and
   bits 11 and 15 forced to 0 before it is written (VA `0x00538727`); the source is the
   in-memory status word. The on-disk `flags` is therefore the manager's word with three bits
   normalised, not a value the saver leaves untouched (§3.6). [OBSERVED]

### 3.3.1 Where `idHwm` comes from

The record writer at VA `0x00538727` — called once per emitted record — does three things
after writing the 10 bytes: it increments the record count and executes

```
if (hwm < *record) hwm = *record;          // hwm = max over emitted ids
```

so the second directory word is *computed as `max(id)` at save time*, not carried over from
an allocation high-water mark. `count` and `idHwm` are then both written by VA `0x00536C85`
(`count` at `0x00536E2E`, `idHwm` at `0x00536E7E`). This is why `idHwm == max(id)` in
493/493 corpus files: it is a writer invariant. On load the word is only a table-size hint,
which is why a file whose `idHwm` disagrees with `max(id)` would still parse: the loader
also allocates a slot on demand when a record's id is at or above the current table size
(VA `0x0049D0E6`, allocation VA `0x0045DBA5`). [OBSERVED for the
save side; the load-side consequence is [INFERENCE] from the code paths]

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

`idHwm == max(id)` in 130/130 P95 files and 493/493 across all four corpora, because the
**writer computes it that way**: the per-record writer increments `count` and sets
`hwm = max(hwm, record.id)` before the directory header is written (§3.3.1). It is therefore
a saver invariant, not a field the loader validates.

The loader reads the word only to size its in-memory chunk table: on the normal load path it
compares the current table size with `idHwm` and grows the table until the size exceeds it
(VA `0x0045E1EA`–`0x0045E224`). It never compares `idHwm` with the ids in the records; a file
whose word disagrees with `max(id)` still loads, and the loader additionally allocates a slot
on demand for any record id above the current table size (VA `0x0049D0E6`). [OBSERVED]

Reader rules: use `max(id)` for "largest id"; use `idHwm` only as an allocation hint; MAY
check `idHwm == max(id)` as a corpus invariant (see §3.10), but MUST NOT reject a file whose
`idHwm` is stale, larger, or smaller than the largest live id.

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
; corpus domain: the 13 values above in 95/97, plus 0x17C0 (cls = 3, bit 7 set) only in the
; five Publisher 98 publications
        0x1440 = bits 6 and 10, set on 10 732/10 732 records
```

| bits | mask | on disk | loader / writer | meaning |
|---|---|---|---|---|
| 0–1 | `0x0003` | `0` in all | set/restored by VA `0x0041D0C7` | 2-bit **in-use state**: 0 idle, 1 in use, 2 sticky/never downgraded, 3 assignable. A saved file always has 0 |
| 2, 4 | `0x0014` | never | — | unused |
| 3 | `0x0008` | varies (2 330) | kept by loader and writer | "registered in auxiliary reference lists": tested by VA `0x00407C1A` before unregistering from three tables **[INFERENCE]** |
| 5 | `0x0020` | 1 342 records: every instance of `0x1A`, `0x1F`, `0x21`, `0x31`, `0x32`, `0x37`, `0x38`, `0x39` and 12/130 of `0x26`; never on any other marker, never with `cls != 2` | kept | record-class **memory/allocation** flag ("owns a separate payload block") **[INFERENCE]**; no individual setter found |
| 6 | `0x0040` | **1 in all** | forced 1 by the record writer VA `0x00538727`; set by the save traversal VA `0x0044D3FC`; cleared on pre-existing slots at load (VA `0x0045E143`) | "persisted / live record" |
| 7 | `0x0080` | varies (3 233) | kept | **linked-object attribute**: the record's Mat/OLE object is a *link* rather than an embedded object. Setter VA `0x004502F6` (`f = (v<<7 ^ f) & 0x80 ^ f`, 98: VA `0x004F74DA`); written with `(_MatQueryObjectType(obj) & 2) >> 1` at insert (VA `0x0044BF05` / `0x0045B975`), copied from the source by clone (VA `0x00450083` / `0x00458A09`), cleared when the object is not a link (VA `0x00522DE1`), and stamped on the chunks a pasted/registered record names at payload `+8` (VA `0x00520C17`) or `+6` (VA `0x004D6F5B`, `0x004FACF7`). See §3.6.5 |
| 8–9 | `0x0300` | varies 0–3 | kept | 2-bit **class/level**: getter VA `0x004010AD`, setter VA `0x0040827E`, "raise to at least n" VA `0x0040CC5F` |
| 10 | `0x0400` | **1 in all** | kept | constant on disk; new-object constructors set it when the object has a parent (VA `0x0044D909`, VA `0x004628E3`) |
| 11 | `0x0800` | `0` in all | **forced 0 by writer VA `0x00538727`; cleared at load VA `0x0045E30A`** | "selected": set/cleared by VA `0x00401A5B` **[INFERENCE]** |
| 12–14 | `0x7000` | `1` in all | masked by the loader as the slot kind | 3-bit **slot kind**: `1` = live chunk, `6` = free/reusable slot (VA `0x0045E15B`, VA `0x00407DA5`) |
| 15 | `0x8000` | `0` in all | **forced 0 by writer VA `0x00538727`; cleared at load (VA `0x0045E14A`)** | traversal mark used by VA `0x0044D3FC` |

Invariants over all 10 732 records: `bit5 ⇒ cls == 2` and `bit7 ⇒ cls ∈ {0, 2}` (no
exceptions).

### 3.6.2 What the binary says the bits are

The word is the chunk manager's **in-memory status word**. It reaches the disk through the
per-record writer (VA `0x00538727`), which forces exactly three bits to fixed values:
bit 6 = 1, bit 11 = 0, bit 15 = 0. The loader stores the disk word unchanged except for
clearing bit 11 (VA `0x0045E30A`). Everything else — bits 0–5, 7–10 and 12–14 — is
whatever the manager had at save time; bits 8–9 are a class enum and bits 12–14 a slot
kind, bit 7 is the linked-object attribute (§3.6.5), and the remaining variable bits (3, 5)
have no structural correlate (§3.6.3).

Only three parts of the word are therefore format-relevant:

* **bits 12–14, slot kind.** The loader masks `(f >> 8) & 0x70` and treats `0x60` as a free
  slot it may reuse (VA `0x0045E15B`); free slots are created by writing
  `(f & 0xEFFF) | 0x6000` (VA `0x00407DA5`). All 10 732 disk records carry kind `1`.
* **bit 6 = 1, "live/persisted".** It is set by the save traversal (VA `0x0044D3FC`) on every
  record reachable from the document and forced again by the record writer. All disk records
  carry it.
* **bits 11 and 15 = 0.** They are transient selection/traversal marks that the writer
  forcibly clears; the loader also clears bit 11 defensively, so a hand-edited 1 there is
  ignored (VA `0x0045E30A`).

All other bits are opaque manager state. A reader that rewrites a record must carry its status
word through unchanged (the writer re-normalises bits 6/11/15 itself, but must not invent the
remaining bits), must not reject a record because a variable bit is set, and must not read a
document property out of bits 3/5/7/8–9. The 13-value domain of §3.6.1 is the projection of
that state for this corpus, not a closed format enumeration. [OBSERVED for the three
normalised bits and the kind mask; INFERENCE for the per-bit names]

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
    `0x1A`/`0x1C`, but they are also set on 2713 / 9116 records that do not. `bit 7`'s
    correlation here is a side effect of its real writer (§3.6.5): the record initialiser
    stamps it from the marker descriptor, so every marker of the document-level family gets
    it. `bit 9` is the class bit. Neither is a per-record text marker.
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

### 3.6.5 Bit 7 — the linked-object attribute (closed)

Bit 7 is not manager bookkeeping: it is the **link flag of the record's Mat/OLE object**,
i.e. "this object is an OLE *link* (an object whose data lives in an external file) rather
than an embedded object". `[OBSERVED]` for the code; the corpus population is a union with a
class default, see below.

The proof is a two-way switch on the same bit, not a correlation:

* VA `0x00438216` builds the OLE verb menu item with
  `wsprintfA(buf, (&PTR_s__s__Object_0046d4b1)[(type & 2) >> 1], className)`. The table is at
  VA `0x0046D4B1` and its two entries are `0x0046D4B9 = "%s &Object"` and
  `0x0046D4C8 = "%s L&ink"`. So **bit 1 of `_MatQueryObjectType`'s result is exactly "the
  object is a link"**, and it selects which of the two strings is shown.
* The status-word writer takes its value from that same bit: at VA `0x0044BF05` (95 insert /
  OLE-paste path) the code does `_MatQueryObjectType_8(obj,&t)` and then, when `t & 2`,
  `FUN_004502F6(chunkId, 1)`. The setter (VA `0x004502F6`) is a pure bit-7 write:
  `f = (v << 7 ^ f) & 0x80 ^ f`. The Publisher 98 build has the identical pair:
  `_MatQueryObjectType_8` → `FUN_004F74DA(chunkId, 1)` in VA `0x0045B975`, and
  `FUN_004F74DA` (VA `0x004F74DA`) writes `f = f & 0xFF7F | (v & 1) << 7`.
* The bit is *cleared* from the same test: VA `0x00522DE1` reads bit 7, re-queries the
  object type, and when the query fails or `type & 2 == 0` does `*f &= 0xFF7F`.
* Clone carries it through verbatim: VA `0x00450083` (95) / `0x00458A09` (98) call
  `FUN_004502F6(newId, (sourceFlags & 0x80) >> 7)` after `_MatCloneObject`.
* Two further writers stamp the bit on the chunks a record *names*, not on the record
  itself: VA `0x00520C17` (OLE paste) sets it on the chunk id held at payload `+8` of the
  pasted record, and VA `0x004D6F5B` / `0x004FACF7` (98) do the same for the chunk id at
  payload `+6` of the record being opened. Both pair the write with `FUN_004F7416(id,1)`,
  the "in use" state of bits 0–1.

`[OBSERVED]` for the two writers above; `[INFERENCE]` for the class default that follows.
The record initialiser VA `0x00407C7D` maps a marker-descriptor bit 10 (`0x400`) into status
bit 7 (`f = ((desc & 0x400) >> 10 << 7 ^ f) & 0x80 ^ f`), so a marker family whose descriptor
carries `0x400` is born with bit 7 = 1 — which is the most economical explanation for the
whole document-level family (`0x15`, `0x16`, `0x1A`, `0x1C`, `0x1E`, `0x23`–`0x2E`,
`0x31`–`0x39`) carrying it in 130/130 files while shapes `0x00`–`0x0F` never do and pages
`0x14` carry it on 274 of 727. Either way, a reader must **carry bit 7 through unchanged** and
must not read a document property out of it.

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

* `0x0016` is a container with four children, in slot order `0x001A`, `0x001C`, `0x002E`,
  `0x002D` (chapter 11 §11.2).
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
idHwm == max(id)                       (writer invariant; loader uses it only as a size hint, §3.5)
flags & 0x1440 == 0x1440 ; flags & 0x7000 == 0x1000
flags & 0x8840 == 0x0040               (bit 6 set; bits 11 and 15 clear — writer-normalised, §3.6.2)
every chunk's u16 type marker is one of the 36 markers of §3.9
```

The 13-value `flags` set of §3.6.1 is a corpus observation, not a rule: only bit 6 = 1 and
bits 11/15 = 0 are forced by the writer (§3.6.2); bits 3/5/7/8–9 may take any combination a
future writer assigns.

`tools/validate.py` checks these against every corpus; it reports 0 violations over the 493
shipped documents.
