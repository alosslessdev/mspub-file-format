import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]
u32=lambda b,o: struct.unpack_from("<i",b,o)[0]
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
boxok=collections.Counter(); contain=collections.Counter(); union=collections.Counter()
depthgroups=collections.Counter(); depthfiles=collections.Counter()
def box(c):
    d=c.data
    if len(d)<0x16: return None
    b=tuple(u32(d,o) for o in (6,10,14,18))
    if b[0]>b[2] or b[1]>b[3]: return None
    return b
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    byid={c.id:c for c in d.chunks}
    kids=collections.defaultdict(list)
    for c in d.chunks: kids[c.parent].append(c)
    seen=set()
    for k in d.chunks:
        if k.type_marker in (0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x0F) and k.parent in byid:
            p=byid[k.parent]
            if p.type_marker==0x0F: seen.add(k.type_marker)
    for g in d.of_type(0x0F):
        gb=box(g)
        if gb is None: boxok[('group', 'invalid')]+=1; continue
        ks=kids[g.id]
        cbs=[]
        for k in ks:
            b=box(k)
            if b is None:
                boxok[(hex(k.type_marker),'invalid')]+=1
                continue
            boxok[(hex(k.type_marker),'valid')]+=1
            cbs.append(b)
        if not cbs: continue
        tag='nested' if any(k.type_marker==0x0F for k in ks) else 'leaf'
        if gb==(0,0,0,0):
            contain[(tag,'degenerate_group_box')]+=1; continue
        ins=sum(1 for b in cbs if gb[0]<=b[0] and gb[1]<=b[1] and b[2]<=gb[2] and b[3]<=gb[3])
        contain[(tag,'all_inside' if ins==len(cbs) else ('some_inside' if ins else 'none_inside'))]+=1
        u=(min(b[0] for b in cbs),min(b[1] for b in cbs),max(b[2] for b in cbs),max(b[3] for b in cbs))
        union[(tag,'exact' if u==gb else 'inexact')]+=1
    # group depth per group
    for g in d.of_type(0x0F):
        n=0; cur=g
        while cur.parent in byid and n<64:
            cur=byid[cur.parent]
            if cur.type_marker==0x0F: n+=1
        depthgroups[n]+=1
print('bbox validity per type',dict(boxok))
print('containment',dict(contain))
print('union',dict(union))
print('group depth histogram',sorted(depthgroups.items()))
