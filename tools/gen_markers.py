"""Generate spec/blocks/chunk-markers.md from the corpus.

One row per chunk type marker: instance count, modal payload size, the writer-side
fixed record length byte B (chapter 12), per-version counts, and whether a spec
chapter documents the marker under a heading (`### 4.2 ... 0x0000 ...`).

Usage: python gen_markers.py
"""
from __future__ import annotations

import collections
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

CFB = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
CORPORA = [("P95", "p95/x"), ("P97", "p97/x"), ("P97D", "p97deluxe/x"), ("P98", "p98/x")]


def corpus_files(path):
    fs = glob.glob(os.path.join(path, "**", "*.PUB"), recursive=True)
    fs += [f for f in glob.glob(os.path.join(path, "**", "*.JSP"), recursive=True)
           if open(f, "rb").read(8) == CFB]
    return fs


def documented_markers():
    """Markers written in inline code (`` `0x0015` ``) in a chapter.

    That is the convention this specification uses when a chapter gives a marker a
    layout entry, so it is a better signal than a bare mention.
    """
    found = set()
    for path in glob.glob(os.path.join("spec", "*.md")):
        text = open(path, encoding="utf-8").read()
        if path.endswith("blocks/chunk-markers.md"):
            continue
        for hexv in re.findall(r"`0x([0-9A-Fa-f]{4})`", text):
            found.add(int(hexv, 16))
    return found


def main():
    data = {}
    for label, path in CORPORA:
        for f in corpus_files(path):
            try:
                doc = pubcore.parse_contents(f)
            except Exception:
                continue
            for c in doc.chunks:
                d = data.setdefault(c.type_marker, {
                    "count": 0, "sizes": collections.Counter(), "ver": collections.Counter(),
                    "B": collections.Counter()})
                d["count"] += 1
                d["sizes"][c.size] += 1
                d["ver"][label] += 1
                d["B"][c.data[3]] += 1

    documented = documented_markers()
    out = [
        "# Chunk marker reference table",
        "",
        "Machine-generated from the 493-document corpus by `tools/gen_markers.py`. One row",
        "per chunk type marker. `B` is the writer-side fixed record length byte at chunk",
        "`+0x03` (chapter 12); it does not grow with the optional counted tail. Sizes are",
        "the modal payload size and its share of instances.",
        "",
        "`Layout` is `yes` when some chapter names the marker in inline code (the convention",
        "used for a layout entry); `-` means the marker is observed but undocumented.",
        "",
        "| Marker | Name | Count | Modal size | Size modes | B | P95 | P97 | P97D | P98 | Layout |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m, d in sorted(data.items()):
        mode, count = d["sizes"].most_common(1)[0]
        sizes = ", ".join("%d×%d" % (s, n) for s, n in d["sizes"].most_common(3))
        bs = ", ".join(str(v) for v, _ in d["B"].most_common(3))
        out.append("| `%#06x` | %s | %d | %d (%.0f%%) | %s | %s | %d | %d | %d | %d | %s |" % (
            m, pubcore.CHUNK_TYPES.get(m, "?"), d["count"], mode, 100.0 * count / d["count"],
            sizes, bs, d["ver"].get("P95", 0), d["ver"].get("P97", 0),
            d["ver"].get("P97D", 0), d["ver"].get("P98", 0),
            "yes" if m in documented else "-"))
    out += ["", "Totals: %d markers, %d instances." % (
        len(data), sum(d["count"] for d in data.values())), ""]
    with open(os.path.join("spec", "blocks", "chunk-markers.md"), "w", encoding="utf-8") as w:
        w.write("\n".join(out))
    print("wrote %d markers, %d documented" % (len(data), sum(1 for m in data if m in documented)))


if __name__ == "__main__":
    main()
