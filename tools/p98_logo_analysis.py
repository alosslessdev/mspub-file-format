"""Consolidated LOGO (0x31) / companion (0x32) analysis. Prints every number used in
notes/p98/slices/logo.md. Run from repo root:  python tools/p98_logo_analysis.py
"""
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
    A, B, C, D, E = struct.unpack_from("<5H", b, 4)
    F, z1, z2, G, z3, z4 = struct.unpack_from("<6H", b, 0x0E)
    ids = list(struct.unpack_from("<%dI" % C, b, 26))
    sent = struct.unpack_from("<I", b, 26 + 4 * C)[0]
    tail = [struct.unpack_from("<HH", b, 30 + 4 * C + 4 * i) for i in range(C)]
    return dict(A=A, B=B, C=C, D=D, E=E, F=F, G=G, z=(z1, z2, z3, z4), ids=ids,
                sent=sent, tail=tail, exact=(len(b) == 30 + 8 * C))

def parse32(b):
    for H in (12, 14, 16, 18):
        for cntpos in (4, 8):
            if cntpos + 4 > H:
                continue
            N = struct.unpack_from("<H", b, cntpos)[0]
            N2 = struct.unpack_from("<H", b, cntpos + 2)[0]
            if N != N2 or N > 400:
                continue
            for olen in (N + 1, N):
                if H + 2 * olen > len(b):
                    continue
                offs = list(struct.unpack_from("<%dH" % olen, b, H))
                if any(offs[i] > offs[i + 1] for i in range(len(offs) - 1)):
                    continue
                out = []
                ok = True
                for o in offs[:-1]:
                    p = H + 2 * olen + o
                    if p >= len(b):
                        ok = False; break
                    e = b.find(b"\x00", p)
                    if e < 0:
                        ok = False; break
                    s = b[p:e]
                    if any(c < 32 or c > 126 for c in s):
                        ok = False; break
                    out.append(s.decode("latin-1"))
                if ok:
                    return dict(H=H, N=N, olen=olen, offs=offs, strs=out,
                                endok=(H + 2 * olen + offs[-1] == len(b)))
    return None

