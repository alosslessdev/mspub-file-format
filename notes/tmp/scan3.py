import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
rows=[]
for corpus in ['p97/x','p97deluxe/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    for f in files:
        doc=pubcore.parse_contents(f)
        chunks={c.id:c for c in doc.chunks}
        for c in doc.chunks:
            if c.type_marker==0x3A and c.size!=26:
                rows.append((corpus,f,c,chunks))
for corpus,f,c,chunks in rows:
    print("="*70)
    print(corpus,f.split(os.sep)[-2]+"/"+os.path.basename(f),"id=%04X parent=%04X size=%d"%(c.id,c.parent,c.size))
    p=chunks.get(c.parent)
    print(" parent type %04X size %d"%(p.type_marker,p.size))
    d=c.data
    print(" ",d.hex())
    print("  header words:",[ "%04X"%x for x in struct.unpack_from("<8H",d,0)])
