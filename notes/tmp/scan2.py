import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
allrows=[]
for corpus in ['p95/x','p97/x','p97deluxe/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    ndocs=0
    for f in files:
        doc=pubcore.parse_contents(f)
        chunks={c.id:c for c in doc.chunks}
        has=False
        for c in doc.chunks:
            if c.type_marker==0x3A:
                has=True
                p=chunks.get(c.parent)
                allrows.append((corpus,f,c,p))
        if has: ndocs+=1
    print(corpus,"docs with 0x3A:",ndocs,"of",len(files))
print("total 0x3A:",len(allrows))
# parent type census
print(collections.Counter((r[0], r[3].type_marker if r[3] else None) for r in allrows))
# size distribution
sizes=collections.Counter(r[2].size for r in allrows)
print("sizes:",sorted(sizes.items())[:40])
print("n distinct sizes",len(sizes),"min",min(sizes),"max",max(sizes))
