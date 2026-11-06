import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
p = sys.argv[1]
doc = pubcore.parse_contents(p)
docch = next((c for c in doc.chunks if c.type_marker == 0x15), None)
mark = struct.unpack_from("<H", docch.data, 0x12)[0]
W, H = struct.unpack_from("<II", docch.data, 0x14)
print("doc %s mark=%#06x W=%d (%.2f in) H=%d (%.2f in)" % (os.path.basename(p), mark, W, W/914400., H, H/914400.))
SHAPES = {0x00,0x01,0x02,0x04,0x05,0x06,0x07,0x08,0x0F}
print("%-5s %-7s %-7s %6s  %-28s %-28s %s" % ("type","id","par","size","quad@6 (raw)","-25in","in-page"))
for ch in doc.chunks:
    if ch.type_marker not in SHAPES: continue
    b = ch.data
    if len(b) < 0x16: 
        print("%#05x %#06x %#06x %6d  <short>" % (ch.type_marker, ch.id, ch.parent, len(b))); continue
    x0,y0,x1,y1 = struct.unpack_from("<iiii", b, 6)
    t = [(v - 22860000) for v in (x0,y0,x1,y1)]
    ok = all(0 <= v <= lim for v, lim in zip(t, (W,H,W,H)))
    print("%#05x %#06x %#06x %6d  (%d,%d)-(%d,%d)  (%d,%d)-(%d,%d) %s" % (
        ch.type_marker, ch.id, ch.parent, len(b), x0,y0,x1,y1, t[0],t[1],t[2],t[3], "OK" if ok else ""))
