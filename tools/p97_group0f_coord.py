import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u32=lambda b,o: struct.unpack_from('<I',b,o)[0]
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
SHAPES=(0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x0F)
res=collections.Counter(); impl=[]
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    doc=d.of_type(0x15)
    if not doc or len(doc[0].data)<0x1c: continue
    dm=doc[0].data; W=u32(dm,0x18); H=u32(dm,0x14)
    xs=[];ys=[];xe=[];ye=[]
    for c in d.chunks:
        if c.type_marker in SHAPES and len(c.data)>=0x16:
            b=[u32(c.data,o) for o in (6,10,14,18)]
            if b==[0,0,0,0]: continue
            if b[0]>b[2] or b[1]>b[3]: continue
            xs.append(b[0]);ys.append(b[1]);xe.append(b[2]);ye.append(b[3])
    if not xs: continue
    sx=max(xe)-min(xs); sy=max(ye)-min(ys)
    okx=sx<=W; oky=sy<=H
    res[(okx,oky)]+=1
    if not (okx and oky) and len(impl)<8:
        impl.append((os.path.basename(f),'page %.2fx%.2f'%(W/914400,H/914400),'span %.2fx%.2f'%(sx/914400,sy/914400),'origin %.2f,%.2f'%(min(xs)/914400,min(ys)/914400)))
print(res)
for i in impl: print(i)
