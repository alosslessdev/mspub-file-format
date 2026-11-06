"""Per-byte distributions for 53-byte 0x06 records."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def files(corpora):
    out = []
    for c in corpora:
        for pat in ("*.PUB", "*.pub"):
            out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))

recs = []
for f in files(sys.argv[1:] or ["p97/x"]):
    try: doc = pubcore.parse_contents(f)
    except Exception: continue
    for ch in doc.chunks:
        if ch.type_marker == 0x06 and len(ch.data) == 53:
            recs.append((f, ch))
print("n=%d" % len(recs))
for o in range(53):
    c = collections.Counter(ch.data[o] for _, ch in recs)
    d = len(c)
    s = ", ".join("%02x:%d" % (v, n) for v, n in c.most_common(8))
    print("%02x  n=%2d  %s%s" % (o, d, s, " ..." if d > 8 else ""))
