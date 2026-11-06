import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u32=lambda b,o: struct.unpack_from('<I',b,o)[0]
def box(c):
    d=c.data
    if len(d)<0x16: return None
    b=tuple(u32(d,o) for o in (6,10,14,18))
    if b[0]>b[2] or b[1]>b[3]: return None
    return b
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
r=collections.Counter(); depth=collections.Counter(); tree=collections.Counter()
relgroup=collections.Counter(); examples=[]
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    ids={c.id for c in d.chunks}
    kids=collections.defaultdict(list)
    for c in d.chunks: kids[c.parent].append(c)
    # tree checks
    for c in d.chunks:
        if c.parent!=0 and c.parent not in ids: tree['orphan']+=1
        if c.parent==c.id: tree['self']+=1
    # depth: walk up from each chunk
    def depth_of(c,seen=None):
        n=0; cur=c
        while cur.parent in ids and n<100:
            cur=next(x for x in d.chunks if x.id==cur.parent); n+=1
        return n
    maxd=0
    for g in d.of_type(0x0F):
        gb=box(g)
        if gb is None: continue
        for k in d.chunks:
            if k.parent!=g.id: continue
            kb=box(k)
            if not kb: continue
            if gb[0]==0 and gb[1]==0:
                relgroup['parent_zero_origin']+=1; continue
            if kb[0]<gb[0] and kb[1]<gb[1]: relgroup['child_below_both']+=1
            elif kb[0]>=gb[0] and kb[1]>=gb[1] and kb[2]<=gb[2] and kb[3]<=gb[3]: relgroup['child_inside']+=1
            elif kb[0]>=gb[0] and kb[1]>=gb[1]: relgroup['child_offset_overlap']+=1
            else: relgroup['other']+=1
    # max nesting via parent chain of 0x0F
    for g in d.of_type(0x0F):
        n=0;cur=g
        while True:
            par=[x for x in d.chunks if x.id==cur.parent]
            if not par: break
            cur=par[0]
            if cur.type_marker==0x0F: n+=1
            if n>50: break
        maxd=max(maxd,n)
    depth[maxd]+=1
print('pair classification',relgroup)
print('per-file max group nesting depth',sorted(depth.items()))
print('tree',tree)
