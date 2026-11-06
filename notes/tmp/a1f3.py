import sys, struct
sys.path.insert(0,'tools')
import pubcore
for path,cid in [('p97/x/AWARD.PUB',0x0101),('p97/x/BRCATALG.PUB',0x014F),('p95/x/AWARD.PUB',0x0101)]:
    doc=pubcore.parse_contents(path)
    c=[x for x in doc.chunks if x.id==cid and x.type_marker==0x1F][0]
    d=c.data
    print("="*70,path,"size",len(d))
    for off in range(0,min(len(d),0x120),16):
        print("  %04x  %s"%(off,d[off:off+16].hex(' ')))
    # find WMF sigs
    sig=b'\x01\x00\x09\x00\x00\x03'
    pos=[]; i=0
    while True:
        i=d.find(sig,i)
        if i<0: break
        pos.append(i); i+=1
    print(" WMF sigs at:",[hex(x) for x in pos][:20], "count",len(pos))
