"""Full LOGO/0x32 structural analysis over the four corpora."""
import sys, os, struct, collections, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pubcore
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPORA = [("p95", "p95/x"), ("p97", "p97/ext2"), ("p97deluxe", "p97deluxe/x"), ("p98", "p98/x")]

def pubs(top):
    out = []
    for dp, _d, fs in os.walk(os.path.join(ROOT, top)):
        for f in fs:
            if f.lower().endswith(".pub"):
                out.append(os.path.join(dp, f))
    return sorted(out)

def parse31(c):
    b = c.data
    if len(b) < 30:
        return None
    h = struct.unpack_from("<5H", b, 4)
    A, B, C, D, E = h
    if 26 + 4 * C + 4 > len(b):
        return None
    ids = list(struct.unpack_from("<%dI" % C, b, 26))
    sent = struct.unpack_from("<I", b, 26 + 4 * C)[0]
    tail = [struct.unpack_from("<HH", b, 30 + 4 * C + 4 * i) for i in range(C)]
    return dict(A=A, B=B, C=C, D=D, E=E, ids=ids, sent=sent, tail=tail,
                sizeok=(len(b) == 30 + 8 * C))

def parse32(c):
    b = c.data
    if len(b) < 16:
        return None
    mk, tag, N, N2, endoff, f1, f2 = struct.unpack_from("<7H", b, 0)
    base = 14
    olen = N + 1
    if base + 2 * olen > len(b):
        return None
    offs = list(struct.unpack_from("<%dH" % olen, b, base))
    strs = []
    ok = True
    for o in offs[:-1]:
        p = base + o
        e = b.find(b"\x00", p)
        if e < 0:
            ok = False; break
        strs.append(b[p:e].decode("latin-1"))
    return dict(N=N, N2=N2, endoff=endoff, f1=f1, f2=f2, offs=offs, strs=strs,
                asc=all(offs[i] <= offs[i + 1] for i in range(len(offs) - 1)),
                endok=(base + offs[-1] == len(b)), ok=ok)

def main():
    rows = []
    for name, top in CORPORA:
        for path in pubs(top):
            try:
                d = pubcore.parse_contents(path)
            except Exception as e:
                print("SKIP", path, e); continue
            kids = collections.defaultdict(list)
            for c in d.chunks:
                kids[c.parent].append(c)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            for c in d.chunks:
                if c.type_marker != 0x31:
                    continue
                p = parse31(c)
                ch = [k for k in kids.get(c.id, []) if k.type_marker == 0x32]
                p32 = parse32(ch[0]) if ch else None
                rows.append(dict(corpus=name, file=rel, id=c.id, size=c.size,
                                 nchildren=len(ch), child_id=ch[0].id if ch else None,
                                 child_size=ch[0].size if ch else None,
                                 p31=p, p32=p32))
    json.dump(rows, open(os.path.join(ROOT, "out/logo_full.json"), "w"),
              default=lambda o: list(o) if isinstance(o, tuple) else o)

    def rep(label, cond):
        print("%-46s %d / %d" % (label, sum(1 for r in rows if cond(r)), len(rows)))

    print("total 0x31 chunks:", len(rows))
    print("\n-- structural conformance")
    rep("size == 30 + 8*C", lambda r: r["p31"] and r["p31"]["sizeok"])
    rep("sentinel u32@26+4C == 0x7FFFFFFF", lambda r: r["p31"] and r["p31"]["sent"] == 0x7FFFFFFF)
    rep("C == D (+0x08 == +0x0A)", lambda r: r["p31"] and r["p31"]["C"] == r["p31"]["D"])
    rep("ids strictly ascending", lambda r: r["p31"] and all(
        r["p31"]["ids"][i] < r["p31"]["ids"][i + 1] for i in range(len(r["p31"]["ids"]) - 1)))
    rep("exactly one 0x32 child", lambda r: r["nchildren"] == 1)
    rep("zero 0x32 child", lambda r: r["nchildren"] == 0)
    rep("B(+0x06) == 0x32 child id", lambda r: r["p31"] and r["nchildren"] == 1 and r["p31"]["B"] == r["child_id"])
    print("\n-- field domains")
    print("A(+0x04):", collections.Counter(r["p31"]["A"] for r in rows if r["p31"]))
    print("E(+0x0C):", collections.Counter(r["p31"]["E"] for r in rows if r["p31"]))
    print("C(+0x08):", collections.Counter(r["p31"]["C"] for r in rows if r["p31"]))
    print("u16@+0x10/0x12/0x16/0x18 nonzero:",
          collections.Counter((r["p31"] is not None) for r in rows))
    print("\n-- 0x32")
    p32 = [r for r in rows if r["p32"]]
    print("with 0x32:", len(p32))
    print("N(+0x04)==N2(+0x06):", sum(1 for r in p32 if r["p32"]["N"] == r["p32"]["N2"]))
    print("offsets ascending:", sum(1 for r in p32 if r["p32"]["asc"]))
    print("end offset lands on chunk end:", sum(1 for r in p32 if r["p32"]["endok"]))
    print("all strings NUL-terminated:", sum(1 for r in p32 if r["p32"]["ok"]))
    print("f1(+0x0A):", collections.Counter(r["p32"]["f1"] for r in p32))
    print("f2(+0x0C):", collections.Counter(r["p32"]["f2"] for r in p32))
    print("N == C(0x31):", sum(1 for r in p32 if r["p31"] and r["p32"]["N"] == r["p31"]["C"]))
    print("\n-- tail semantics")
    perm = [r for r in rows if r["p31"] and r["p31"]["C"] > 0]
    print("C>0 samples:", len(perm))
    print("tail hi is permutation 0..C-1:", sum(1 for r in perm
          if sorted(t[1] for t in r["p31"]["tail"]) == list(range(r["p31"]["C"]))))
    print("tail hi ascending:", sum(1 for r in perm
          if all(r["p31"]["tail"][i][1] < r["p31"]["tail"][i + 1][1] for i in range(len(r["p31"]["tail"]) - 1))))
    names = collections.Counter()
    for r in p32:
        for s in r["p32"]["strs"]:
            names[s] += 1
    print("\n-- top 40 strings")
    for s, n in names.most_common(40):
        print("   %5d  %r" % (n, s))

main()
