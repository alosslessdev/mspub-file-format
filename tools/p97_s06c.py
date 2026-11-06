"""Throwaway: decode 0x06 records under libmspub-derived hypotheses."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def load(corpora):
    files = []
    for c in corpora:
        for pat in ("*.PUB", "*.pub"):
            files += sorted(glob.glob(os.path.join(c, "**", pat), recursive=True))
    out = []
    for f in sorted(set(files)):
        try:
            doc = pubcore.parse_contents(f)
        except Exception:
            continue
        out.append(doc)
    return out

docs = load(sys.argv[1:] or ["p97/x"])
recs = [(d, ch) for d in docs for ch in d.chunks if ch.type_marker == 0x06]
print("docs=%d recs=%d" % (len(docs), len(recs)))

def docsize(d):
    for ch in d.chunks:
        if ch.type_marker == 0x15:
            return (struct.unpack_from("<i", ch.data, 0x14)[0],
                    struct.unpack_from("<i", ch.data, 0x18)[0], ch)
    return None

print("\n-- first 8 records, decoded --")
for d, ch in recs[:8]:
    b = ch.data
    x0, y0, x1, y1 = struct.unpack_from("<iiii", b, 6)
    ds = docsize(d)
    print("%-28s id=%#06x par=%#06x rot=%d geom=(%d,%d)-(%d,%d) [+4=%#06x]" % (
        os.path.basename(d.path), ch.id, ch.parent,
        struct.unpack_from("<H", b, 4)[0], x0, y0, x1, y1, struct.unpack_from("<H", b, 4)[0]))
    print("    docsize=%s  b31=%#04x b33=%#04x b32=%#04x u16@30=%#06x u32@2c=%#010x" % (
        (ds[0], ds[1]) if ds else None, b[0x31], b[0x33], b[0x32],
        struct.unpack_from("<H", b, 0x30)[0], struct.unpack_from("<I", b, 0x2c)[0]))
