import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u32=lambda b,o: struct.unpack_from('<I',b,o)[0]
BOX=(6,0x0A,0x0E,0x12)
def box(c):
    d=c.data
    if len(d)<0x16: return None
    b=tuple(u32(d,o) for o in BOX)
    if b[0]>b[2] or b[1]>b[3]: return None
    return b
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
res=collections.Counter(); union=collections.Counter(); nested=collections.Counter()
bad=[]
zero=0
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    byid={c.id:c for c in d.chunks}
    for g in d.of_type(0x0F):
        gb=box(g)
        if gb is None: res['badbox']+=1; continue
        if gb==(0,0,0,0): zero+=1; continue
        kids=[byid[k.id] for k in d.chunks if k.parent==g.id]
        cb=[box(k) for k in kids]; cb=[b for b in cb if b]
        if not cb: continue
        is_nested = any(k.type_marker==0x0F for k in kids)
        tag='nested' if is_nested else 'leaf'
        ins=all(gb[0]<=b[0] and gb[1]<=b[1] and b[2]<=gb[2] and b[3]<=gb[3] for b in cb)
        res[(tag,'inside' if ins else 'outside')]+=1
        u=(min(b[0] for b in cb),min(b[1] for b in cb),max(b[2] for b in cb),max(b[3] for b in cb))
        union[(tag,'eq' if u==gb else 'ne')]+=1
        if not ins and len(bad)<8:
            bad.append((os.path.basename(f),hex(g.id),tag,[hex(v) for v in gb],[hex(v) for v in u]))
print('zero bbox groups',zero)
print(res); print(union)
for b in bad: print(b)
