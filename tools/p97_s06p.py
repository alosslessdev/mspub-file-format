"""Group-bbox vs children, monotonicity, text-id falsification."""
import sys, os, struct, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

files = sorted(set(glob.glob('p97/x/*.PUB')))
docs = []
for f in files:
    try: docs.append(pubcore.parse_contents(f))
    except Exception: pass

def quad(c):
    return struct.unpack_from("<iiii", c.data, 6)

# (a) group quad vs union of children quads
exact_same = 0; total = 0; rot_in = 0; mism = []
for d in docs:
    byid = {c.id: c for c in d.chunks}
    for g in d.chunks:
        if g.type_marker != 0x0F or len(g.data) < 0x16: continue
        kids = [c for c in d.chunks if c.parent == g.id and c.type_marker in (0x00,0x01,0x02,0x04,0x05,0x06,0x07,0x08,0x0F)]
        if not kids: continue
        kq = [quad(k) for k in kids if len(k.data) >= 0x16 and quad(k) != (0,0,0,0)]
        if not kq: continue
        gq = quad(g)
        union = (min(q[0] for q in kq), min(q[1] for q in kq), max(q[2] for q in kq), max(q[3] for q in kq))
        total += 1
        hasrot = any(struct.unpack_from("<H", k.data, 4)[0] for k in kids if len(k.data) >= 6)
        if hasrot: rot_in += 1
        if gq == union: exact_same += 1
        elif len(mism) < 6: mism.append((os.path.basename(d.path), g.id, gq, union, hasrot))
print("groups=%d  group_quad == union(children) : %d (%.1f%%)  groups containing a rotated child: %d" % (
    total, exact_same, 100.*exact_same/total, rot_in))
for m in mism: print("   mismatch:", m)

# (b) monotonicity of x0/y0 across 0x06 records on the same page (page = nearest ancestor with type 0x14)
print("\n(b) monotonicity")
def page_of(d, ch):
    byid = {c.id: c for c in d.chunks}
    seen = set()
    cur = ch
    while cur.parent in byid and cur.id not in seen:
        seen.add(cur.id)
        cur = byid[cur.parent]
        if cur.type_marker == 0x14: return cur.id
    return None
tot = 0; monox = 0; monoy = 0
for d in docs:
    pages = collections.defaultdict(list)
    for c in d.chunks:
        if c.type_marker == 0x06 and len(c.data) == 53:
            p = page_of(d, c)
            if p is not None: pages[p].append(c)
    for p, lst in pages.items():
        for a, b in zip(lst, lst[1:]):
            qa, qb = quad(a), quad(b)
            if qa == (0,0,0,0) or qb == (0,0,0,0): continue
            tot += 1
            if qb[0] >= qa[0]: monox += 1
            if qb[1] >= qa[1]: monoy += 1
print("adjacent pairs on same page: %d ; x0 non-decreasing %d (%.1f%%) ; y0 non-decreasing %d (%.1f%%)" % (
    tot, monox, 100.*monox/max(tot,1), monoy, 100.*monoy/max(tot,1)))

# (c) text ids in each doc: u16@0x46 of type 0x00 chunks
print("\n(c) text-id space vs candidate fields in 0x06")
hit = collections.Counter(); n = 0
for d in docs:
    tids = set()
    for c in d.chunks:
        if c.type_marker == 0x00 and len(c.data) >= 0x48:
            tids.add(struct.unpack_from("<H", c.data, 0x46)[0])
    if not tids: continue
    for c in d.chunks:
        if c.type_marker != 0x06: continue
        n += 1
        v = struct.unpack_from("<I", c.data, 0x1c)[0]
        if v in tids: hit["u32@0x1C"] += 1
        v = struct.unpack_from("<I", c.data, 0x18)[0]
        if v in tids: hit["u32@0x18"] += 1
print("records=%d ; matches: %s" % (n, dict(hit)))
c = collections.Counter(struct.unpack_from("<I", ch.data, 0x1c)[0] for d in docs for ch in d.chunks if ch.type_marker == 0x06)
print("u32@0x1C overall domain:", c.most_common(6))
