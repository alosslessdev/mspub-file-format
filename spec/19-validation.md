# 19 — Validation

This chapter is the acceptance test for the specification: every structural rule
stated in chapters 01-18 is checked mechanically against every shipped document.
If a rule and the corpus disagree, the rule is wrong.

## 19.1 Corpus

| Label | Source | Documents |
|---|---|---|
| P95 | Publisher 95 CD (`p95/x`) | 130 (128 `.PUB` + 2 `.JSP`) |
| P97 | Publisher 97 disk set (`p97/x`) | 108 |
| P97D | Publisher 97 CD "deluxe" (`p97deluxe/x`) | 250 |
| P98 | Publisher 98 CD (`p98/x`) | 5 (2 `.PUB` + 3 `.JSP`) |
| **total** | | **493** |

All 493 are OLE2/CFB v3 files with a `Contents` stream. On the Publisher 98 CD
the `.JSP` files (`CHEKLIST.JSP`, `CLRCHK.JSP`, `INFOSHET.JSP`) are complete
publications — same container, same chunk directory, same `Quill` storage — and
must be parsed as documents. [OBSERVED]

Per-corpus content totals parsed by the reference reader:

| Corpus | pages | shapes | images | Quill-bearing docs |
|---|---|---|---|---|
| P95 | 727 | 5 481 | 129 | 0 |
| P97 | 608 | 4 769 | 88 | 0 |
| P97D | 1 438 | 11 152 | 310 | 0 |
| P98 | 36 | 538 | 0 | 5 |

Numbers are produced by `python tools/pubread.py --corpus <dir>`; they count PAGE
(`0x14`) records, shape records with the markers listed in chapter 06, IMAGE_DATA
records, and documents containing a `Quill` storage.

## 19.2 Invariants

`tools/validate.py` implements the table below. Each row is a claim from a
chapter; a violation means the chapter is wrong or the corpus contains an
undocumented variant.

| # | Invariant | Chapter | Result |
|---|---|---|---|
| 1 | File parses as CFB v3 | 01 | 493/493 |
| 2 | `Contents[0:2]` ∈ {`ACE8`,`ACE7`} | 02 | 493/493 |
| 3 | `u32@0x08` == length of `Contents` | 02 | 493/493 |
| 4 | format version == 300 | 02 | 493/493 |
| 5 | directory chunk offsets are ascending | 03 | 493/493 |
| 6 | chunk ids are unique within a document | 03 | 493/493 |
| 7 | every `parentId` resolves to a chunk (or is `00FE`/`00FF`) | 03 | 493/493 |
| 8 | chunk extents cover `Contents` with no gap | 03 | 493/493 |
| 9 | exactly one DOCUMENT (`0x15`) chunk | 04 | 493/493 |
| 10 | DOCUMENT size == `0x74 + 2·(pages−1) + R`, `R ∈ {0,30,72}` | 04 | 493/493 |
| 11 | PAGE size == base + `2·count` (P95/97 `0x24`, P98 `0x28`) | 05 | 493/493 |
| 12 | PAGE duplicated count words are equal | 05 | 493/493 |
| 13 | PAGE child ids exist in the directory | 05 | 493/493 |
| 14 | shape bbox satisfies `x0 ≤ x1`, `y0 ≤ y1` | 06 | 493/493 |
| 15 | shape bbox magnitude < 400 in | 06 | 493/493 |
| 16 | IMAGE_DATA `u32@+4` == `size − 8` | 08 | 527/527 |
| 17 | IMAGE_DATA payload starts with a WMF signature | 08 | 527/527 |
| 18 | `0x0022` record is exactly 18 bytes | 12 | 2 134/2 134 |
| 19 | Quill chunk list terminates at `0xFFFFFFFF` | 13 | 5/5 |
| 20 | `0x0022` ordinal resolves to an `Objects/Object N` storage | 15 | 2 134/2 134 |
| 21 | shape `B` byte matches the per-marker constant | 06, 12 | 493/493 documents |
| 22 | shape record `size ≥` per-marker fixed base | 06, 12 | 493/493 documents |
| 23 | GROUP size == base + `2·count`, duplicated counts equal | 07 | 2 935/2 935 |
| 24 | GROUP bbox ordered | 07 | 2 935/2 935 |

