import sys, glob, os, struct
sys.path.insert(0,'tools')
import pubcore
f='p98/x/CHEKLIST.JSP'
doc=pubcore.parse_contents(f)
for c in doc.chunks:
    if c.type_marker==0x4F:
        d=c.data; n=struct.unpack_from('<H',d,0x0A)[0]
        print("0x4F id=%04X size=%d n=%d rule=%d"%(c.id,c.size,n,0x14+11*n))
        for i in range(n):
            e=d[0x14+11*i:0x14+11*(i+1)]
            kind,a,b,pad,val=struct.unpack_from('<HHHBI',e,0)
            print("  e%-2d kind=%d a=%#06x b=%#06x pad=%d val=%#010x"%(i,kind,a,b,pad,val))
    if c.type_marker==0x4E:
        d=c.data; n=struct.unpack_from('<H',d,0x0A)[0]
        print("0x4E id=%04X size=%d n=%d"%(c.id,c.size,n))
        for i in range(n):
            print("  e%d:"%i, d[0x0E+46*i:0x0E+46*(i+1)].hex(' '))
    if c.type_marker==0x50:
        d=c.data; n=struct.unpack_from('<H',d,0x0A)[0]
        print("0x50 id=%04X size=%d n=%d rule=%d"%(c.id,c.size,n,0x14+5*n))
        for i in range(n):
            e=d[0x14+5*i:0x19+5*i]
            a,b,fl=struct.unpack('<HHB',e)
            print("  e%-2d a=%#06x b=%#06x f=%d"%(i,a,b,fl))