def main():
    docs = {}
    rows = []
    for name, top in CORPORA:
        for path in pubs(top):
            try:
                d = pubcore.parse_contents(path)
            except Exception as e:
                print("SKIP", path, e); continue
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            docs[rel] = d
            kids = collections.defaultdict(list)
            for c in d.chunks:
                kids[c.parent].append(c)
            for c in d.chunks:
                if c.type_marker != 0x31:
                    continue
                p = parse31(c)
                ch = [k for k in kids.get(c.id, []) if k.type_marker == 0x32]
                p32 = parse32(ch[0].data) if ch else None
                rows.append(dict(corpus=name, file=rel, id=c.id, parent=c.parent, size=c.size,
                                 idx=c.index, n32=len(ch), child=ch[0].id if ch else None,
                                 p31=p, p32=p32))
    json.dump({"n": len(rows)}, open(os.path.join(ROOT, "out/logo_rows.json"), "w"))
    print("0x31 chunks: %d in %d files" % (len(rows), len(docs)))
    print("by corpus:", collections.Counter(r["corpus"] for r in rows))

    P = lambda r: r["p31"]
    def rep(label, cond, n=None):
        base = rows if n is None else n
        print("  %-52s %4d / %d" % (label, sum(1 for r in base if cond(r)), len(base)))

    print("\n[A] 0x31 structural invariants")
    rep("size == 30 + 8*C", lambda r: P(r)["exact"])
    rep("u16@0x08 == u16@0x0A  (count duplicated)", lambda r: P(r)["C"] == P(r)["D"])
    rep("u32@(26+4C) == 0x7FFFFFFF", lambda r: P(r)["sent"] == 0x7FFFFFFF)
    rep("u16@0x0C == 4", lambda r: P(r)["E"] == 4)
    rep("id array strictly ascending", lambda r: all(P(r)["ids"][i] < P(r)["ids"][i+1] for i in range(len(P(r)["ids"])-1)))
    rep("u16@0x10,0x12,0x16,0x18 all zero", lambda r: P(r)["z"] == (0,0,0,0))
    rep("parent == DOCUMENT chunk", lambda r: r["parent"] == next(c.id for c in docs[r["file"]].chunks if c.type_marker == 0x15))
    print("  A(+0x04):", dict(collections.Counter(P(r)["A"] for r in rows)))
    print("  C(+0x08): zero=%d nonzero=%d; distinct=%s" % (
        sum(1 for r in rows if P(r)["C"] == 0), sum(1 for r in rows if P(r)["C"]),
        sorted(set(P(r)["C"] for r in rows if P(r)["C"]))))
    print("  F(+0x0E) nonzero:", sum(1 for r in rows if P(r)["F"]), " G(+0x14) nonzero:", sum(1 for r in rows if P(r)["G"]))

    print("\n[B] 0x31 -> 0x32 pairing")
    rep("exactly one 0x32 child", lambda r: r["n32"] == 1)
    rep("no 0x32 child", lambda r: r["n32"] == 0)
    rep("B(+0x06) == 0x32 child id", lambda r: r["n32"] == 1 and P(r)["B"] == r["child"])
    per = collections.Counter()
    for r in rows:
        per[(r["file"], r["n32"])] += 1
    files = collections.defaultdict(list)
    for r in rows:
        files[r["file"]].append(r)
    comp = collections.Counter((len(v), sum(1 for x in v if x["n32"]), sum(1 for x in v if P(x)["A"] == 1),
                                sum(1 for x in v if P(x)["C"])) for v in files.values())
    print("  per-file (n_logos, n_with_32, n_A=1, n_C>0):")
    for k, v in sorted(comp.items()):
        print("     ", k, v)

    print("\n[C] 0x32 record")
    p32 = [r for r in rows if r["p32"]]
    print("  parsed %d of %d 0x32 chunks" % (len(p32), sum(1 for r in rows if r["n32"])))
    print("  header length H:", dict(collections.Counter(r["p32"]["H"] for r in p32)))
    print("  offsets ascending: %d/%d" % (sum(1 for r in p32 if all(r["p32"]["offs"][i] <= r["p32"]["offs"][i+1] for i in range(len(r["p32"]["offs"])-1))), len(p32)))
    print("  last offset lands on chunk end: %d/%d" % (sum(1 for r in p32 if r["p32"]["endok"]), len(p32)))
    print("  N(0x32) == C(0x31): %d/%d" % (sum(1 for r in p32 if r["p31"]["C"] == r["p32"]["N"]), len(p32)))
    print("  olen == N+1:", sum(1 for r in p32 if r["p32"]["olen"] == r["p32"]["N"]+1))
    print("  H by corpus:", dict(collections.Counter((r["corpus"], r["p32"]["H"]) for r in p32)))
    print("  distinct strings:", len(set(s for r in p32 for s in r["p32"]["strs"])))
    print("  empty strings:", sum(1 for r in p32 for s in r["p32"]["strs"] if s == ""))

    print("\n[D] tail (key,index) semantics")
    ok = bad = perm = inrange = 0
    for r in p32:
        p = P(r)
        if p["C"] == 0:
            continue
        strs = r["p32"]["strs"]
        if any(i >= len(strs) for _, i in p["tail"]):
            bad += 1; continue
        inrange += 1
        m = collections.defaultdict(set)
        for k, i in p["tail"]:
            m[k].add(strs[i])
        inv = collections.defaultdict(set)
        for k, v in m.items():
            for s in v:
                inv[s].add(k)
        if all(len(v) == 1 for v in m.values()) and all(len(v) == 1 for v in inv.values()):
            ok += 1
        else:
            bad += 1
        if sorted(i for _, i in p["tail"]) == list(range(p["C"])):
            perm += 1
    print("  C>0 samples with parseable 0x32: %d" % (inrange + bad))
    print("  index within N: %d ; index set == 0..C-1: %d" % (inrange, perm))
    print("  key<->string bijective: %d ok / %d not" % (ok, bad))

    print("\n[E] what the id array points at")
    t = collections.Counter(); par = collections.Counter(); pg = collections.Counter()
    idsonly = 0
    for r in p32:
        p = P(r)
        if p["C"] == 0:
            continue
        d = docs[r["file"]]
        byid = {c.id: c for c in d.chunks}
        idset = set(p["ids"])
        missing = [i for i in p["ids"] if i not in byid]
        if missing:
            idsonly += 1
        for i in p["ids"]:
            if i in byid:
                t[byid[i].type_name] += 1
                par[byid[i].parent] += 1
        pages = [c for c in d.chunks if c.type_marker == 0x14]
        kids = collections.defaultdict(list)
        for c in d.chunks:
            kids[c.parent].append(c)
        def desc(root):
            out = []; st = [root]
            while st:
                x = st.pop()
                for c in kids.get(x, []):
                    out.append(c.id); st.append(c.id)
            return set(out)
        hit = [pp.id for pp in pages if desc(pp.id) >= idset]
        pg[len(hit)] += 1
    print("  samples with unresolvable ids:", idsonly)
    print("  chunk types of listed ids:", dict(t))
    print("  #pages whose subtree contains the whole id set:", dict(pg))

main()
