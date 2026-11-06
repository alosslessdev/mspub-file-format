import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
for corpus in ['p95/x','p97/x','p97deluxe/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    cnt=collections.Counter(); rows=[]
    for f in files:
        doc=pubcore.parse_contents(f)
        for c in doc.chunks:
            if c.type_marker==0x1F:
                d=c.data
                A=d[2]; B=d[3]
                n16=struct.unpack_from('<H',d,4)[0]; n16b=struct.unpack_from('<H',d,6)[0]
                e16=struct.unpack_from('<H',d,8)[0]
                e32=struct.unpack_from('<I',d,8)[0] if len(d)>=12 else None
                cnt[(corpus,A,B,c.size,e16)]+=1
                rows.append((corpus,f,c,A,B,e16))
    print("="*30,corpus)
    for k,v in sorted(cnt.items(),key=lambda x:(x[0][1],x[0][2],x[0][3]))[:40]:
        print("  A=%02X B=%02X size=%d end16=%#x  n=%d"%(k[1],k[2],k[3],k[4],v))
    print("  total",len(rows))