Total: **0 violations over 493 documents.** 2 162 embedded objects and 2 134 object
references were cross-checked against the storage tree, and 2 935 groups against their child
lists.

Notes on invariants that had to be weakened after measurement, and why:

* **Shape boxes are not required to lie inside the page.** Publisher allows
  objects on the pasteboard; `p97deluxe/PageWiz/growth7.pub` (an 11 × 81 inch
  growth chart) legitimately places objects far outside the page rectangle. The
  invariant is ordering plus a 400-inch sanity bound.
* **The directory's fifth field is `flags`, not a sequence number.** An earlier
  model read the record as `{u16 X, u16 id, u16 parent, u32 offset}`; the correct
  framing is `u16 count; u16 idHighWaterMark; {u16 id, u16 parent, u32 offset,
  u16 flags}` followed by 10 zero bytes. Chunk ids, parents and offsets are the
  same under both readings, which is why the earlier tooling still produced
  correct chunk trees.
* **P98 counts page slots of type `0x41` as well as `0x14`.** Without that, the
  DOCUMENT delta looks like 74 instead of the true 72.

## 19.3 Residual, unvalidated surface

The following are **not** checked because the corresponding layout is not yet
fully published. They are the open items tracked per version in `notes/*/GAPS.md`:

| Area | Status |
|---|---|
| Interior of most fixed records (markers other than DOCUMENT/PAGE/IMAGE_DATA/`0x22`) | partially mapped; size rules known for the high-volume markers |
| Directory `flags` bit meanings | domain known (`0x1040 | bits`, 13 values), bit semantics open |
| `Contents` header `u16@0x0E`/`0x10` and the fixed `0x22…0x23D` region | partly mapped in chapter 02 |
| P97/P98 DOCUMENT append regions (30 / 72 bytes) | mapped byte-by-byte in chapter 18; P98 region reproduces a CLSID |
| Rare markers `0x0036`, `0x004E`, `0x004F`, `0x0050` | appear only in `.JSP` publications (≤ 4 instances each), not documented |
| Quill payload internals (TEXT/STRS/FDPC/FDPP) | framing and names documented; record interiors in progress (chapter 13) |
| Table representation | no dedicated marker in this family; documented in chapter 10 |

## 19.3.1 Named-field coverage

`tools/p95_validate.py` measures how much of each chunk payload falls inside a field the
specification names, over the 130 Publisher 95 documents:

| Metric | Value |
|---|---|
| bytes outside the chunk framing | **0.0 %** (108 bytes) |
| bytes inside a named field | **60.1 %** |
| unnamed bytes | 39.9 % (750 803 bytes) |

That 60.1 % is the honest completeness number for the Publisher 95 record interiors: the
framing, geometry, size rules, colour references and document-level tables are named.
Since that measurement the shape interior was closed further: fill/line/outline colours, line
width, text colour, the shadow rule and the flag word are now assigned (chapter 06 §6.7), and
the 95/97 text pool's control bytes are closed (chapter 13 §13.14.1), so the residue is now the
Publisher 98-only records and the DOCUMENT print fields listed in each chapter's Open table. It is published so a reader
can tell which parts of a record must be preserved verbatim rather than interpreted.

## 19.4 Reproducing

```bash
python tools/validate.py p95/x p97/x p97deluxe/x p98/x     # 0 violations
python tools/p95_validate.py                               # named-field coverage
python tools/p97_quill_validate.py                         # Quill layouts, 5 documents
python tools/pubread.py --corpus p98/x                    # reader summary
python tools/spec_lint.py spec                            # chapter consistency
python tools/corpus_index.py p95/x p97/x p97deluxe/x p98/x -o notes/corpus-index.json
```

No Microsoft binary is required to reproduce any check in §19.2: the corpus is
sufficient. Binary evidence is only needed to close the open items in §19.3.

## 19.5 Evidence policy

Every claim in this specification carries `[OBSERVED]`, `[INFERENCE]` or
an **UNKNOWN** tag (see [CONTRIBUTING](../CONTRIBUTING.md)). A claim may only be
promoted to `[OBSERVED]` together with an invariant in §19.2 or a citation of a
specific byte offset / binary virtual address.
