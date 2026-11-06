"""Cross-tabs: candidate fill type vs candidate colour; palette inspection."""
import sys, os, struct, collections, glob
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

print("== palette-ish chunks present")
cnt = collections.Counter()
sizes = collections.defaultdict(collections.Counter)
for d in docs:
    for ch in d.chunks:
        if ch.type_marker in (0x47, 0x5C, 0x44):
            cnt[ch.type_marker] += 1
            sizes[ch.type_marker][len(ch.data)] += 1
print(dict(cnt))
for t, s in sizes.items():
    print("  type %#05x sizes: %s" % (t, s.most_common(6)))

# dump one palette
for d in docs:
    pal = [c for c in d.chunks if c.type_marker in (0x47, 0x5C)]
    if pal and len(pal[0].data) > 40:
        print("\n== palette dump %s type=%#05x len=%d" % (os.path.basename(d.path), pal[0].type_marker, len(pal[0].data)))
        b = pal[0].data
        for o in range(0, min(len(b), 96), 16):
            print("  %02x %s" % (o, " ".join("%02x" % v for v in b[o:o+16])))
        break

recs = [(d, ch) for d in docs for ch in d.chunks if ch.type_marker == 0x06 and len(ch.data) == 53]
print("\n== crosstab u8@0x20 (rows) x u32@0x18 (cols, top 12)")
tab = collections.defaultdict(collections.Counter)
for d, ch in recs:
    b = ch.data
    tab[b[0x20]][struct.unpack_from("<I", b, 0x18)[0]] += 1
for ft in sorted(tab):
    print("  ft=%#04x n=%3d: %s" % (ft, sum(tab[ft].values()),
          ", ".join("%d:%d" % (v, k) for v, k in tab[ft].most_common(12))))

print("\n== crosstab u8@0x20 (rows) x u32@0x22 (cols, top 12)")
tab2 = collections.defaultdict(collections.Counter)
for d, ch in recs:
    b = ch.data
    tab2[b[0x20]][struct.unpack_from("<I", b, 0x22)[0]] += 1
for ft in sorted(tab2):
    print("  ft=%#04x n=%3d: %s" % (ft, sum(tab2[ft].values()),
          ", ".join("%d:%d" % (v, k) for v, k in tab2[ft].most_common(12))))

print("\n== crosstab u8@0x2b (rows) x u32@0x18")
tab3 = collections.defaultdict(collections.Counter)
for d, ch in recs:
    b = ch.data
    tab3[b[0x2b]][struct.unpack_from("<I", b, 0x18)[0]] += 1
for ft in sorted(tab3):
    print("  b2b=%#04x n=%3d: %s" % (ft, sum(tab3[ft].values()),
          ", ".join("%d:%d" % (v, k) for v, k in tab3[ft].most_common(10))))

print("\n== all u32@0x18 values")
c = collections.Counter(struct.unpack_from("<I", ch.data, 0x18)[0] for _, ch in recs)
print(sorted(c.items()))
print("\n== all u32@0x1c values")
c = collections.Counter(struct.unpack_from("<I", ch.data, 0x1c)[0] for _, ch in recs)
print(sorted(c.items()))
print("\n== all u16@0x04 values (rotation cand)")
c = collections.Counter(struct.unpack_from("<H", ch.data, 4)[0] for _, ch in recs)
print(sorted(c.items()))
