import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
def try_form(d):
    res=[]
    L=len(d)
    for name,w,cntoff,endoff,base in [('p95',2,4,8,0x0E),('p97',4,4,0x0C,0x16)]:
        if L<base: continue
        if w==2:
            n=struct.unpack_from('<H',d,cntoff)[0] if L>=cntoff+2 else None
            end=struct.unpack_from('<H',d,endoff)[0] if L>=endoff+2 else None
        else:
            n=struct.unpack_from('<I',d,cntoff)[0] if L>=cntoff+4 else None
            end=struct.unpack_from('<I',d,endoff)[0] if L>=endoff+4 else None
        if n is None: continue
        need=base+w*(n+1)
        if need>L: res.append((name,'short',n,end)); continue
        if w==2: offs=list(struct.unpack_from('<%dH'%(n+1),d,base))
        else: offs=list(struct.unpack_from('<%dI'%(n+1),d,base))
        mono=all(offs[i]<=offs[i+1] for i in range(len(offs)-1))
        ok_first=offs[0]==w*(n+1)
        ok_end=offs[-1]==end
        res.append((name,mono,ok_first,ok_end,n,end,offs[:6]))
    return res
stats=collections.Counter()
ex={}
for corpus in ['p95/x','p97/x','p97deluxe/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    for f in files:
        doc=pubcore.parse_contents(f)
        for c in doc.chunks:
            if c.type_marker==0x1F:
                d=c.data
                if len(d)<=26: 
                    stats[(corpus,'empty',len(d))]+=1
                    continue
                r=try_form(d)
                key=(corpus,)+tuple((x[0],)+tuple(x[1:4]) for x in r)
                stats[key]+=1
                ex.setdefault(key,(os.path.basename(f),len(d),r))
for k,v in stats.items():
    print(v,"|",k if not isinstance(k,tuple) or len(str(k))<120 else str(k)[:200])
