"""Does a 0x06 record reference text? Compare candidate fields with chunk ids/text ids."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def files(c):
    out = []
    for pat in ("*.PUB", "*.pub"):
        out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))

docs = []
for f in files("p97/x"):
    try: docs.append(pubcore.parse_contents(f))
    except Exception: pass

# text ids referenced by type 0x00 shapes (libmspub: u16 @ +0x46)
hits = collections.Counter()
tot = 0
for d in docs:
    ids = {c.id for c in d.chunks}
    textids = {}
    for c in d.chunks:
        if c.type_marker == 0x00 and len(c.data) >= 0x48:
            tid = struct.unpack_from("<H", c.data, 0x46)[0]
            textids[tid] = c.id
    for c in d.chunks:
        if c.type_marker != 0x06 or len(c.data) != 53: continue
        b = c.data
        tot += 1
        for name, off, w in (("u16@0x16", 0x16, 2), ("u32@0x18", 0x18, 4), ("u32@0x1c", 0x1c, 4),
                             ("u16@0x20", 0x20, 2), ("u32@0x22", 0x22, 4), ("u32@0x26", 0x26, 4),
                             ("u16@0x2e", 0x2e, 2), ("u32@0x2c", 0x2c, 4), ("u16@0x30", 0x30, 2)):
            v = struct.unpack_from("<H" if w == 2 else "<I", b, off)[0]
            if v == 0: continue
            if v in textids: hits[name + " is text id"] += 1
            if v in ids: hits[name + " is chunk id"] += 1
print("records=%d" % tot)
for k, v in hits.most_common(): print("  %-22s %d" % (k, v))

# text ids per doc, and whether 0x06 records live in the same parent as text shapes
print("\nExample: AWARD.PUB text shapes and 0x06 siblings")
for d in docs:
    if not d.path.endswith("AWARD.PUB"): continue
    for c in d.chunks:
        if c.type_marker == 0x00 and len(c.data) >= 0x48:
            print("  text shape id=%#06x par=%#06x textId=%#06x" % (c.id, c.parent, struct.unpack_from("<H", c.data, 0x46)[0]))
        if c.type_marker == 0x06:
            print("  0x06 id=%#06x par=%#06x tail22=%s" % (c.id, c.parent, c.data[0x22:0x2a].hex()))
        if c.type_marker == 0x15:
            print("  DOC id=%#06x len=%d" % (c.id, len(c.data)))
            print("    u32@0x12=%#x" % struct.unpack_from("<I", c.data, 0x12)[0])
