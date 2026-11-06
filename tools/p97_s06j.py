"""Shape record (type,len,A,B) census per corpus."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def files(corpora):
    out = []
    for c in corpora:
        for pat in ("*.PUB", "*.pub"):
            out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))

for corpus in (sys.argv[1:] or ["p97/x"]):
    per = collections.Counter()
    n = 0
    for f in files([corpus]):
        try: doc = pubcore.parse_contents(f)
        except Exception: continue
        for ch in doc.chunks:
            if ch.type_marker <= 0x08 or ch.type_marker == 0x0F:
                n += 1
                per[(ch.type_marker, len(ch.data), struct.unpack_from("<H", ch.data, 2)[0])] += 1
    print("== %s  shape-ish chunks=%d" % (corpus, n))
    for (t, ln, ab), k in sorted(per.items()):
        print("   type=%#05x len=%3d AB=%#06x (A=%#04x B=%#04x) x%d  %s" % (
            t, ln, ab, ab >> 8, ab & 0xff, k, "B==len" if (ab & 0xff) == ln else ("B==len-10" if (ab & 0xff) == ln - 10 else "")))
