# Publisher 95/97/98 file format specification

Reverse-engineered specification of the Microsoft Publisher 95, 97 and 98
document formats (`.pub`), derived from the retail binaries and from the
documents they write. Published by [alosslessdev](https://github.com/alosslessdev).

## What is here

* [`spec/`](spec/) — the specification, one chapter per subsystem, with a
  provenance tag on every non-trivial claim (`[OBSERVED]`, `[INFERENCE]`,
  `[UNKNOWN]`).
* [`notes/EVIDENCE.md`](notes/EVIDENCE.md) — the shared, cross-version evidence
  ledger: facts measured once and reused by every chapter.
* [`notes/`](notes/) — per-version gap ledgers, corpus statistics and raw
  measurements.
* [`tools/`](tools/) — the analysis and validation tooling that produced and
  checks the specification.

## Format at a glance

```
.pub
└─ OLE2/CFB v3 compound file
   ├─ Contents                     the document (header + chunk directory + chunks)
   ├─ Objects/Object N/…           embedded OLE objects (nested mini-documents)
   ├─ \x01CompObj, \x03Internal    OLE class descriptor, private state
   ├─ \x05SummaryInformation       property set (thumbnail)
   └─ Quill/QuillSub/CONTENTS      Publisher 98 only: the text engine
```

`Contents` layout: `0x22`-byte header → chunk area → directory at `u32@0x16`
(`u16 count` + `count` × `{u16 seqSkip, u16 id, u16 parent, u32 offset}`).
Chunk sizes are derived from the next chunk's offset. Every chunk starts with a
`u16` type marker and the payload is a **fixed record** whose layout depends on
that marker (the `{u8 id, u8 type}` TLV model belongs to Publisher 2000+, not to
this family).

## Reference reader

`tools/pubread.py` implements the specification and is the acceptance test for
it. It parses header, directory, document, page, shape and image records:

```bash
python tools/pubread.py document.pub          # structural summary
python tools/pubread.py --corpus p95/x        # validate a whole corpus
```

Current validation status over 493 shipped documents (Publisher 95 CD 130,
Publisher 97 CD 250, Publisher 97 disk set 108, Publisher 98 CD 5 — the three
`.JSP` files on the 98 CD are publications, not scripts):

| Check | Result |
|---|---|
| CFB parses | 493/493 |
| `Contents` declared length == actual | 493/493 |
| format version == 300 | 493/493 |
| document chunk found | 493/493 |
| PAGE size == base + 2·count | 712/712 (P95), 2016/2016 (P97), 12/12 (P98) |
| DOCUMENT size rule with version delta 0/30/72 | 493/493 |
| directory parents resolve, ids unique, extents cover stream | 484/484 |
| IMAGE_DATA length prefix + WMF signature | 527/527 |
| full structural validator | **0 violations / 493 files** |

## Method

Three independent evidence classes, cross-checked:

1. **Corpus statistics** — differential measurement over every `.pub` shipped on
   the original media. Constant fields are tags; varying fields are correlated
   with known document properties (paper size, page count, z-order).
2. **Static reverse engineering** — the shipped `MSPUB.EXE` / `MSPUB.M14` and the
   Publisher DLLs are decompiled to recover validation rules, enum domains and
   exact offsets.
3. **Prior art** — the MPL-2.0 `libmspub` importer is used only as a set of
   hypotheses to confirm or refute. Its TLV-block model, for instance, is shown
   here to apply to Publisher 2000+ and not to 95/97/98.

Disagreements with prior art are recorded with their evidence rather than
silently resolved.

## License

Specification text and tooling: MPL-2.0 (see [LICENSE](LICENSE)). Microsoft
binaries and documents are not redistributed here; the tools take a corpus path
as an argument.
