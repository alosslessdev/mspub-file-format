import sys, glob, os, struct, collections
sys.path.insert(0,'tools')
import pubcore
for corpus in ['p95/x','p97/x','p98/x']:
    files=sorted(glob.glob(os.path.join(corpus,'**','*.PUB'),recursive=True))[:60]
    files+=[f for f in sorted(glob.glob(os.path.join(corpus,'**','*.JSP'),recursive=True)) if open(f,'rb').read(8)==b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1']
    shown=0
    for f in files:
        doc=pubcore.parse_contents(f)
        for c in doc.chunks:
            if c.type_marker==0x1F and c.size>26 and shown<3:
                d=c.data; shown+=1
                print("="*60,corpus,os.path.basename(f),"id=%04X size=%d"%(c.id,c.size))
                print(" ".join("%02x"%b for b in d[:48]))
                print("words:",[("%04x"%w) for w in struct.unpack_from('<%dH'%(min(24,len(d))//2),d,0)])
