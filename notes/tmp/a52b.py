import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
files=sorted(glob.glob(os.path.join('p98/x','**','*.PUB'),recursive=True))
files+=[f for f in sorted(glob.glob(os.path.join('p98/x','**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
tot=collections.Counter()
for f in files:
    doc=pubcore.parse_contents(f)
    by={}
    for c in doc.chunks: by.setdefault(c.type_marker,[]).append(c)
    for c in by.get(0x52,[]):
        d=c.data; n=struct.unpack_from('<H',d,0x12)[0]
        hdr=struct.unpack_from('<2H',d,0x16)  # 0x1E, then field
        tot['docs']+=1; tot['recs']+=n
        tot['rule']+= (c.size==40+34*n)
        tot['dup']+= (struct.unpack_from('<H',d,0x14)[0]==n)
        tot['elem']+= (hdr[0]==0x1E)
        tot['pre0']+= (d[4:0x12]==b'\x00'*14 and struct.unpack_from('<H',d,0x10)[0]==0)
        keys=list(struct.unpack_from('<%dI'%n,d,0x24)) if n else []
        tot['sorted']+= (keys==sorted(keys) and len(set(keys))==len(keys))
        tot['sent']+= (struct.unpack_from('<I',d,0x24+4*n)[0]==0x7fffffff if c.size>=0x28+4*n else False)
        off=0x24+4*(n+1)
        ids=[]; f12=set(); f16=set(); f1a=set(); fl=set(); t0=set(); p1=[]; p2=[]
        for i in range(n):
            r=d[off+30*i:off+30*(i+1)]
            t0.add(struct.unpack_from('<I',r,0)[0])
            ids.append(struct.unpack_from('<I',r,4)[0])
            p1.append(struct.unpack_from('<I',r,8)[0]); p2.append(struct.unpack_from('<I',r,0xC)[0])
            fl.add(struct.unpack_from('<H',r,0x10)[0])
            f12.add(struct.unpack_from('<I',r,0x12)[0]); f16.add(struct.unpack_from('<I',r,0x16)[0])
            f1a.add(struct.unpack_from('<f',r,0x1A)[0])
        tot['t0']+=tuple(sorted(t0))==(1,) or tuple(sorted(t0))==(2,)
        tot['f12']+= f12=={0xCB18967C}
        tot['f16']+= f16=={0xCB18967C}
        keyset=set(keys); idset=set(c2.id for c2 in doc.chunks)
        overlap=len(keyset&idset)
        print("%-18s n=%3d size=%4d rule=%s t0=%s flags=%s f1a=%s idrange=%s key_id_overlap=%d ptr1=%08x..%08x" % (
            os.path.basename(f), n, c.size, c.size==40+34*n, sorted(t0), sorted(fl), sorted(f1a),
            (min(ids),max(ids)) if ids else None, overlap, (min(p1),max(p1)) if p1 else None))
        if n:
            print("     keys:",[hex(k) for k in keys][:20],"ids:",ids[:20])
print(dict(tot))
