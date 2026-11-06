import sys, glob, os, struct
sys.path.insert(0,'tools')
import pubcore
files=sorted(glob.glob(os.path.join('p98/x','**','*.JSP'),recursive=True))
print(files)
for f in files:
    doc=pubcore.parse_contents(f)
    print("="*70,os.path.basename(f),len(doc.chunks),"chunks")
    for c in doc.chunks:
        if c.type_marker in (0x4E,0x4F,0x50,0x36):
            print("-"*60)
            print("%04X id=%04X parent=%04X size=%d"%(c.type_marker,c.id,c.parent,c.size))
            d=c.data
            for off in range(0,len(d),16):
                print("  %04x  %s"%(off,d[off:off+16].hex(' ')))
