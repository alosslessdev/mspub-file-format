"""Find rotation evidence: swapped-dimension siblings; group match split by rotation."""
import sys, os, struct, glob, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

files = sorted(set(glob.glob('p97/x/*.PUB')))
docs = []
for f in files:
    try: docs.append(pubcore.parse_contents(f))
    except Exception: pass

def quad(c): return struct.unpack_from("<iiii", c.data, 6)
def rot(c): return struct.unpack_from("<H", c.data, 4)[0]

# group match split
ok_norot = tot_norot = ok_rot = tot_rot = 0
for d in docs:
    for g in d.chunks:
        if g.type_marker != 0x0F or len(g.data) < 0x16: continue
        kids = [c for c in d.chunks if c.parent == g.id and len(c.data) >= 0x16 and c.type_marker in (0,1,2,4,5,6,7,8,0x0F)]
        kq = [quad(k) for k in kids if quad(k) != (0,0,0,0)]
        if not kq: continue
        union = (min(q[0] for q in kq), min(q[1] for q in kq), max(q[2] for q in kq), max(q[3] for q in kq))
        anyrot = any(rot(k) for k in kids)
        if anyrot:
            tot_rot += 1; ok_rot += (quad(g) == union)
        else:
            tot_norot += 1; ok_norot += (quad(g) == union)
print("group bbox == union(children):  no rotated child %d/%d (%.1f%%) ; has rotated child %d/%d (%.1f%%)" % (
    ok_norot, tot_norot, 100.*ok_norot/max(tot_norot,1), ok_rot, tot_rot, 100.*ok_rot/max(tot_rot,1)))

# swapped-dimension siblings in the same group with a 90-degree rotation difference
found = 0
for d in docs:
    groups = collections.defaultdict(list)
    for c in d.chunks:
        if c.type_marker == 0x06 and len(c.data) == 53:
            groups[c.parent].append(c)
    for gid, kids in groups.items():
        for a, b in itertools.combinations(kids, 2):
            qa, qb = quad(a), quad(b)
            wa, ha = qa[2]-qa[0], qa[3]-qa[1]
            wb, hb = qb[2]-qb[0], qb[3]-qb[1]
            if wa and ha and wb and hb and wa == hb and ha == wb and wa != ha:
                ra, rb = rot(a), rot(b)
                if abs(ra - rb) in (900, 2700):
                    found += 1
                    if found <= 6:
                        print("\nSWAP PAIR %s group=%#x  a=%#x rot=%d (%dx%d)  b=%#x rot=%d (%dx%d)" % (
                            os.path.basename(d.path), gid, a.id, ra, wa, ha, b.id, rb, wb, hb))
                        for c in (a, b):
                            print("   id=%#06x quad=(%d,%d)-(%d,%d) bytes16=%s" % (
                                c.id, *quad(c), c.data[0x16:0x24].hex()))
print("\nswapped-dimension pairs with 90-deg difference: %d" % found)
