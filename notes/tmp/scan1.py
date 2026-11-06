import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
markers={0x3A,0x3B,0x3F}
for corpus in ['p95/x','p97/x','p97deluxe/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    cnt=collections.Counter()
    for f in files:
        try: doc=pubcore.parse_contents(f)
        except Exception as e: print("ERR",f,e); continue
        for c in doc.chunks:
            if c.type_marker in markers:
                cnt[(c.type_marker, c.size if c.type_marker!=0x3A else 'var', c.parent)]+=1
    print(corpus, len(files))
    for k,v in sorted(cnt.items(), key=lambda x:(x[0][0],str(x[0][1]))):
        print("   %04X size=%s parent=%04X n=%d"%(k[0],k[1],k[2],v))
