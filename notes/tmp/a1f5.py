import sys, glob, os, struct
sys.path.insert(0,'tools')
import pubcore
shown=0
for f in sorted(glob.glob('p95/x/**/*.PUB',recursive=True)):
    doc=pubcore.parse_contents(f)
    for c in doc.chunks:
        if c.type_marker!=0x1F: continue
        d=c.data; L=len(d)
        if L<=26: continue
        n=struct.unpack_from('<H',d,4)[0]; end=struct.unpack_from('<H',d,8)[0]
        if 0x0E+2*(n+1)>L: continue
        offs=list(struct.unpack_from('<%dH'%(n+1),d,0x0E))
        mono=all(offs[i]<=offs[i+1] for i in range(n))
        ok=mono and offs[0]==2*(n+1) and offs[-1]==end
        if ok and n>=2 and shown<5:
            shown+=1
            print("="*60,os.path.basename(f),"size",L,"count",n,"end",hex(end))
            print("offsets:",[hex(x) for x in offs])
            for off in range(0,min(L,0x60),16):
                print("   %04x  %s"%(off,d[off:off+16].hex(' ')))
