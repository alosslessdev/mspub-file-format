"""Build a JSON index of every .PUB file in a corpus.

Records container facts only (no field interpretation), so it is safe for all
version coordinators to share: streams, version magic, chunk counts by type,
file size and hashes.

Usage: python corpus_index.py <corpus>... -o notes/corpus-index.json
"""
from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore


def describe(path: str) -> dict:
    rec = {
        "path": path.replace("\\", "/"),
        "size": os.path.getsize(path),
        "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest(),
    }
    try:
        rec["streams"] = pubcore.list_streams(path)
    except Exception as e:
        rec["error"] = "streams: %s" % e
        return rec
    try:
        doc = pubcore.parse_contents(path)
    except Exception as e:
        rec["error"] = "contents: %s" % e
        return rec
    rec["version_magic"] = doc.version_magic
    rec["trailer_offset"] = doc.trailer_offset
    rec["directory_count"] = doc.directory_count
    rec["chunk_count"] = len(doc.chunks)
    counts = collections.Counter(c.type_name for c in doc.chunks)
    rec["chunk_types"] = dict(sorted(counts.items()))
    rec["has_quill"] = any("Quill" in s for s in rec["streams"])
    rec["has_escher"] = any("Escher" in s for s in rec["streams"])
    rec["object_storages"] = sum(1 for s in rec["streams"] if s.startswith("storage\tObject "))
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpora", nargs="+")
    ap.add_argument("-o", "--out", default="notes/corpus-index.json")
    a = ap.parse_args()
    index = []
    for corpus in a.corpora:
        files = sorted(glob.glob(os.path.join(corpus, "**", "*.PUB"), recursive=True))
        files += sorted(f for f in glob.glob(os.path.join(corpus, "**", "*.JSP"), recursive=True)
                        if open(f, "rb").read(8) == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        print("%s: %d files" % (corpus, len(files)))
        for f in files:
            index.append(describe(f))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as w:
        json.dump(index, w, indent=1)
    ok = [r for r in index if "error" not in r]
    vers = collections.Counter(r.get("version_magic") for r in ok)
    print("indexed %d/%d ok, version magics %s -> %s" % (len(ok), len(index), dict(vers), a.out))


if __name__ == "__main__":
    main()
