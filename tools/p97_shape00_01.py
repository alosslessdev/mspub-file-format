import sys, glob, collections, struct, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def collect(corpora, tm):
    out = []
    for corp in corpora:
        for f in sorted(glob.glob(os.path.join(corp, '**', '*.PUB'), recursive=True)):
            try: doc = pubcore.parse_contents(f)
            except Exception: continue
            for c in doc.chunks:
                if c.type_marker == tm:
                    out.append((f, doc, c))
    return out

def peroffs(items, base, tm):
    print('== tm=%#x n=%d' % (tm, len(items)))
    extra = collections.Counter(len(c.data) - base for _, _, c in items)
    print('   extras:', sorted(extra.items()))
    for i in range(base):
        cnt = collections.Counter(c.data[i] for _, _, c in items if len(c.data) > i)
        top = sorted(cnt.items(), key=lambda x: -x[1])[:5]
        print('   %02x n=%3d %s' % (i, len(cnt), ' '.join('%02x:%d' % (v, k) for v, k in top)))

if __name__ == '__main__':
    corp = sys.argv[1].split(',')
    tm = int(sys.argv[2], 16)
    base = int(sys.argv[3])
    peroffs(collect(corp, tm), base, tm)
