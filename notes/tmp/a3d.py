import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
rows=[]
for corpus in ['p97/x','p97deluxe/x']:
    for f in sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True)):
        doc=pubcore.parse_contents(f); chunks={c.id:c for c in doc.chunks}
        for c in doc.chunks:
            if c.type_marker==0x3A:
                rows.append((corpus,f,c,chunks))
# header invariants all 342
ok=collections.Counter()
for corpus,f,c,ch in rows:
    d=c.data
    n,d2=struct.unpack_from('<II',d,4)
    end=struct.unpack_from('<I',d,0x0C)[0]
    ok['cnt']+=1
    ok['cntdup']+= (n==d2)
    ok['end']+= (end==c.size-0x16)
    ok['u16_1']+= (struct.unpack_from('<H',d,0x10)[0]==1)
    ok['parent31']+= (ch[c.parent].type_marker==0x31)
print(ok)
print("--- populated")
for corpus,f,c,ch in rows:
    d=c.data
    if c.size==26: continue
    n=struct.unpack_from('<I',d,4)[0]
    end=struct.unpack_from('<I',d,0x0C)[0]
    w=[struct.unpack_from('<I',d,0x16+4*i)[0] for i in range(n+1)]
    arena=end-4*(n+1)
    print("%-22s size=%4d n=%3d end=%#06x arena=%4d mod14=%d last=end:%s firstwords=%s"%(
        os.path.basename(f),c.size,n,end,arena,arena%14,w[-1]==end,[hex(x) for x in w[:5]]))
    # tail records
    tail=d[0x16+4*(n+1):]
    pat=collections.Counter(tail[i:i+14].hex(' ') for i in range(0,len(tail),14))
    print("    records",len(tail)//14,"distinct:",len(pat), pat.most_common(2))
