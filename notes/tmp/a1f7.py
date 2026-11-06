import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
def printable(b):
    return all(32<=x<127 or x==0 for x in b)
res=collections.Counter(); examples=[]
for corpus in ['p95/x','p97/x','p97deluxe/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    for f in files:
        doc=pubcore.parse_contents(f)
        for c in doc.chunks:
            if c.type_marker!=0x1F: continue
            d=c.data; L=len(d)
            if L<=26: continue
            if struct.unpack_from('<H',d,8)[0]==L-0x0E:
                w,base,cs=2,0x0E,'u16'; n=struct.unpack_from('<H',d,4)[0]
            else:
                w,base,cs=4,0x16,'u32'; n=struct.unpack_from('<I',d,4)[0]
            slots=list(struct.unpack_from('<%d%s'%(n+1,'H' if w==2 else 'I'),d,base))
            end=L-0x0E if w==2 else L-0x16
            for s in slots:
                if s>=end: continue
                p=base+s
                if p+2>L: continue
                u16v=struct.unpack_from('<H',d,p)[0]
                u32v=struct.unpack_from('<I',d,p)[0] if p+4<=L else None
                name16=d[p+2:p+42]
                name32=d[p+4:p+44] if p+44<=L else b''
                ok16 = u16v==1 and printable(name16) and name16[0]>=32
                ok32 = u32v==1 and printable(name32) and name32 and name32[0]>=32
                res[(cs,'slot<end', 'ok16' if ok16 else ('ok32' if ok32 else 'neither'))]+=1
                if not ok16 and len(examples)<6:
                    examples.append((os.path.basename(f),L,cs,hex(s),hex(p),hex(u16v),d[p:p+16].hex(' ')))
for k,v in res.items(): print(v,k)
print(examples)
