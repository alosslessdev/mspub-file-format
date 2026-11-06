import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
tot=collections.Counter()
bad=[]
for corpus in ['p95/x','p97/x','p97deluxe/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    for f in files:
        doc=pubcore.parse_contents(f)
        for c in doc.chunks:
            if c.type_marker!=0x1F: continue
            d=c.data; L=len(d)
            u16ok = L>=0x0E and struct.unpack_from('<H',d,8)[0]==L-0x0E and struct.unpack_from('<H',d,4)[0]==struct.unpack_from('<H',d,6)[0]
            u32ok = L>=0x10 and struct.unpack_from('<I',d,0x0C)[0]==L-0x16 and struct.unpack_from('<I',d,4)[0]==struct.unpack_from('<I',d,8)[0]
            form = 'u16' if u16ok else ('u32' if u32ok else 'none')
            tot[(corpus,form)]+=1
            if form=='none': bad.append((corpus,f,c))
            elif L>26:
                if form=='u16':
                    n=struct.unpack_from('<H',d,4)[0]; base=0x0E; w=2
                    offs=struct.unpack_from('<%dH'%(n+1),d,base)
                else:
                    n=struct.unpack_from('<I',d,4)[0]; base=0x16; w=4
                    offs=struct.unpack_from('<%dI'%(n+1),d,base)
                first_ok = offs[0]==w*(n+1)
                last_ok = offs[-1]==(L-0x0E if form=='u16' else L-0x16)
                mono = all(offs[i]<=offs[i+1] for i in range(len(offs)-1))
                tot[(corpus,form,'first',first_ok)]+=1
                tot[(corpus,form,'last',last_ok)]+=1
                tot[(corpus,form,'mono',mono)]+=1
                if not first_ok or not last_ok or not mono:
                    bad.append((corpus,f,c,form,n,[hex(x) for x in offs[:6]],[hex(x) for x in offs[-3:]],first_ok,last_ok,mono))
for k,v in sorted(tot.items(),key=lambda x:str(x[0])): print(v,k)
print("--- nonconforming:",len(bad))
for b in bad[:30]:
    print(os.path.basename(b[1]),"size",b[2].size,b[3:] if len(b)>3 else '')
