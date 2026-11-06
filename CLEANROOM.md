# Clean-room reimplementation package

This repository is the **documentation source** for an independent (clean-room)
implementation of the Microsoft Publisher 95 / 97 / 98 file format. It contains
everything an implementer needs and nothing they must not read.

## What is in the package (the reading set)

| Path | Content |
|---|---|
| [`spec/`](spec/) | the specification, 20 chapters + marker table + enums |
| [`kaitai/`](kaitai/) | declarative binary grammar (Kaitai Struct) for the container and the `Contents` stream |
| [`tests/`](tests/) | sample-file manifest (source, size, SHA-256) and the **expected output** for each sample, as data |
| [`notes/EVIDENCE.md`](notes/EVIDENCE.md) | the shared measurement ledger the chapters cite |

## What is excluded (do not read it if you are implementing)

| Path | Why |
|---|---|
| `tools/` | our reference reader, validators and generators — code, therefore excluded |
| `notes/*/slices/`, `notes/tmp/` | raw working notes containing script references |
| the `libmspub` fork (separate repository) | derived from MPL-2.0 code, therefore excluded |

If you are the implementer: work from `spec/`, `kaitai/` and `tests/` only. Ask
questions against those files, not against the excluded ones.

## Provenance rules for the specification

1. Every non-trivial claim carries `[OBSERVED]`, `[INFERENCE]` or `[UNKNOWN]`.
   `[OBSERVED]` means it was measured on a shipped document or read out of a
   shipped binary; the offset or virtual address is cited.
2. **No implementation code was consulted to write the rules.** The MPL-2.0
   `libmspub` importer was used only as a set of *hypotheses to test*. The
   convention is mechanical: **any paragraph that contains the word `libmspub` is
   a prior-art comparison and may be skipped without losing a rule.** No rule
   table (a Markdown table row) mentions it — enforced by
   `tools/spec_lint.py` — so nothing normative depends on prior art.
3. The sample documents and the Microsoft binaries are **not** distributed here.
   `tests/corpus.md` names each file's Internet Archive item, path, size and
   SHA-256 so the same bytes can be obtained and verified.

## Protocol

1. Read `spec/00-overview.md`, then the chapter for the layer you are
   implementing. Chapters 01-05 are structural (container, header, directory,
   document, pages) and are the minimum for a reader.
2. Read `kaitai/mspub.ksy` for the declarative form of the same structures —
   generated code from it is a valid starting point and a second, independent
   encoding of the spec.
3. Obtain the samples listed in `tests/corpus.md`, verify the SHA-256, and diff
   your output against `tests/expect/<sample>.json`.
4. When the expected file and the spec disagree, the expected file wins for
   *values* and the spec wins for *meaning*; report the conflict so both can be
   fixed.

## Expected output format

`tests/expect/*.json` is plain data: no code, no interpreter, no library. It
lists, per sample, the container streams, the header fields, the chunk inventory,
pages with their z-order child lists, shapes with raw rotation and EMU geometry,
image payload sizes and MD5s, palettes, embedded-object references, and the text
store or Quill stream summary. See `tests/corpus.md` for the key-by-key
description.

Because the payload MD5s are published, an implementation can prove it extracted
the exact same bytes without any copyrighted material being redistributed.

## Legal

The format itself is not copyrightable; the specification and grammar here are
original work released under MPL-2.0 (see [LICENSE](LICENSE)). Microsoft
Publisher, its binaries and its template documents remain Microsoft's property
and are not redistributed. `[INFERENCE]` markers exist precisely so that a
reimplementer knows which rules still need an independent experiment rather than
inherited trust.
