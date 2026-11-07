# Microsoft Publisher 95 / 97 / 98 File Format Specification

Status: **work in progress** — this document set is derived entirely from shipped
artifacts (the retail CD images, the executables, and the documents they write).
Where the evidence is incomplete the field is tagged **INFERENCE** or **UNKNOWN**.

Publisher versions covered:

| Version | Release | Container | Version magic |
|---|---|---|---|
| Publisher 95 | 1995 | OLE2/CFB v3 | `0x22` |
| Publisher 97 | 1996 | OLE2/CFB v3 | `0x22` |
| Publisher 98 | 1998 | OLE2/CFB v3 | `0x22` |

Publisher 2000 and later use version magic `0x2C` and are out of scope.

## Reading order

1. [01-container.md](01-container.md) — the OLE2 compound file layer.
2. [02-contents-header.md](02-contents-header.md) — the 0x22-byte `Contents` header.
3. [03-directory.md](03-directory.md) — the chunk directory and object graph.
4. [04-chunk-document.md](04-chunk-document.md) — document-wide settings.
5. [05-chunk-page.md](05-chunk-page.md) — pages, masters, logos.
6. [06-chunk-shape.md](06-chunk-shape.md) — shapes and their geometry.
7. [07-chunk-group.md](07-chunk-group.md) — groups.
8. [08-chunk-image.md](08-chunk-image.md) — raster/vector image records.
9. [09-chunk-palette.md](09-chunk-palette.md) — colour tables.
10. [10-chunk-table-cells.md](10-chunk-table-cells.md) — tables.
11. [11-chunk-logo-borderart-font.md](11-chunk-logo-borderart-font.md) — logos, border art, fonts.
12. [12-tlv-blocks.md](12-tlv-blocks.md) — the typed sub-record system used inside every chunk.
13. [13-quill.md](13-quill.md) — the text engine stream (`Quill/QuillSub/CONTENTS`).
14. [14-escher.md](14-escher.md) — the `Escher/EscherStm` drawing layer.
15. [15-embedded-objects.md](15-embedded-objects.md) — OLE objects and their substorages.
16. [16-metadata.md](16-metadata.md) — `SummaryInformation`.
17. [17-enums.md](17-enums.md) — enum domains.
18. [18-version-differences.md](18-version-differences.md) — 95 vs 97 vs 98.
19. [19-validation.md](19-validation.md) — parser validation results.
20. [blocks/chunk-markers.md](blocks/chunk-markers.md) — generated marker reference table.

Machine-readable tables live in [blocks/chunk-markers.md](blocks/chunk-markers.md)
(one row per chunk marker, generated from the corpus) and [enums/](enums/).

## Terminology

* **CFB** — Microsoft Compound File Binary format, the OLE2 structured-storage
  container. Publisher files are CFB version 3 (512-byte sectors).
* **Stream / storage** — a CFB byte stream / a CFB directory node holding streams.
* **`Contents` stream** — the root-level stream holding the document proper.
* **Chunk** — a top-level typed object in `Contents` (document, page, shape, …).
* **Block** — a typed sub-record inside a chunk payload, framed as
  `{u8 id, u8 type, payload}` where the payload width is implied by `type`.
* **Directory** — the flat table of chunks at the end of `Contents`, with parent
  links forming the object graph.
* **Quill** — Publisher's text engine; its named chunks hold characters, runs,
  paragraph properties and style sheets.

## Conformance language

`MUST`, `SHOULD`, `MAY` are used as in RFC 2119. Byte offsets are zero-based from
the start of the named stream unless stated otherwise. Integer byte order is
little-endian throughout.

## Provenance

Every non-trivial claim in this specification carries one of:

* `[OBSERVED]` — directly measured from at least one shipped file or from the
  disassembly of the shipped binaries.
* `[INFERENCE]` — follows from observations plus domain knowledge but was not
  directly confirmed.
* **UNKNOWN** — not yet established; the open question is stated. (Tags are written as
  `[OBSERVED]`, `[INFERENCE]`, `[UNKNOWN]` on individual claims; this line names them without
  brackets so a marker-count check counts only real unresolved claims.)
