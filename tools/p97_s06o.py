"""Annotated fixed-offset decode of 0x06 records."""
import sys, os, struct, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def show(b, indent="  "):
    for o in range(0x16, 53, 8):
        seg = b[o:o+8]
        print("%s%02x: %s" % (indent, o, " ".join("%02x" % v for v in seg)))

for fn in sys.argv[1:]:
    d = pubcore.parse_contents(fn)
    docch = next((c for c in d.chunks if c.type_marker == 0x15), None)
    W, H = struct.unpack_from("<II", docch.data, 0x14)
    print("\n=== %s  W=%d H=%d" % (os.path.basename(fn), W, H))
    for c in d.chunks:
        if c.type_marker != 0x06: continue
        b = c.data
        x0, y0, x1, y1 = struct.unpack_from("<iiii", b, 6)
        rot = struct.unpack_from("<H", b, 4)[0]
        print("id=%#06x par=%#06x rot10=%d quad=(%d,%d)-(%d,%d)" % (c.id, c.parent, rot, x0, y0, x1, y1))
        show(b)
