import sys,glob,collections,struct
sys.path.insert(0,'tools'); import pubcore
KNOWN={0x78:0,0x05:0,0x08:'V',0x0a:0,0x10:2,0x12:2,0x18:2,0x1a:2,0x07:2,
    0x20:4,0x22:4,0x58:4,0x68:4,0x70:4,0xb8:4,0x28:8,0x38:16,0x48:24,
    0xc0:'V',0x80:'V',0x82:'V',0x88:'V',0x8a:'V',0x90:'V',0x98:'V',0xa0:'V'}
CANDS=[0,1,2,3,4,6,8,10,12,14,16,18,20,22,24,26,28,30,32,'V']
files=sorted(glob.glob('p95/x/**/*.PUB',recursive=True))
per=collections.defaultdict(list)
for f in files:
    try: doc=pubcore.parse_contents(f)
    except Exception: continue
    for c in doc.chunks: per[c.type_marker].append(bytes(c.data))
sys.setrecursionlimit(100000)
def adv(data,pos,w):
    if w=='V':
        if pos+6>len(data): return -1
        ln=struct.unpack_from('<I',data,pos+2)[0]
        if ln<4 or pos+2+ln>len(data): return -1
        return pos+2+ln
    if pos+2+w>len(data): return -1
    return pos+2+w
def solve(data,assign,pos,sols,limit):
    if len(sols)>limit: return
    if pos==len(data): sols.append(dict(assign)); return
    if pos+2>len(data): return
    t=data[pos+1]
    if t in assign:
        np=adv(data,pos,assign[t])
        if np>=0: solve(data,assign,np,sols,limit)
        return
    c=[KNOWN[t]] if t in KNOWN else CANDS
    for w in c:
        na=dict(assign); na[t]=w
        np=adv(data,pos,w)
        if np>=0: solve(data,na,np,sols,limit)
A={}
order=sorted(per,key=lambda k:-len(per[k]))
for it in range(8):
    ch=False
    for tm in order:
        for d in per[tm][:80]:
            sols=[]; solve(d,dict(A),0,sols,60)
            if not sols: continue
            keys=set()
            for s in sols: keys|=set(s)
            for k in keys:
                if k in A: continue
                vals={s.get(k) for s in sols}
                if len(vals)==1 and None not in vals:
                    A[k]=vals.pop(); ch=True
    print("iter",it,{hex(k):v for k,v in sorted(A.items())},flush=True)
    if not ch: break
import json
json.dump({str(k):v for k,v in A.items()},open('/tmp/widths.json','w'))
