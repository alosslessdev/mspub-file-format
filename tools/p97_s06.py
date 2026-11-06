"""Throwaway: census of 0x06 chunks."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

CORPORA = sys.argv[1:] or ["p97/x", "p95/x"]

files = []
for c in CORPORA:
    files += sorted(glob.glob(os.path.join(c, "**", "*.PUB"), recursive=True))
    files += sorted(glob.glob(os.path.join(c, "**", "*.pub"), recursive=True))

recs = []
errs = []
for f in files:
    try:
        doc = pubcore.parse_contents(f)
    except Exception as e:
        errs.append((f, repr(e)))
        continue
    for ch in doc.chunks:
        if ch.type_marker == 0x06:
            recs.append((f, ch, doc))

print("files=%d ok, errs=%d, 0x06 chunks=%d" % (len(files) - len(errs), len(errs), len(recs)))
sizes = collections.Counter(len(c.data) for _, c, _ in recs)
print("sizes:", sizes.most_common())
print("payload[2:4]:", collections.Counter(c.data[2:4].hex() for _, c, _ in recs).most_common(5))
print("parent types:", collections.Counter(
    (next((p.type_name for p in d.chunks if p.id == c.parent), "ROOT")) for _, c, d in recs).most_common())
print("seq_skip vals:", collections.Counter(c.seq_skip for _, c, _ in recs).most_common())
