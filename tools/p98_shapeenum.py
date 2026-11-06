"""Shape/chunk-marker enumeration census (P95/P97/P98 corpora).

Produces:
  * global chunk marker histogram
  * per-byte value histograms for markers 0x00/0x01/0x03/0x04/0x05/0x06/0x07
  * for each marker, the list of byte offsets whose value set is small
Run: python tools/p98_shapeenum.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
import p98_corpus as pc

CORPORA = {
    "p95": "p95/x",
    "p97": "p97/ext2",
    "p97deluxe": "p97deluxe/x",
    "p98": "p98/x",
}
P98_ONLY = ["p98/x/MSPUB.PUB", "p98/x/ZMSPUB.PUB", "p98/x/CHEKLIST.JSP",
            "p98/x/CLRCHK.JSP", "p98/x/INFOSHET.JSP"]


def load_all():
    docs = []
    for tag, d in CORPORA.items():
        files = pc.pub_files(d) if os.path.isdir(d) else []
        if tag == "p98":
            files = [f for f in P98_ONLY if os.path.exists(f)]
        for f in files:
            try:
                docs.append((tag, f, pubcore.parse_contents(f)))
            except Exception as e:  # noqa: BLE001
                print(f"!! {f}: {e}")
    return docs


def main():
    docs = load_all()
    print(f"documents: {len(docs)}")
    markers = Counter()
    per_marker_bytes = defaultdict(lambda: defaultdict(Counter))
    sizes = defaultdict(Counter)
    for tag, f, doc in docs:
        for c in doc.chunks:
            markers[c.type_marker] += 1
            sizes[c.type_marker][len(c.data)] += 1
            if c.type_marker <= 0x08 or c.type_marker in (0x0F, 0x16):
                d = c.data
                for i in range(len(d)):
                    per_marker_bytes[c.type_marker][i][d[i]] += 1

    print("\n== marker histogram ==")
    for m, n in sorted(markers.items()):
        print(f"0x{m:04X} {n:6d}  sizes={dict(sizes[m].most_common(4))}")

    for m in sorted(per_marker_bytes):
        print(f"\n== marker 0x{m:04X}: varying bytes ==")
        for off in sorted(per_marker_bytes[m]):
            cnt = per_marker_bytes[m][off]
            if len(cnt) <= 12:
                top = ", ".join(f"{v:#04x}x{n}" for v, n in cnt.most_common())
                print(f"  +0x{off:02X}: {top}")


if __name__ == "__main__":
    main()
