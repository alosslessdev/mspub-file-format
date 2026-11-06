"""Publisher 98 corpus harness: walk every .PUB, index chunks, cache payloads.

Usage (as a library):
    import p98_corpus as pc
    docs = pc.load('p98/x')                 # [(path, Document)] parsed via pubcore
    rows = pc.index(docs)                   # [(path, Chunk)]
    pc.write_index(rows, 'notes/p98/chunk_index.tsv')

Usage (as a script):
    python tools/p98_corpus.py <corpus-dir> <out-tsv>
"""
from __future__ import annotations

import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore


def pub_files(corpus: str):
    return sorted(f for f in glob.glob(os.path.join(corpus, "**", "*"), recursive=True)
                  if f.lower().endswith(".pub") and os.path.isfile(f))


def load(corpus: str):
    out = []
    for f in pub_files(corpus):
        try:
            out.append((f, pubcore.parse_contents(f)))
        except Exception as exc:  # unreadable / not a Publisher doc
            out.append((f, exc))
    return out


def docs_only(pairs):
    return [(p, d) for p, d in pairs if not isinstance(d, Exception)]


def index(pairs):
    rows = []
    for path, doc in docs_only(pairs):
        for c in doc.chunks:
            rows.append((path, c))
    return rows


def write_index(rows, out_path):
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write("file\tindex\tid\tparent\tseq_skip\toffset\ttype_marker\ttype_name\tsize\n")
        for path, c in rows:
            fh.write("%s\t%d\t0x%04x\t0x%04x\t0x%04x\t0x%x\t0x%04x\t%s\t%d\n" % (
                os.path.basename(path), c.index, c.id, c.parent, c.seq_skip,
                c.offset, c.type_marker, c.type_name, c.size))


def type_histogram(rows):
    return collections.Counter(c.type_marker for _, c in rows)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    corpus, out = sys.argv[1], sys.argv[2]
    pairs = load(corpus)
    ok = docs_only(pairs)
    bad = [p for p, d in pairs if isinstance(d, Exception)]
    print("files=%d parsed=%d failed=%d" % (len(pairs), len(ok), len(bad)))
    for p in bad[:10]:
        print("  FAILED", p)
    rows = index(pairs)
    write_index(rows, out)
    hist = type_histogram(rows)
    print("chunks=%d" % len(rows))
    for t, n in sorted(hist.items()):
        print("  0x%04x %-16s %d" % (t, pubcore.CHUNK_TYPES.get(t, "?"), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
