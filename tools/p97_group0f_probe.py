import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u32=lambda b,o: struct.unpack_from('<I',b,o)[0]
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
c=collections.defaultdict(collections.Counter)
rel=collections.Counter()
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    for g in d.of_type(0x0F):
        p=g.data; n=len([x for x in d.chunks if x.parent==g.id])
        for off in (4,0x16,0x18,0x1a,0x1c,0x1e,0x20):
            c[hex(off)][u16(p,off)]+=1
        rel[(u16(p,0x1c),n)]+=1
for k in c: print(k, c[k].most_common(12))
print('0x1c vs n', rel.most_common(15))
