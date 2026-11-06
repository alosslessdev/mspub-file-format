"""Geometry invariant tests for 0x06 records."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def files(corpora):
    out = []
    for c in corpora:
        for pat in ("*.PUB", "*.pub"):
            out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))

IN = 914400
rows = []
marks = collections.Counter()
for f in files(sys.argv[1:] or ["p97/x"]):
    try: doc = pubcore.parse_contents(f)
    except Exception: continue
    docch = next((c for c in doc.chunks if c.type_marker == 0x15), None)
    if not docch or len(docch.data) < 0x1c: continue
    mark = struct.unpack_from("<H", docch.data, 0x12)[0]
    W, H = struct.unpack_from("<II", docch.data, 0x14)
    marks[mark] += 1
    for ch in doc.chunks:
        if ch.type_marker != 0x06 or len(ch.data) != 53: continue
        a, b, c_, d = struct.unpack_from("<iiii", ch.data, 6)
        rows.append((f, ch, W, H, mark, a, b, c_, d))
print("records=%d  coordMark counter (per doc): %s" % (len(rows), marks.most_common()))

for name, off in (("identity", 0), ("-25in", 25*IN), ("-120in", 120*IN)):
    z = 0; inpage = 0; pos = 0; ord_ = 0
    bad = []
    for f, ch, W, H, mark, a, b, c_, d in rows:
        x0, y0, x1, y1 = a-off, b-off, c_-off, d-off
        if (a, b, c_, d) == (0, 0, 0, 0): z += 1; continue
        if x1 > x0 and y1 > y0: ord_ += 1
        if x0 >= 0 and y0 >= 0 and x1 <= W and y1 <= H: inpage += 1
        else: bad.append((os.path.basename(f), ch.id, x0, y0, x1, y1, W, H))
        if x0 >= 0 and y0 >= 0: pos += 1
    nz = len(rows) - z
    print("\n%s: zero-quad=%d nonzero=%d | x1>x0 and y1>y0: %d/%d (%.1f%%) | fully in page: %d/%d (%.1f%%) | x0>=0,y0>=0: %d/%d" % (
        name, z, nz, ord_, nz, 100.*ord_/max(nz,1), inpage, nz, 100.*inpage/max(nz,1), pos, nz))
    for r in bad[:6]: print("   miss:", r)
