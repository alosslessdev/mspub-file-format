import sys, glob, os, struct
sys.path.insert(0,'tools')
import pubcore
targets=[('p97/x','CLASSIC.PUB',0x014C),('p97/x','PLAIN.PUB',0x0126),('p97deluxe/x','PageWiz/modrn_cd.pub',0x013F)]
for corpus,name,cid in targets:
    path=os.path.join(corpus,name)
    doc=pubcore.parse_contents(path)
    c=[x for x in doc.chunks if x.id==cid][0]
    d=c.data
    print("="*60); print(name,"size",len(d))
    i=d.find(b'\x00\x00\x0e\x00\x00\x00\x01\x00\x00\x00')
    print("first 14-byte pattern at",hex(i))
    # print from 0x16 to i as u32
    vals=[struct.unpack_from('<I',d,o)[0] for o in range(0x16,i,4)]
    print("u32 words 0x16..:",len(vals),"words; i-0x16 =",i-0x16,"=",4*len(vals))
    print(["%x"%v for v in vals])
    print("tail from",hex(i),":")
    tail=d[i:]
    # try 14-byte records
    for k in range(0,min(len(tail),14*6),14):
        print("   ",tail[k:k+14].hex(' '))
