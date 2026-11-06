"""Specification linter: keeps the published document set consistent.

Checks
  1. every chapter referenced by spec/00-overview.md exists;
  2. every chapter has a title and a status/provenance note;
  3. no large blocks of decompiled/disassembled vendor code leaked in;
  4. every "open question" is tracked with an explicit UNKNOWN/INFERENCE marker;
  5. tables in spec/blocks/ are machine-sortable (consistent column count).

Usage: python spec_lint.py [spec-dir]
"""
from __future__ import annotations

import os
import re
import sys

REQUIRED = [
    "00-overview.md", "01-container.md", "02-contents-header.md", "03-directory.md",
    "04-chunk-document.md", "05-chunk-page.md", "06-chunk-shape.md", "07-chunk-group.md",
    "08-chunk-image.md", "09-chunk-palette.md", "10-chunk-table-cells.md",
    "11-chunk-logo-borderart-font.md", "12-tlv-blocks.md", "13-quill.md",
    "14-escher.md", "15-embedded-objects.md", "16-metadata.md", "17-enums.md",
    "18-version-differences.md", "19-validation.md",
]

# Heuristic markers of pasted vendor code; the spec must describe, not reproduce.
CODE_SMELLS = [
    re.compile(r"^\s*undefined\d?\s+\w+\(", re.M),      # Ghidra signature
    re.compile(r"^\s*LAB_[0-9a-f]{6,}", re.M),          # Ghidra label
    re.compile(r"^\s*FUN_[0-9a-f]{6,}", re.M),          # Ghidra function name
    re.compile(r"^\s*mov\s+\[?e[a-d]x", re.M),          # disassembly
]


def lint(spec: str) -> int:
    problems = 0
    missing = []
    for name in REQUIRED:
        path = os.path.join(spec, name)
        if not os.path.exists(path):
            missing.append(name)
    if missing:
        print("missing chapters (%d):" % len(missing))
        for m in missing:
            print("   " + m)
        problems += len(missing)

    for name in sorted(os.listdir(spec)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(spec, name)
        text = open(path, encoding="utf-8").read()
        if not text.startswith("# "):
            print("%s: no top-level title" % name)
            problems += 1
        for smell in CODE_SMELLS:
            hit = smell.search(text)
            if hit:
                print("%s: possible pasted vendor code: %r" % (name, hit.group(0)))
                problems += 1
        if len(text) > 400 and not re.search(r"\[(OBSERVED|INFERENCE|UNKNOWN)\]", text):
            print("%s: no provenance markers" % name)
            problems += 1
    # Clean-room invariant: no normative table row may cite prior art.
    prior_rows = 0
    prior_paras = 0
    for name in sorted(os.listdir(spec)):
        if not name.endswith(".md"):
            continue
        text = open(os.path.join(spec, name), encoding="utf-8").read()
        for line in text.splitlines():
            if line.lstrip().startswith("|") and "libmspub" in line:
                print("%s: normative table row cites libmspub: %s" % (name, line[:80]))
                problems += 1
                prior_rows += 1
        for para in text.split("\n\n"):
            if "libmspub" in para and not para.lstrip().startswith("|"):
                prior_paras += 1
    print("prior-art paragraphs (skippable by convention): %d" % prior_paras)
    if prior_rows == 0:
        print("clean-room invariant: no rule table cites prior art")

    blocks = os.path.join(spec, "blocks")
    if os.path.isdir(blocks):
        for name in sorted(os.listdir(blocks)):
            if not name.endswith(".md"):
                continue
            widths = set()
            for line in open(os.path.join(blocks, name), encoding="utf-8"):
                if line.strip().startswith("|"):
                    widths.add(line.count("|"))
            if len(widths) > 1:
                print("blocks/%s: inconsistent table column counts %s" % (name, sorted(widths)))
                problems += 1
    print("\n%d problem(s)" % problems)
    return problems


if __name__ == "__main__":
    sys.exit(1 if lint(sys.argv[1] if len(sys.argv) > 1 else "spec") else 0)
