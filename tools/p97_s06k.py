"""Cluster 0x06 records by tail signature; print raw hex for exemplars."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def files(c):
    out = []
    for pat in ("*.PUB", "*.pub"):
        out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))

recs = []
for f in files(sys.argv[1] if len(sys.argv) > 1 else "p97/x"):
    try: doc = pubcore.parse_contents(f)
    except Exception: continue
    for ch in doc.chunks:
        if ch.type_marker == 0x06 and len(ch.data) == 53:
            recs.append((f, ch))

# signature: which tail bytes are zero
sig = collections.Counter()
for f, ch in recs:
    b = ch.data
    mask = "".join("0" if b[i] == 0 else "1" for i in range(0x16, 53))
    sig[mask] += 1
print("distinct tail zero-masks:", len(sig))
for m, k in sig.most_common(15):
    print("  %3d  %s" % (k, m))

# group by byte 0x1b / 0x22..0x26 patterns
print("\n-- exemplars with b[0x1b] != 0 --")
n = 0
for f, ch in recs:
    b = ch.data
    if b[0x1b] != 0 and n < 4:
        n += 1
        print("%-24s id=%#06x par=%#06x" % (os.path.basename(f), ch.id, ch.parent))
        for o in range(0, 53, 16):
            print("   %02x %s" % (o, " ".join("%02x" % v for v in b[o:o+16])))
print("\n-- exemplars with b[0x1b] == 0 and b[0x31]!=0 --")
n = 0
for f, ch in recs:
    b = ch.data
    if b[0x1b] == 0 and b[0x31] != 0 and n < 4:
        n += 1
        print("%-24s id=%#06x par=%#06x" % (os.path.basename(f), ch.id, ch.parent))
        for o in range(0, 53, 16):
            print("   %02x %s" % (o, " ".join("%02x" % v for v in b[o:o+16])))
print("\n-- exemplars with all-zero tail --")
n = 0
for f, ch in recs:
    b = ch.data
    if all(v == 0 for v in b[0x16:]) and n < 3:
        n += 1
        print("%-24s id=%#06x par=%#06x" % (os.path.basename(f), ch.id, ch.parent))
        for o in range(0, 53, 16):
            print("   %02x %s" % (o, " ".join("%02x" % v for v in b[o:o+16])))
