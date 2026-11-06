import sys, glob, os, struct
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
    d=c.data; n=struct.unpack_from('<I',d,4)[0]; end=struct.unpack_from('<I',d,0x0C)[0]
    v=[struct.unpack_from('<I',d,0x16+4*i)[0] for i in range(min(n+2,(c.size-0x16)//4))]
    mono_all=all(v[i]<v[i+1] for i in range(len(v)-1))
    print(os.path.basename(f),"n=%d"%n,"end=%#x"%end)
    print("   first20:",["%x"%x for x in v[:20]])
    print("   monotone:",mono_all,"v[0]=%#x 4n=%#x 4(n+1)=%#x"%(v[0],4*n,4*(n+1)), "v[n-1]=%#x v[n]=%#x end=%#x"%(v[n-1],v[n] if len(v)>n else -1,end))
