import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
order=collections.Counter(); dupids=collections.Counter(); roots=collections.Counter()
cycle=0; selfp=0; idmatch=collections.Counter(); flagrot=collections.Counter()
rotdist=collections.Counter(); ver=collections.Counter()
childcounter=collections.Counter(); grpflag=collections.Counter()
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    offs=[c.offset for c in d.chunks]
    order['dir==offset' if offs==sorted(offs) else 'dir!=offset']+=1
    ids=[c.id for c in d.chunks]
    dupids['dup' if len(ids)!=len(set(ids)) else 'unique']+=1
    idsset=set(ids)
    roots[sum(1 for c in d.chunks if c.parent not in idsset)]+=1
    for c in d.chunks:
        if c.parent==c.id: selfp+=1
        # cycle detection
        seen=[]; cur=c
        while cur.parent in idsset and len(seen)<200:
            if cur.parent in seen: cycle+=1; break
            seen.append(cur.id)
            cur=next(x for x in d.chunks if x.id==cur.parent)
    byid={c.id:c for c in d.chunks}
    kids=collections.Counter()
    for c in d.chunks:
        if c.parent in byid: kids[c.parent]+=1
    for g in d.of_type(0x0F):
        ver[g.data[2:4].hex()]+=1
        p=g.data
        n=len([c for c in d.chunks if c.parent==g.id])
        grpflag[(u16(p,0x16), n==u16(p,0x18), n==u16(p,0x1a), u16(p,0x1c))]+=1
        rotdist[u16(p,4)]+=1
        flagrot[(u16(p,0x16), 'rot' if u16(p,4) else 'norot')]+=1
print('dir vs offset order',order)
print('ids',dupids,'roots per file',roots,'self parent',selfp,'cycles',cycle)
print('group version bytes',ver)
print('rotation values',sorted(rotdist.items()))
print('flag x rot',flagrot)
print('flag/count layout',grpflag.most_common(8))
