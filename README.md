# Publisher 95/97/98 file format specification

Reverse-engineered specification of the Microsoft Publisher 95, 97 and 98
document formats (`.pub`), derived from the retail binaries and the documents
they write.

## What is here

* [`spec/`](spec/) — the specification, one chapter per subsystem.
* [`spec/blocks/tlv-id-table.md`](spec/blocks/tlv-id-table.md) — machine-readable
  table of the typed sub-records used inside every chunk.
* [`spec/enums/`](spec/enums/) — colour, shape, fill, line and text enum domains.
* [`tools/`](tools/) — the analysis and validation tooling used to produce and
  check the specification.
* [`notes/`](notes/) — raw evidence: corpus statistics, disassembly extracts,
  per-version gap ledgers.

## Quick start

```bash
python tools/pubcore.py path/to/document.pub     # chunk inventory
python tools/pubstats.py corpus/ --type 0x15     # field distribution for a chunk type
```

`tools/pubcore.py` is a standalone Reader for the container layer:

```python
import sys; sys.path.insert(0, "tools")
import pubcore
doc = pubcore.parse_contents("document.pub")
for chunk in doc.chunks:
    print(hex(chunk.id), chunk.type_name, hex(chunk.offset), chunk.size)
```

## Coverage

| Layer | Publisher 95 | Publisher 97 | Publisher 98 |
|---|---|---|---|
| CFB container, streams | documented | documented | documented |
| `Contents` header + chunk directory | documented | documented | documented |
| Document / page / shape / group chunks | documented | documented | documented |
| Images, palettes, tables, border art, fonts | documented | documented | documented |
| Typed sub-record (TLV) system | documented | documented | documented |
| Quill text engine | n/a | documented | documented |
| Escher drawing layer | n/a | documented | documented |
| Embedded OLE objects | documented | documented | documented |

Exact coverage and every remaining open question are tracked in
[`notes/`](notes/) per version.

## Method

Three independent evidence classes are used and cross-checked:

1. **Corpus statistics** — differential analysis over every `.pub` file shipped
   on the original CDs. Fields that are constant across hundreds of documents
   are tags; fields that vary are measured against documents whose rendered
   properties are known.
2. **Static reverse engineering** — the shipped `MSPUB.EXE` and companion DLLs
   are disassembled and decompiled to recover exact field offsets, enum domains
   and validation rules.
3. **Prior art** — the MPL-2.0 `libmspub` importer is used only as a set of
   hypotheses to confirm or refute, never as an authority. Where this
   specification and `libmspub` disagree, the disagreement and its evidence are
   recorded.

## License

Specification text and tooling: MPL-2.0 (see [LICENSE](LICENSE)).
The commercial Microsoft binaries and documents are not redistributed here.
