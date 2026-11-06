"""Throwaway: byte-column statistics for 53-byte 0x06 records."""
import sys, os, struct, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore

CORPORA = sys.argv[1:] or ["p97/x"]
files = []
for c in CORPORA:
    files += sorted(glob.glob(os.path.join(c, "**", "*.PUB"), recursive=True))
    files += sorted(glob.glob(os.path.join(c, "**", "*.pub"), recursive=True))
recs = []
for f in files:
    try:
        doc = pubcore.parse_contents(f)
    except Exception:
        continue
    for ch in doc.chunks:
        if ch.type_marker == 0x06 and len(ch.data) == 53:
            recs.append((f, ch, doc))
print("n=", len(recs))
for off in range(0, 53, 2):
    u16 = collections.Counter(struct.unpack_from("<H", c.data, off)[0] for _, c, _ in recs)
    di = collections.Counter(c.data[off] for _, c, _ in recs)
    db = collections.Counter(c.data[off+1] for _, c, _ in recs)
    u32 = collections.Counter(struct.unpack_from("<I", c.data, off)[0] for _, c, _ in recs) if off + 4 <= 53 else {}
    print("%02x: u16 distinct=%4d top=%s | lo top=%s | hi top=%s | u32 distinct=%s top=%s" % (
        off, len(u16), u16.most_common(4), di.most_common(3), db.most_common(3),
        len(u32) if u32 else '-', list(u32.most_common(2)) if u32 else '-'))
