# Correlation and evidence policy

This repository documents a proprietary binary format from shipped artifacts.
To keep the result reproducible and legally clean, follow these rules.

## Evidence classes

Every non-trivial statement in `spec/` MUST carry one of:

* `[OBSERVED]` — measured from at least one shipped file, or read out of the
  shipped binaries. Include the file path and byte offset (or the binary and
  function/address) inline.
* `[INFERENCE]` — follows from observations plus domain knowledge; state the
  reasoning in one sentence.
* `[UNKNOWN]` — not established; state the experiment that would settle it.

Never promote an `[INFERENCE]` to `[OBSERVED]` without a new measurement.

## Quoting binary code

Describe behaviour, offsets, enum domains and validation rules in prose and
tables. Do **not** paste decompiled or disassembled Microsoft code into the
repository. Short factual extracts (a constant, a comparison, a switch domain)
are fine; blocks of pseudocode are not. Record *where* to look instead:
binary path + virtual address + function name.

## Corpus

`.pub` files and the Microsoft installers are **not** redistributed here. The
tools take a corpus path as an argument. Corpus statistics (counts, field value
distributions) are published in `notes/` because they are measurements, not
copies of the documents.

## Verification

A claim about a field layout is only final when a validator in `tools/` reads it
from every file in the corpus without a structural violation. Additions to a
chapter SHOULD come with the corresponding validator check.

## Naming

Use the file's own terminology where it can be recovered (chunk/block names from
the binary, Quill chunk names as literal 4-byte ASCII). Invented names are
allowed but must be marked `(working name)` the first time they appear.
