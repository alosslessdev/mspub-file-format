"""Domains of u16/u32 fields at every offset in 53-byte 0x06 records."""
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
            recs.append((f, ch, doc))
print("n=%d files=%d" % (len(recs), len({r[0] for r in recs})))
for off in range(4, 52):
    if off + 2 > 53: break
    c16 = collections.Counter(struct.unpack_from("<H", ch.data, off)[0] for _, ch, _ in recs)
    line = "%02x u16 n=%3d: %s" % (off, len(c16), ", ".join("%d:%d" % (v, k) for v, k in c16.most_common(12)))
    if off + 4 <= 53:
        c32 = collections.Counter(struct.unpack_from("<I", ch.data, off)[0] for _, ch, _ in recs)
        vals = list(c32.most_common(6))
        line += "  || u32 n=%3d: %s" % (len(c32), ", ".join("%d:%d" % (v, k) for v, k in vals))
    print(line)
