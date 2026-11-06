"""Differential analysis: which tail bytes co-vary, from minimal-diff pairs."""
import sys, os, struct, collections, glob, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

def files(c):
    out = []
    for pat in ("*.PUB", "*.pub"):
        out += glob.glob(os.path.join(c, "**", pat), recursive=True)
    return sorted(set(out))

docs = []
for f in files("p97/x"):
    try: docs.append(pubcore.parse_contents(f))
    except Exception: pass

solo = collections.Counter()      # offset differs alone
joint = collections.Counter()     # frozenset of differing offsets
paircount = 0
for d in docs:
    rs = [c for c in d.chunks if c.type_marker == 0x06 and len(c.data) == 53]
    for a, b in itertools.combinations(rs, 2):
        diffs = [i for i in range(0x16, 53) if a.data[i] != b.data[i]]
        if 1 <= len(diffs) <= 3:
            paircount += 1
            if len(diffs) == 1:
                solo[diffs[0]] += 1
            joint[tuple(diffs)] += 1
print("pairs with 1..3 tail diffs: %d" % paircount)
print("\nbytes that vary ALONE (independent single-byte fields):")
for off, k in sorted(solo.items()):
    print("   +%#04x  %d" % (off, k))
print("\ntop joint diff sets:")
for s, k in joint.most_common(25):
    print("   %-28s %d" % (", ".join("%#04x" % x for x in s), k))
