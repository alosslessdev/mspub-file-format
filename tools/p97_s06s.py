"""Byte-field correlation matrix: find mirrored/duplicated fields."""
import sys, os, struct, glob, collections, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

files = sorted(set(glob.glob('p97/x/*.PUB')))
recs = []
for f in files:
    try: d = pubcore.parse_contents(f)
    except Exception: continue
    for c in d.chunks:
        if c.type_marker == 0x06 and len(c.data) == 53: recs.append((f, c))
print("recs", len(recs))

offs = [0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f,0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x29,0x2a,0x2b,0x2c,0x2d,0x2e,0x2f,0x30,0x31,0x32,0x33,0x34]
print("\nequal-column pairs (a==b in >=90% of records where either is nonzero):")
for a, b in itertools.combinations(offs, 2):
    both = [r for r in recs if r[1].data[a] or r[1].data[b]]
    if not both: continue
    eq = sum(1 for r in both if r[1].data[a] == r[1].data[b])
    if eq / len(both) >= 0.90:
        print("   %#04x == %#04x : %d/%d (%.0f%%)" % (a, b, eq, len(both), 100.*eq/len(both)))

print("\ntests:")
# b[0x23] vs fill colour low byte
sel = [(r[1].data[0x23], r[1].data[0x18]) for r in recs if r[1].data[0x23]]
print("  b[0x23] == b[0x18] when b[0x23]!=0: %d/%d" % (sum(1 for x,y in sel if x==y), len(sel)))
sel = [(r[1].data[0x23], r[1].data[0x18]) for r in recs if r[1].data[0x18] < 0x25]
print("  b[0x23] == b[0x18] when colour is a small index: %d/%d" % (sum(1 for x,y in sel if x==y), len(sel)))
# b[0x2b] vs b[0x20]
sel = [(r[1].data[0x2b], r[1].data[0x20]) for r in recs if r[1].data[0x2b]]
print("  b[0x2b] == b[0x20] when b[0x2b]!=0: %d/%d" % (sum(1 for x,y in sel if x==y), len(sel)))
# b[0x29] vs b[0x20]
sel = [(r[1].data[0x29], r[1].data[0x20]) for r in recs if r[1].data[0x29]]
print("  b[0x29] == b[0x20] when b[0x29]!=0: %d/%d" % (sum(1 for x,y in sel if x==y), len(sel)))
# joint of (b[0x20], b[0x29])
j = collections.Counter((r[1].data[0x20], r[1].data[0x29]) for r in recs)
print("  joint (b20,b29):", j.most_common(12))
j = collections.Counter((r[1].data[0x20], r[1].data[0x2b]) for r in recs)
print("  joint (b20,b2b):", j.most_common(12))
