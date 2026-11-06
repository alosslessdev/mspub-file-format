import sys, struct
sys.path.insert(0,'tools')
import pubcore
doc=pubcore.parse_contents('p98/x/CHEKLIST.JSP')
for c in doc.chunks:
    if c.type_marker in (0x4E,):
        d=c.data
        print("="*70,"0x4E id=%04X size=%d"%(c.id,len(d)))
        # print as u16 words with index annotation, only rows
        for off in range(0,len(d),2):
            w=struct.unpack_from('<H',d,off)[0]
            print("%04x:%04x"%(off,w), end='  ' if (off//2)%8!=7 else '\n')
        print()
