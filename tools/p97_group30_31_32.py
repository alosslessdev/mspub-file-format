import sys, glob, struct, collections, os
sys.path.insert(0,'tools'); import pubcore
u16=lambda b,o: struct.unpack_from('<H',b,o)[0]
files=[]
for corp in ('p97/x','p95/x','p97deluxe/x','p98/x'):
    files+=sorted(glob.glob(corp+'/**/*.PUB',recursive=True))
stats=collections.defaultdict(collections.Counter)
kidpat=collections.defaultdict(collections.Counter)
idmatch=collections.Counter()
ex=collections.defaultdict(list)
parents=collections.defaultdict(collections.Counter)
for f in files:
    try: d=pubcore.parse_contents(f)
    except Exception: continue
    byid={c.id:c for c in d.chunks}
    for t in (0x31,0x32):
        for c in d.of_type(t):
            stats[t]['n']+=1
            stats[t]['size%d'%len(c.data)]+=1
            for o in range(2,min(len(c.data),0x1a),2):
                stats[t]['u16@%02x=%04x'%(o,u16(c.data,o))]+=1
            ks=[k for k in d.chunks if k.parent==c.id]
            kidpat[t][(len(ks),tuple(sorted(sorted(set(k.type_marker for k in ks)))))]+=1
            pc=byid.get(c.parent)
            parents[t][pc.type_marker if pc else -1]+=1
            if len(ex[t])<4: ex[t].append((os.path.basename(f),c.data.hex()))
            if len(c.data)>=8:
                v=u16(c.data,6)
                idmatch[(t, bool(ks) and ks[0].id==v)]+=1
for t in (0x31,0x32):
    print('== ',hex(t),dict(stats[t]) if False else '')
    print(' n',stats[t]['n'],'sizes',{k:v for k,v in stats[t].items() if k.startswith('size')})
    print(' kidpat',dict(kidpat[t]))
    print(' parent types',dict(parents[t]))
    print(' +6 == first child id:',{k:v for k,v in idmatch.items() if k[0]==t})
    for e in ex[t]: print('  ex',e)
print()
print('0x31 u16 fields:')
for k,v in sorted(stats[0x31].items()):
    if k.startswith('u16@'): print(' ',k,v)
print('0x32 u16 fields:')
for k,v in sorted(stats[0x32].items()):
    if k.startswith('u16@'): print(' ',k,v)
