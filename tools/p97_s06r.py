"""Does the group bbox equal the AABB of the rotated child frame?"""
import sys, os, struct, glob, math, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

files = sorted(set(glob.glob('p97/x/*.PUB')))
docs = []
for f in files:
    try: docs.append(pubcore.parse_contents(f))
    except Exception: pass

def quad(c): return struct.unpack_from("<iiii", c.data, 6)
def rot(c): return struct.unpack_from("<H", c.data, 4)[0]

def aabb(q, deg):
    x0, y0, x1, y1 = q
    cx, cy = (x0+x1)/2.0, (y0+y1)/2.0
    t = math.radians(deg)
    xs, ys = [], []
    for px, py in ((x0,y0),(x1,y0),(x1,y1),(x0,y1)):
        dx, dy = px-cx, py-cy
        xs.append(cx + dx*math.cos(t) - dy*math.sin(t))
        ys.append(cy + dx*math.sin(t) + dy*math.cos(t))
    return (min(xs), min(ys), max(xs), max(ys))

ok = tot = 0; shown = 0
for d in docs:
    for g in d.chunks:
        if g.type_marker != 0x0F or len(g.data) < 0x16: continue
        kids = [c for c in d.chunks if c.parent == g.id and len(c.data) >= 0x16 and
                c.type_marker in (0,1,2,4,5,6,7,8)]
        if len(kids) != 1: continue
        k = kids[0]
        if not rot(k) or quad(k) == (0,0,0,0): continue
        tot += 1
        gq = quad(g)
        pred = aabb(quad(k), rot(k)/10.0)
        err = max(abs(a-b) for a, b in zip(gq, pred))
        if err < 2000: ok += 1
        if shown < 5:
            shown += 1
            print("%-16s grp=%#06x rot10=%4d child quad=%s" % (os.path.basename(d.path), g.id, rot(k), quad(k)))
            print("                 group quad=%s predicted AABB=(%.0f,%.0f,%.0f,%.0f) maxerr=%.0f" % (gq, *pred, err))
print("\nsingle-rotated-child groups: %d ; AABB prediction within 2000 EMU: %d (%.0f%%)" % (tot, ok, 100.*ok/max(tot,1)))
