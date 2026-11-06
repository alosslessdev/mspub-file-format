import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
files=sorted(glob.glob(os.path.join('p98/x','**','*.PUB'),recursive=True))
files+=[f for f in sorted(glob.glob(os.path.join('p98/x','**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
for f in files:
    doc=pubcore.parse_contents(f)
    chunks={c.id:c for c in doc.chunks}
    for c in doc.chunks:
        if c.type_marker==0x52:
            d=c.data; n=struct.unpack_from('<H',d,0x12)[0]; n2=struct.unpack_from('<H',d,0x14)[0]
            print("="*70,os.path.basename(f),"id=%04X parent=%04X size=%d n=%d dup=%d rule=%d"%(c.id,c.parent,c.size,n,n2,40+34*n))
            print("  head:",d[:0x28].hex(' '))
            keys=[struct.unpack_from('<I',d,0x24+4*i)[0] for i in range(n)]
            print("  keys:",[hex(k) for k in keys])
            sent=struct.unpack_from('<I',d,0x24+4*n)[0]
            print("  sentinel:",hex(sent))
            off=0x24+4*(n+1)
            for i in range(n):
                rec=d[off+30*i:off+30*(i+1)]
                print("   rec%d"%i, rec.hex(' '))
                print("        u32:",[hex(x) for x in struct.unpack_from('<7I',rec,0)],"u16@28:",hex(struct.unpack_from('<H',rec,28)[0]))
            print("  tail extra:",len(d)-(off+30*n))
