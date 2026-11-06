import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
rows=[]
for corpus in ['p97/x','p97deluxe/x']:
    for f in sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True)):
        doc=pubcore.parse_contents(f)
        for c in doc.chunks:
            if c.type_marker==0x3A and c.size!=26:
                rows.append((corpus,f,c))
for corpus,f,c in rows:
    d=c.data; n=struct.unpack_from('<I',d,4)[0]
    print("%-40s size=%4d n=%3d end=%#06x size-0x16=%#06x +0x12=%#06x +0x16=%#06x"%(os.path.basename(f),c.size,n,struct.unpack_from('<I',d,0x0C)[0],c.size-0x16,struct.unpack_from('<I',d,0x12)[0],struct.unpack_from('<I',d,0x16)[0]))
