import sys, os, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
p = sys.argv[1]
doc = pubcore.parse_contents(p)
for ch in doc.chunks:
    if ch.type_marker in (0x00, 0x01, 0x05, 0x06, 0x07):
        print("== type=%#05x id=%#06x par=%#06x off=%#x len=%d" % (ch.type_marker, ch.id, ch.parent, ch.offset, len(ch.data)))
        b = ch.data
        for o in range(0, len(b), 16):
            seg = b[o:o+16]
            print("  %02x %-47s %s" % (o, " ".join("%02x" % v for v in seg),
                  "".join(chr(v) if 32 <= v < 127 else "." for v in seg)))
