import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
p = sys.argv[1]
doc = pubcore.parse_contents(p)
want = [int(x, 16) for x in sys.argv[2:]] if len(sys.argv) > 2 else None
for ch in doc.chunks:
    if ch.type_marker != 0x06: continue
    if want and ch.id not in want: continue
    print("== id=%#06x parent=%#06x off=%#x size=%d" % (ch.id, ch.parent, ch.offset, len(ch.data)))
    b = ch.data
    for o in range(0, len(b), 16):
        seg = b[o:o+16]
        print("  %02x (abs %#08x)  %-47s %s" % (o, ch.offset+o, " ".join("%02x" % v for v in seg),
              "".join(chr(v) if 32 <= v < 127 else "." for v in seg)))
